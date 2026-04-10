"""
LoRA Fine-tuning module for ResilM-IBN
This module provides LoRA fine-tuning capabilities to adapt LLMs for generating
specific JSON formats for network configurations.
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

try:
    from peft import PeftModel
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
            # Common target modules for different architectures
            self.target_modules = ["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

class NetworkConfigDataset:
    """Dataset class for network configuration examples"""

    def __init__(self, examples: List[Dict], tokenizer, max_length: int = 512):
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def create_prompt_completion_pairs(self) -> List[Dict]:
        """Convert examples to prompt-completion pairs for training"""
        pairs = []
        for example in self.examples:
            # Create a prompt asking for JSON format
            intent = example.get("intent", "")
            json_output = json.dumps(example.get("json_output", {}), ensure_ascii=False)

            # Format as instruction-following dataset
            prompt = f"""### 指令：
根据以下网络意图生成对应的JSON格式配置：

### 输入：
{intent}

### 输出：
```json
{json_output}
```
"""
            pairs.append({
                "text": prompt
            })
        return pairs

    def tokenize_dataset(self) -> Dataset:
        """Tokenize the dataset for training"""
        pairs = self.create_prompt_completion_pairs()

        def tokenize_function(examples):
            return self.tokenizer(
                examples["text"],
                truncation=True,
                padding=True,
                max_length=self.max_length,
                return_tensors="pt"
            )

        # Convert to Hugging Face Dataset
        hf_dataset = Dataset.from_list(pairs)
        tokenized_dataset = hf_dataset.map(tokenize_function, batched=True)
        return tokenized_dataset

class NetworkConfigLoRA:
    """LoRA fine-tuning system for network configuration generation"""

    def __init__(self, base_model_name: str = "microsoft/DialoGPT-medium"):
        self.base_model_name = base_model_name
        self.model = None
        self.tokenizer = None
        self.lora_model = None
        self.trained = False

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
            }
        ]

    def load_base_model(self):
        """Load the base model and tokenizer"""
        if not LORA_AVAILABLE:
            raise ImportError("PEFT library is not installed. Please install it with 'pip install peft'")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model = AutoModelForCausalLM.from_pretrained(
                self.base_model_name,
                load_in_8bit=True,  # Reduce memory usage
                torch_dtype=torch.float16,
                device_map="auto"
            )

            # Prepare model for k-bit training
            self.model = prepare_model_for_kbit_training(self.model)

        except Exception as e:
            logging.error(f"Error loading base model: {e}")
            # If loading fails, we'll use a simpler approach
            self.model = None
            self.tokenizer = None

    def setup_lora(self, lora_config: Optional[LoRAConfigParams] = None):
        """Setup LoRA configuration for the model"""
        if not LORA_AVAILABLE:
            raise ImportError("PEFT library is not installed.")

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
        logging.info("LoRA model initialized successfully")

    def train(self,
              training_examples: Optional[List[Dict]] = None,
              output_dir: str = "./lora-network-config",
              num_train_epochs: int = 3,
              per_device_train_batch_size: int = 1,
              warmup_steps: int = 10,
              logging_steps: int = 10):
        """Train the LoRA model with network configuration examples"""

        if training_examples is None:
            training_examples = self.default_examples

        # Combine with user examples if provided
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
            warmup_steps=warmup_steps,
            logging_steps=logging_steps,
            save_strategy="epoch",
            prediction_loss_only=True,
            remove_unused_columns=False,
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

        # Save the model
        trainer.save_model(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        self.trained = True
        logging.info(f"LoRA model saved to {output_dir}")

    def generate_network_config(self, intent: str, model_path: str = "./lora-network-config", max_length: int = 512) -> str:
        """Generate network configuration JSON from intent using the trained LoRA model"""

        try:
            # Load the trained LoRA model if not already loaded
            if not self.trained or self.lora_model is None:
                base_model = AutoModelForCausalLM.from_pretrained(
                    self.base_model_name,
                    torch_dtype=torch.float16,
                    device_map="auto"
                )
                self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)

                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token

                self.lora_model = PeftModel.from_pretrained(base_model, model_path)
                self.trained = True

            # Create the prompt
            prompt = f"""### 指令：
根据以下网络意图生成对应的JSON格式配置：

### 输入：
{intent}

### 输出：
```json
"""

            # Tokenize the input
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length-max_length//4)
            input_ids = inputs["input_ids"].to(self.lora_model.device)

            # Generate the response
            with torch.no_grad():
                outputs = self.lora_model.generate(
                    input_ids,
                    max_length=len(input_ids[0]) + max_length//4,
                    temperature=0.1,
                    pad_token_id=self.tokenizer.eos_token_id,
                    do_sample=True
                )

            # Decode the output
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extract the JSON part from the response
            json_start = generated_text.find("```json")
            if json_start != -1:
                json_content = generated_text[json_start+7:]  # Skip "```json"
                json_end = json_content.find("```")
                if json_end != -1:
                    json_content = json_content[:json_end]

                return json_content.strip()
            else:
                # If no JSON block found, return the part after the prompt
                response_start = generated_text.find("### 输出：") + len("### 输出：")
                if response_start != -1:
                    return generated_text[response_start:].strip()

            return generated_text[len(prompt):].strip()

        except Exception as e:
            logging.error(f"Error generating network config: {e}")
            return "{}"

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