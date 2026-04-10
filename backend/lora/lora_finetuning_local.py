"""
LoRA Fine-tuning module for ResilM-IBN with Local Models
This module provides LoRA fine-tuning capabilities for local models like those served via Ollama.
"""
import os
import json
import torch
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, DataCollatorForLanguageModeling
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training, set_peft_model_state_dict
from datasets import Dataset
import logging
from pathlib import Path

try:
    from peft import PeftModel, LoraConfig as PeftLoraConfig
    LORA_AVAILABLE = True
except ImportError:
    LORA_AVAILABLE = False
    logging.warning("peft library not installed. LoRA functionality will be disabled.")

@dataclass
class LoRAConfigParams:
    """Configuration parameters for LoRA fine-tuning"""
    r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.1
    target_modules: List[str] = None
    bias: str = "none"
    task_type: TaskType = TaskType.CAUSAL_LM

    def __post_init__(self):
        if self.target_modules is None:
            # Common target modules for different architectures (including DeepSeek)
            self.target_modules = ["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj", "embed_tokens", "lm_head"]


class NetworkConfigDataset:
    """Dataset class for network configuration examples"""

    def __init__(self, examples: List[Dict], tokenizer, max_length: int = 1024):
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def create_conversation_format(self) -> List[Dict]:
        """Convert examples to conversation format for instruction tuning"""
        conversations = []
        for example in self.examples:
            intent = example.get("intent", "")
            json_output = json.dumps(example.get("json_output", {}), ensure_ascii=False, indent=2)

            # Create a conversation-style prompt for instruction tuning
            conversation = {
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的网络配置助手，专门生成精确的JSON格式网络配置命令。只输出JSON，不要任何解释。"
                    },
                    {
                        "role": "user",
                        "content": f"请为以下网络意图生成对应的JSON配置：{intent}"
                    },
                    {
                        "role": "assistant",
                        "content": json_output
                    }
                ]
            }
            conversations.append(conversation)
        return conversations

    def tokenize_dataset(self) -> Dataset:
        """Tokenize the dataset for training"""
        conversations = self.create_conversation_format()

        def tokenize_function(examples):
            # Format conversations into a single text for causal LM training
            texts = []
            for conv in examples['messages']:
                text = ""
                for msg in conv:
                    role = msg['role']
                    content = msg['content']
                    if role == "system":
                        text += f"<|system|>\n{content}\n<|end|>\n"
                    elif role == "user":
                        text += f"<|user|>\n{content}\n<|end|>\n"
                    elif role == "assistant":
                        text += f"<|assistant|>\n{content}\n<|end|>\n"
                texts.append(text)

            return self.tokenizer(
                texts,
                truncation=True,
                padding=True,
                max_length=self.max_length,
                return_tensors="pt"
            )

        # Convert to Hugging Face Dataset
        hf_dataset = Dataset.from_list(conversations)
        tokenized_dataset = hf_dataset.map(tokenize_function, batched=True, remove_columns=hf_dataset.column_names)
        return tokenized_dataset


