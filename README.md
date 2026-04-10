# ResilM-IBN: Multi-Agent Network Intent-Based Networking System

ResilM-IBN is an advanced intent-based networking system that translates natural language network requirements into automated network configurations using AI-powered agents, SDN controllers, and network simulation.

## 🚀 Overview

ResilM-IBN leverages Large Language Models (LLMs) to bridge the gap between human-readable network intentions and automated network operations. The system enables network administrators to express complex network requirements in plain English and automatically implements them through intelligent multi-agent coordination.

### Key Features

- **Natural Language Interface**: Express network requirements in plain English
- **AI-Powered Translation**: LLMs convert intent to executable network configurations  
- **Multi-Agent Architecture**: Specialized agents handle different network operations
- **SDN Integration**: Built on Ryu SDN controller for network automation
- **Network Simulation**: Uses Mininet for testing and validation
- **Real-time Feedback**: Comprehensive logging and monitoring capabilities
- **RAG Enhancement**: Retrieval-Augmented Generation for improved accuracy
- **Local Model Support**: Compatible with local models like DeepSeek via Ollama
- **LoRA Integration**: Fine-tuned adapters for specialized network configurations

## 🏗️ Architecture

The system comprises several interconnected components:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │───▶│   Intent Agent   │───▶│ Message Pool    │
│ (Natural Lang.) │    │ (LLM Processing) │    │ (Pub/Sub)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                          │
    ┌─────────────────┐    ┌──────────────────┐    ┌─────▼─────┐
    │   API Server    │    │  Specialized     │    │  Network  │
    │   (Flask)       │    │    Agents        │    │   Layer   │
    └─────────────────┘    └──────────────────┘    └───────────┘
                            ├─ Flow Agent      │        │
                            ├─ Topology Agent  │        │
                            ├─ QA Agent        │        │
                            ├─ Executor Agent  │        │
                            └─ JSON Builder    │        │
                                                     Mininet
                                                      Ryu
