"""
Production-ready LoRA integration for ResilM-IBN
This module integrates LoRA fine-tuning with fallback to standard LLM calls.
"""
import os
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

# Attempt to import required libraries for LoRA
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    LORA_AVAILABLE = True
except ImportError:
    LORA_AVAILABLE = False
    logging.warning("LoRA libraries not available. Using fallback mechanism.")

from backend.llm.llm_utils import client
from backend.rag.rag_system import rag_system

class ResilMLoRAIntegration:
    """Integration class to use LoRA fine-tuned models in ResilM-IBN"""

    def __init__(self, model_path: str = "./lora-network-config"):
        self.model_path = model_path
        self.use_lora = LORA_AVAILABLE and os.path.exists(model_path)
        self.lora_model = None
        self.tokenizer = None

        if self.use_lora:
            try:
                self._load_lora_model()
            except Exception as e:
                logging.warning(f"Could not load LoRA model: {e}. Falling back to standard LLM.")
                self.use_lora = False

    def _load_lora_model(self):
        """Load the fine-tuned LoRA model"""
        if not self.use_lora:
            return

        try:
            # Load base model
            base_model_name = "microsoft/DialoGPT-medium"  # Using a smaller model as default
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                torch_dtype=torch.float16,
                device_map="auto"
            )
            self.tokenizer = AutoTokenizer.from_pretrained(base_model_name)

            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Load LoRA adapter
            self.lora_model = PeftModel.from_pretrained(base_model, self.model_path)
            logging.info("LoRA model loaded successfully")
        except Exception as e:
            logging.error(f"Error loading LoRA model: {e}")
            self.use_lora = False

    def generate_network_json(self, intent: str, use_rag: bool = True) -> str:
        """
        Generate network configuration JSON from intent
        Uses LoRA model if available, falls back to standard LLM
        """
        if self.use_lora:
            return self._generate_with_lora(intent)
        else:
            return self._generate_with_standard_llm(intent, use_rag)

    def _generate_with_lora(self, intent: str) -> str:
        """Generate JSON using fine-tuned LoRA model"""
        try:
            # Create a prompt for the network configuration
            prompt = f"""Convert the following network intent into JSON format:
Intent: {intent}
JSON:"""

            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            input_ids = inputs["input_ids"].to(self.lora_model.device)

            with torch.no_grad():
                outputs = self.lora_model.generate(
                    input_ids,
                    max_length=len(input_ids[0]) + 128,
                    temperature=0.1,
                    pad_token_id=self.tokenizer.eos_token_id,
                    do_sample=True
                )

            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Extract just the JSON part
            json_part = generated_text[len(prompt):].strip()

            return json_part
        except Exception as e:
            logging.error(f"Error in LoRA generation: {e}")
            # Fallback to standard method
            return self._generate_with_standard_llm(intent, use_rag=True)

    def _generate_with_standard_llm(self, intent: str, use_rag: bool = True) -> str:
        """Generate JSON using standard LLM with RAG enhancement"""
        # Enhance the prompt with RAG if available
        system_prompt = """You are a network configuration expert. Generate only valid JSON for network configurations based on the user's intent. Do not include any explanation, only the JSON output."""

        user_message = f"""Generate a JSON configuration for the following network intent:
{intent}

Remember to output only valid JSON, no explanations."""

        # If RAG is available and requested, enhance the prompt
        if use_rag:
            try:
                enhanced_prompt = rag_system.augment_prompt(user_message, intent)
                user_message = enhanced_prompt
            except Exception as e:
                logging.warning(f"RAG enhancement failed: {e}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = client.chat.completions.create(
                model="glm-4.6",  # Using the same model as in your system
                messages=messages,
                temperature=0.1,
                max_tokens=512
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Error in standard LLM generation: {e}")
            return "{}"

    def is_available(self) -> bool:
        """Check if LoRA is available"""
        return self.use_lora


# Global instance
lora_integration = ResilMLoRAIntegration()


def get_network_config_with_lora(intent: str, use_rag: bool = True) -> str:
    """
    Get network configuration using LoRA if available, with RAG enhancement

    Args:
        intent (str): The network intent in natural language
        use_rag (bool): Whether to use RAG enhancement

    Returns:
        str: JSON configuration string
    """
    return lora_integration.generate_network_json(intent, use_rag)


def add_network_training_data(intent: str, expected_json: Dict):
    """
    Add training data for future LoRA fine-tuning

    Args:
        intent (str): Natural language intent
        expected_json (Dict): Expected JSON output
    """
    # This would be used when actually training the model
    training_example = {
        "intent": intent,
        "expected_output": json.dumps(expected_json, ensure_ascii=False)
    }

    # Store this for potential future training
    training_dir = Path("./lora-training-data")
    training_dir.mkdir(exist_ok=True)

    # Append to a training file
    training_file = training_dir / "custom_training_examples.jsonl"
    with open(training_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(training_example, ensure_ascii=False) + "\n")

    logging.info(f"Added training example for intent: {intent}")