#!/usr/bin/env python3
"""
LoRA Training Helper for ResilM-IBN
This script helps initialize and manage LoRA fine-tuning for network configuration generation.
"""
import os
import json
import argparse
from pathlib import Path
from typing import Dict, List

from backend.lora.lora_finetuning import NetworkConfigLoRA, LoRAConfigParams


def create_sample_training_data():
    """Create sample training data for LoRA fine-tuning"""

    sample_data = [
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
            "intent": "建立一个由3台主机和2台交换机构成的线性拓扑",
            "json_output": {
                "action": "create_topology",
                "hosts": ["h1", "h2", "h3"],
                "switches": ["s1", "s2"],
                "links": [
                    {"src": "h1", "dst": "s1"},
                    {"src": "h2", "dst": "s1"},
                    {"src": "h3", "dst": "s2"},
                    {"src": "s1", "dst": "s2"}
                ],
                "controller": {
                    "type": "RemoteController",
                    "ip": "127.0.0.1",
                    "port": 6633
                }
            }
        },
        {
            "intent": "阻止h1与h2之间的通信",
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
            "intent": "允许h1和h2之间正常通信",
            "json_output": {
                "action": "install_flowtable",
                "switches": ["s1"],
                "match": {
                    "dl_type": 2048,
                    "nw_src": "10.0.0.1",
                    "nw_dst": "10.0.0.2",
                    "nw_proto": 1
                },
                "actions": "ALLOW",
                "priority": 100
            }
        },
        {
            "intent": "测试主机h1到h2的连通性",
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
            "intent": "限制从h1到h2的带宽为20Mbps",
            "json_output": {
                "action": "limit_bandwidth",
                "src_host": "h1",
                "dst_host": "h2",
                "rate_mbps": 20
            }
        },
        {
            "intent": "断开交换机s1和s2之间的连接",
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
            "intent": "清空交换机s1上的所有流表规则",
            "json_output": {
                "action": "delete_flowtable",
                "switches": ["s1"]
            }
        },
        {
            "intent": "恢复交换机s1和s2之间的链路",
            "json_output": {
                "action": "link_up",
                "link": ["s1", "s2"]
            }
        }
    ]

    # Save to file
    data_dir = Path("./training-data")
    data_dir.mkdir(exist_ok=True)

    with open(data_dir / "sample_network_configs.json", "w", encoding="utf-8") as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)

    print(f"Created sample training data with {len(sample_data)} examples in ./training-data/")
    return sample_data


def train_lora_model(data_file: str = "./training-data/sample_network_configs.json",
                    output_dir: str = "./lora-network-config",
                    epochs: int = 3):
    """Train a LoRA model with the provided data"""

    if not os.path.exists(data_file):
        print(f"Training data file not found: {data_file}")
        print("Creating sample training data...")
        training_data = create_sample_training_data()
    else:
        with open(data_file, "r", encoding="utf-8") as f:
            training_data = json.load(f)

    print(f"Loading ResilM-IBN LoRA trainer...")
    lora_trainer = NetworkConfigLoRA()

    print(f"Starting LoRA training with {len(training_data)} examples...")
    print(f"Training for {epochs} epochs, saving to {output_dir}")

    # Train the model
    lora_trainer.train(
        training_examples=training_data,
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=1
    )

    print(f"LoRA training completed! Model saved to {output_dir}")


def test_lora_model(model_path: str = "./lora-network-config", test_intent: str = None):
    """Test the trained LoRA model"""

    if test_intent is None:
        test_intent = "创建一个包含两台主机和一台交换机的网络拓扑"

    print(f"Testing LoRA model with intent: '{test_intent}'")

    # Try using the trained model if available
    try:
        from backend.lora.lora_integration import get_network_config_with_lora

        result = get_network_config_with_lora(test_intent)
        print("Generated JSON:")
        print(result)

        # Try to parse as JSON to verify validity
        try:
            parsed = json.loads(result)
            print("✓ Generated valid JSON!")
        except json.JSONDecodeError:
            print("⚠ Generated output is not valid JSON")
            # Try extracting JSON from the result if it contains other text
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                try:
                    parsed = json.loads(json_str)
                    print("✓ Found valid JSON in output!")
                    print(json_str)
                except json.JSONDecodeError:
                    print("⚠ Could not extract valid JSON from output")

    except Exception as e:
        print(f"Error testing LoRA model: {e}")


def main():
    parser = argparse.ArgumentParser(description="LoRA Training Helper for ResilM-IBN")
    parser.add_argument("--mode", choices=["create-data", "train", "test"],
                       default="create-data", help="Operation mode")
    parser.add_argument("--data-file", default="./training-data/sample_network_configs.json",
                       help="Path to training data file")
    parser.add_argument("--model-dir", default="./lora-network-config",
                       help="Directory to save/load the LoRA model")
    parser.add_argument("--epochs", type=int, default=3,
                       help="Number of training epochs")
    parser.add_argument("--test-intent", default=None,
                       help="Test intent for model evaluation")

    args = parser.parse_args()

    if args.mode == "create-data":
        create_sample_training_data()
        print("Sample training data created successfully!")

    elif args.mode == "train":
        train_lora_model(
            data_file=args.data_file,
            output_dir=args.model_dir,
            epochs=args.epochs
        )

    elif args.mode == "test":
        test_lora_model(
            model_path=args.model_dir,
            test_intent=args.test_intent
        )


if __name__ == "__main__":
    main()