class NetworkConfigLoRA:
    """LoRA fine-tuning system for network configuration generation with local models"""

    def __init__(self, base_model_name: str = "deepseek-ai/deepseek-coder-6.7b-instruct"):  # Using a model similar to deepseek
        self.base_model_name = base_model_name
        self.model = None
        self.tokenizer = None
        self.lora_model = None
        self.trained = False
        self.model_loaded = False

        # Default network configuration examples
        self.default_examples = [
            {
                "intent": "创建包含2台主机和1个交换机的简单网络拓扑",
                "json_output": {
                    "action": "create_topology",
                    "hosts": ["h1", "h2"],
                    "switches": ["s1"],
                    "links": [{"src": "h1", "dst": "s1"}, {"src": "h2", "dst": "s1"}],
                    "controller": {
                        "type": "RemoteController",
                        "ip": "127.0.0.1",
                        "port": 6633
                    }
                }
            },
            {
                "intent": "阻止h1和h2之间通信的流表规则",
                "json_output": {
                    "action": "install_flowtable",
                    "switches": ["s1"],
                    "match": {
                        "dl_type": 2048,
                        "nw_src": "10.0.0.1",
                        "nw_dst": "10.0.0.2",
                        "nw_proto": 1
                    },
                    "actions": "DENY",
                    "priority": 100
                }
            },
            {
                "intent": "测试h1和h2之间连通性的ping测试",
                "json_output": {
                    "action": "ping_test",
                    "hosts": ["h1", "h2"],
                    "extra": {
                        "source": "h1",
                        "target": "10.0.0.2"
                    }
                }
            },
            {
                "intent": "限制h1到h2带宽为10Mbps",
                "json_output": {
                    "action": "limit_bandwidth",
                    "src_host": "h1",
                    "dst_host": "h2",
                    "rate_mbps": 10
                }
            },
            {
                "intent": "断开交换机s1和s2之间的链路",
                "json_output": {
                    "action": "link_down",
                    "link": ["s1", "s2"]
                }
            },
            {
                "intent": "获取交换机s1的流表信息",
                "json_output": {
                    "action": "get_flowtable",
                    "switches": ["s1"]
                }
            },
            {
                "intent": "创建包含3台主机和2台交换机的线性拓扑",
                "json_output": {
                    "action": "create_topology",
                    "hosts": ["h1", "h2", "h3"],
                    "switches": ["s1", "s2"],
                    "links": [
                        {"src": "h1", "dst": "s1"},
                        {"src": "h2", "dst": "s1"},
                        {"src": "s3", "dst": "s2"},
                        {"src": "s1", "dst": "s2"}
                    ],
                    "controller": {
                        "type": "RemoteController",
                        "ip": "127.0.0.1",
                        "port": 6633
                    }
                }
            }
        ]

    def load_base_model(self, quantization: bool = True):
        """Load the base model and tokenizer for local fine-tuning"""
        if not LORA_AVAILABLE:
            raise ImportError("PEFT library is not installed. Please install it with 'pip install peft'")

        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Determine if we should use quantization based on available VRAM
            if quantization:
                # Use 4-bit quantization to reduce memory usage
                from transformers import BitsAndBytesConfig

                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )

                self.model = AutoModelForCausalLM.from_pretrained(
                    self.base_model_name,
                    quantization_config=bnb_config,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    trust_remote_code=True
                )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.base_model_name,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    trust_remote_code=True
                )

            # Prepare model for k-bit training if quantized
            if quantization:
                self.model = prepare_model_for_kbit_training(self.model)

            self.model_loaded = True
            logging.info(f"Base model {self.base_model_name} loaded successfully")

        except Exception as e:
            logging.error(f"Error loading base model: {e}")
            # Try with a smaller model as fallback
            try:
                fallback_model = "microsoft/DialoGPT-medium"  # Smaller model as fallback
                self.tokenizer = AutoTokenizer.from_pretrained(fallback_model)
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token

                self.model = AutoModelForCausalLM.from_pretrained(
                    fallback_model,
                    torch_dtype=torch.float16,
                    device_map="auto"
                )
                self.model_loaded = True
                logging.info(f"Fallback model {fallback_model} loaded successfully")
            except Exception as fallback_error:
                logging.error(f"Fallback model loading also failed: {fallback_error}")
                raise

    def setup_lora(self, lora_config: Optional[LoRAConfigParams] = None):
        """Setup LoRA configuration for the model"""
        if not LORA_AVAILABLE:
            raise ImportError("PEFT library is not installed.")

        if not self.model_loaded:
            self.load_base_model()

        if lora_config is None:
            lora_config = LoRAConfigParams()

        peft_config = LoraConfig(
            task_type=lora_config.task_type,
            inference_mode=False,
            r=lora_config.r,
            lora_alpha=lora_config.lora_alpha,
            lora_dropout=lora_config.lora_dropout,
            target_modules=lora_config.target_modules,
            bias=lora_config.bias
        )

        self.lora_model = get_peft_model(self.model, peft_config)
        logging.info("LoRA adapters initialized successfully")

    def train(self,
              training_examples: Optional[List[Dict]] = None,
              output_dir: str = "./resil-m-lora-adapter",
              num_train_epochs: int = 3,
              per_device_train_batch_size: int = 1,
              gradient_accumulation_steps: int = 8,
              warmup_steps: int = 10,
              logging_steps: int = 10,
              save_steps: int = 50,
              learning_rate: float = 5e-5):
        """Train the LoRA model with network configuration examples"""

        if training_examples is None:
            training_examples = []

        # Combine with default examples
        all_examples = self.default_examples + training_examples

        if self.lora_model is None:
            self.load_base_model()
            self.setup_lora()

        # Create dataset
        dataset_creator = NetworkConfigDataset(all_examples, self.tokenizer)
        train_dataset = dataset_creator.tokenize_dataset()

        # Setup training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            overwrite_output_dir=True,
            num_train_epochs=num_train_epochs,
            per_device_train_batch_size=per_device_train_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            warmup_steps=warmup_steps,
            logging_steps=logging_steps,
            save_steps=save_steps,
            evaluation_strategy="no",  # No eval set for now
            save_strategy="epoch",
            learning_rate=learning_rate,
            bf16=torch.cuda.is_available(),  # Use bf16 if available, else the training loop will handle it
            dataloader_pin_memory=False,
            remove_unused_columns=False,
            push_to_hub=False,
            report_to=None,  # Disable reporting to save resources
        )

        # Initialize trainer
        trainer = Trainer(
            model=self.lora_model,
            args=training_args,
            train_dataset=train_dataset,
            data_collator=DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer, mlm=False
            ),
        )

        # Start training
        logging.info("Starting LoRA fine-tuning...")
        trainer.train()

        # Save the adapter weights
        trainer.save_model(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        self.trained = True
        logging.info(f"LoRA adapter saved to {output_dir}")

    def generate_network_config(self, intent: str, model_path: str = "./resil-m-lora-adapter", max_length: int = 512, temperature: float = 0.1) -> str:
        """Generate network configuration JSON from intent using the trained LoRA model"""

        try:
            # Load the trained LoRA model if not already loaded
            if not self.trained or self.lora_model is None:
                if os.path.exists(model_path):
                    # Load base model
                    base_model = AutoModelForCausalLM.from_pretrained(
                        self.base_model_name,
                        torch_dtype=torch.float16,
                        device_map="auto",
                        trust_remote_code=True
                    )
                    self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)

                    if self.tokenizer.pad_token is None:
                        self.tokenizer.pad_token = self.tokenizer.eos_token

                    # Load LoRA adapter
                    self.lora_model = PeftModel.from_pretrained(base_model, model_path)
                    self.trained = True
                    logging.info(f"Trained LoRA model loaded from {model_path}")
                else:
                    logging.warning(f"Trained model not found at {model_path}, using base model with prompt optimization")
                    self.load_base_model(quantization=True)
                    # Use the base model with enhanced prompting instead
                    return self._generate_with_enhanced_prompting(intent)

            # Create the prompt in the same format used during training
            prompt = f"""<|system|>
你是一个专业的网络配置助手，专门生成精确的JSON格式网络配置命令。只输出JSON，不要任何解释。
<|end|>
<|user|>
请为以下网络意图生成对应的JSON配置：{intent}
<|end|>
<|assistant|>
"""

            # Tokenize the input
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length-max_length//4)
            input_ids = inputs["input_ids"].to(self.lora_model.device)

            # Generate the response
            with torch.no_grad():
                outputs = self.lora_model.generate(
                    input_ids,
                    max_length=len(input_ids[0]) + max_length//4,
                    temperature=temperature,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    do_sample=True,
                    repetition_penalty=1.2
                )

            # Decode the output
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extract just the assistant response part
            assistant_start = generated_text.find("<|assistant|>") + len("<|assistant|>")
            if assistant_start != -1:
                result = generated_text[assistant_start:].strip()
                # Remove the <|end|> tag if present
                result = result.replace("<|end|>", "").strip()
                return result
            else:
                return generated_text[len(prompt):].strip()

        except Exception as e:
            logging.error(f"Error generating network config with LoRA: {e}")
            # Fallback to enhanced prompting
            return self._generate_with_enhanced_prompting(intent)

    def _generate_with_enhanced_prompting(self, intent: str) -> str:
        """Fallback method using enhanced prompting without LoRA"""
        # This would connect to your local Ollama instance
        # Since we can't import ollama here without potential circular imports,
        # we'll just return an indication that Ollama should be used
        return f'{{"intent": "{intent}", "note": "Use local Ollama with enhanced prompting for actual generation"}}'

    def add_training_example(self, intent: str, json_output: Dict):
        """Add a custom training example to the default set"""
        example = {
            "intent": intent,
            "json_output": json_output
        }
        self.default_examples.append(example)
        logging.info(f"Added new training example for intent: {intent}")


# Global LoRA instance for ResilM-IBN
lora_finetuner = NetworkConfigLoRA()