```

### Core Components

- **Intent Agent**: Translates natural language into structured JSON instructions using LLMs
- **JSON Builder Agent**: Converts planned steps into structured JSON commands following specific schemas
- **Message Pool**: Central coordinator for inter-agent communication via pub/sub pattern
- **Specialized Agents**: Handle specific network operations:
  - Flow Agent: Manages flow table rules and bandwidth limits
  - Topology Agent: Creates and manages network topologies
  - QA Agent: Performs connectivity tests (ping, bandwidth)
  - Executor Agent: Handles control operations (wait, print, etc.)

The JSON Builder Agent follows specific schemas for different network operations:
- create_topology: Defines hosts, switches, links and controller configuration
- install_flowtable: Configures flow rules with match criteria and actions  
- delete_flowtable: Removes specific flow rules or clears all rules on switches
- ping_test: Tests host connectivity with optional automatic fixes
- get_flowtable: Retrieves current flow table entries from switches
- limit_bandwidth/clear_bandwidth_limit: Manages bandwidth restrictions between hosts
- link_down/link_up: Controls network link states
- ping_all/wait: Network-wide ping tests and timing delays

### Project Directory Structure

```
ResilM-IBN/
├── backend/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py                 # Flask API server with routes
│   ├── agent_core/
│   │   ├── __init__.py
│   │   ├── flowtable_manager.py   # Flow table management
│   │   ├── qa_manager.py          # QA/testing management
│   │   └── topology_manager.py    # Topology management
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── executor_agent.py      # Execution control agent
│   │   ├── flow_agent.py          # Flow management agent
│   │   ├── intent_agent.py        # Natural language processing agent
│   │   ├── json_builder_agent.py  # JSON command generation agent
│   │   ├── prompts/               # Agent prompt templates
│   │   │   ├── intent_agent.txt
│   │   │   └── json_builder_agent.txt
│   │   ├── qa_agent.py            # QA/testing agent
│   │   └── topology_agent.py      # Topology management agent
│   ├── controller/
│   │   ├── PathIntentController.py # Ryu SDN controller implementation
│   │   ├── __init__.py
│   │   ├── controller_instance.py  # Controller instance management
│   │   └── ryu_topology_rest.py    # REST API for topology
│   ├── coordinator/
│   │   ├── coordinator_agent.py    # Coordination agent
│   │   ├── message_pool.py         # Message queue/pub-sub system
│   │   └── __init__.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── llm_utils.py            # LLM utilities and JSON parsing
│   │   ├── llm_flexible.py         # Flexible LLM interface (local/cloud)
│   │   ├── prompt_templates.py
│   │   └── Qwen.py
│   ├── lora/                      # LoRA fine-tuning implementation
│   │   ├── __init__.py
│   │   ├── cloud_optimization.py   # Cloud model optimization
│   │   ├── local_lora_integration.py # Local LoRA integration
│   │   ├── lora_finetuning_local.py # Local LoRA implementation
│   │   └── train_helper.py         # Training utilities
│   ├── net_simulation/            # Network simulation layer
│   │   ├── __init__.py
│   │   ├── instruction_executor.py
│   │   ├── mininet_manager.py      # Mininet orchestration
│   │   ├── net_bridge.py
│   │   └── ryu_controller.py
│   ├── rag/                       # RAG (Retrieval Augmentation) system
│   │   ├── __init__.py
│   │   ├── rag_system.py          # FAISS-based vector DB and retrieval
│   │   ├── rag_utils.py           # RAG utilities
│   │   └── cloud_optimization.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── arp_utils.py
│   │   ├── logger.py              # Logging system
│   │   ├── messagepool_utils.py
│   │   ├── ryu_utils.py
│   │   ├── token_counter.py
│   │   ├── token_recorder.py
│   │   ├── token_utils.py
│   │   ├── topology_utils.py
│   │   └── utils.py
│   └── main.py
├── frontend/
│   ├── static/                    # Static assets (images, CSS, JS)
│   │   └── img/
│   │       ├── host.png
│   │       └── switch.png
│   └── templates/                 # HTML templates
│       └── index.html
├── ryu_app/
│   ├── __init__.py
│   └── auto_generate_path_intents.py # Path generation utilities
├── .gitignore
├── README.md
├── LICENSE
├── requirements.lock.txt          # Dependencies
├── start_all.py                   # Main application launcher
├── demo_local_lora.py            # Local LoRA usage examples
└── tmp/                          # Temporary files
```

## 🔧 Technologies & Libraries

- **Backend**: Python 3.8+, Flask API server
- **SDN**: Ryu SDN Controller for network control
- **Network Simulation**: Mininet for topology testing
- **Database**: FAISS for vector similarity search (RAG system)
- **ML/NLP**: Transformers, sentence-transformers for semantic processing
- **AI Models**: OpenAI-compatible API (supports both cloud and local models)
- **Network Analysis**: NetworkX for graph algorithms
- **Microservices**: Multi-agent architecture with pub/sub messaging

## Supported Operations

- **Network Topology Management**: Create, modify, and delete network topologies  
- **Flow Table Control**: Install, delete, and query flow table rules
- **Connectivity Testing**: Ping tests, bandwidth verification
- **Bandwidth Management**: Limit and clear bandwidth restrictions
- **Link Control**: Bring links up/down dynamically
- **Automated Repair**: Smart troubleshooting and automatic fixes

## 🛠️ Prerequisites

- Python 3.8+
- Mininet (for network simulation)
- Ryu SDN Controller
- NetworkX for topology management
- OpenAI-compatible LLM API or local models (Ollama with DeepSeek/Codellama)

## 📦 Installation

1. Clone the repository:
```bash
git clone <your-repository-url>
cd ResilM-IBN
```

2. Install dependencies:
```bash
pip install -r requirements.lock.txt
```

3. For local model support (optional but recommended):
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model (e.g., DeepSeek-Coder)
ollama pull deepseek-coder:6.7b
```

4. Configure your LLM API key in `backend/llm/llm_utils.py` or setup local model access

## 🚀 Usage

Start the system with both the Ryu controller and Flask API server:

```bash
python start_all.py
```

The system will start:
- Ryu SDN Controller on port 6633
- REST API server on port 8081  
- Web API server on port 5000

### Example Requests

Submit a natural language intent:
```bash
curl -X POST http://localhost:5000/intent \
  -H "Content-Type: application/json" \
  -d '{"intent": "Create a network with 2 hosts connected to 1 switch"}'
```

Get current topology:
```bash
curl http://localhost:5000/topology
```

Get token usage statistics:
```bash
curl http://localhost:5000/token_stats
```

## 📄 API Endpoints

- `POST /intent`: Submit natural language network intents
- `GET /topology`: Retrieve current network topology
- `POST /stop`: Stop the current network topology
- `GET /token_stats`: Get LLM token usage statistics
- `POST /cleanup`: Clean up topology and reset state
- `GET /shortest_path`: Get shortest path between hosts
- `POST /token/reset`: Reset token counter
- `GET /token/summary`: Get token usage summary

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Authors

- **JingWen Gou**

## 🙏 Acknowledgments

- Special thanks to the Ryu SDN Controller community
- Mininet for network simulation capabilities
- OpenAI-compatible API providers for LLM services
- NetworkX for graph algorithms
- HuggingFace and PEFT for LoRA implementation support