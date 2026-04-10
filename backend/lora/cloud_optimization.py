"""
Fine-tuning simulation for ResilM-IBN cloud-based LLMs
Since we're using cloud-based LLM APIs, true fine-tuning isn't possible.
Instead, we simulate fine-tuning effects using enhanced prompting techniques.
"""
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

from backend.llm.llm_utils import client
from backend.rag.rag_system import rag_system


class CloudModelOptimizer:
    """
    Optimizer for cloud-based LLMs using prompt engineering instead of true fine-tuning.
    Since we're using API-based models, we can't perform actual LoRA fine-tuning,
    but we can optimize the prompts to achieve similar results.
    """

    def __init__(self):
        self.training_examples = []
        self.optimization_enabled = True
        self.load_default_examples()

    def load_default_examples(self):
        """Load default network configuration examples for prompt optimization"""
        self.training_examples = [
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
            }
        ]
        logging.info("Loaded default network configuration examples for prompt optimization")

    def add_training_example(self, intent: str, json_output: Dict):
        """Add a custom training example for prompt optimization"""
        example = {
            "intent": intent,
            "json_output": json_output
        }
        self.training_examples.append(example)
        logging.info(f"Added training example for intent: {intent}")

    def create_optimized_prompt(self, intent: str, use_rag: bool = True) -> str:
        """
        Create an optimized prompt that simulates fine-tuning effects for cloud models

        Args:
            intent: The network intent in natural language
            use_rag: Whether to include RAG-enhanced examples

        Returns:
            str: Optimized prompt for cloud-based LLM
        """
        # Start with a system instruction that primes the model for JSON output
        system_prompt = """你是网络配置专家，专门生成精确的JSON格式网络配置命令。
重要要求：
1. 只输出有效的JSON，不要任何解释文字
2. 严格按照示例中的格式生成
3. 确保JSON语法完全正确
4. 包含所有必需的字段
5. 对于网络地址，使用标准格式如"10.0.0.X" """

        # Include relevant examples from our "training" data
        examples_section = "以下是几个网络配置示例作为参考：\n\n"
        for i, example in enumerate(self.training_examples[-3:], 1):  # Use last 3 examples
            examples_section += f"示例{i}:\n"
            examples_section += f"意图: {example['intent']}\n"
            examples_section += f"输出: {json.dumps(example['json_output'])}\n\n"

        # Create the main user prompt
        user_prompt = f"""根据以下网络意图生成对应的JSON配置：

{intent}

请严格按照上述示例格式生成JSON输出，确保所有字段都正确。
只输出JSON内容，不要任何其他文字。"""

        # Enhance with RAG if enabled
        if use_rag:
            rag_context = rag_system.retrieve_context(intent, top_k=2)
            if rag_context:
                rag_section = "相关配置参考：\n"
                for i, ctx in enumerate(rag_context, 1):
                    rag_section += f"{i}. {ctx['content']} (相似度: {ctx['similarity_score']:.3f})\n"
                user_prompt = f"{rag_section}\n{user_prompt}"

        # Combine everything
        optimized_prompt = f"{examples_section}{user_prompt}"

        return system_prompt, optimized_prompt

    def generate_with_optimization(self, intent: str, model: str = "glm-4.6", use_rag: bool = True) -> str:
        """
        Generate network configuration using optimized prompting

        Args:
            intent: Network intent in natural language
            model: Model to use (passed to cloud API)
            use_rag: Whether to use RAG enhancement

        Returns:
            str: Generated JSON configuration
        """
        if not self.optimization_enabled:
            # Fallback to basic prompting
            system_prompt = "你是网络配置专家，生成有效的JSON格式网络配置命令，只输出JSON，不要解释。"
            user_prompt = f"生成以下网络意图的JSON配置：\n{intent}"
        else:
            system_prompt, user_prompt = self.create_optimized_prompt(intent, use_rag)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,  # Lower temperature for more consistent outputs
                max_tokens=512
            )

            result = response.choices[0].message.content.strip()
            logging.info(f"Cloud model optimization generated response for intent: {intent[:50]}...")
            return result

        except Exception as e:
            logging.error(f"Error in optimized generation: {e}")
            # Fallback to basic call
            try:
                basic_messages = [
                    {"role": "system", "content": "你是一个网络配置专家，生成有效的JSON格式网络配置命令。只输出JSON，不要解释文字。"},
                    {"role": "user", "content": f"生成以下网络意图的JSON配置：{intent}"}
                ]

                response = client.chat.completions.create(
                    model=model,
                    messages=basic_messages,
                    temperature=0.1,
                    max_tokens=512
                )

                return response.choices[0].message.content.strip()
            except Exception:
                return "{}"  # Return empty JSON on complete failure


# Global instance
optimizer = CloudModelOptimizer()


def get_optimized_network_config(intent: str, model: str = "glm-4.6", use_rag: bool = True) -> str:
    """
    Get network configuration with optimization techniques (simulating fine-tuning effects)

    Args:
        intent: Network intent in natural language
        model: Cloud model to use
        use_rag: Whether to use RAG enhancement

    Returns:
        str: JSON configuration string
    """
    return optimizer.generate_with_optimization(intent, model, use_rag)