"""
Utility functions to manage the RAG system for ResilM-IBN
This module provides helper functions to add custom documents to the RAG system.
"""
from backend.rag.rag_system import rag_system


def add_network_document(content: str, metadata: dict = None):
    """
    Add a custom network configuration document to the RAG system

    Args:
        content (str): The content to add to the RAG system
        metadata (dict): Optional metadata about the content

    Returns:
        str: Document ID if successful, None otherwise
    """
    return rag_system.add_custom_document(content, metadata)


def retrieve_network_context(query: str, top_k: int = 3):
    """
    Retrieve relevant context from the RAG system based on the query

    Args:
        query (str): The query to search for relevant context
        top_k (int): Number of top results to return

    Returns:
        List[dict]: List of relevant documents with similarity scores
    """
    return rag_system.retrieve_context(query, top_k)


def augment_network_prompt(original_prompt: str, query: str):
    """
    Augment a network-related prompt with retrieved context from the RAG system

    Args:
        original_prompt (str): The original prompt to augment
        query (str): The query to search for relevant context

    Returns:
        str: Augmented prompt with retrieved context
    """
    return rag_system.augment_prompt(original_prompt, query)


# Example usage:
if __name__ == "__main__":
    # Example: Adding a custom network configuration to the RAG system
    sample_config = '''
    创建一个具有负载均衡功能的网络拓扑，包含3台服务器和2台负载均衡器。
    使用命令: {"action": "create_topology", "hosts": ["server1", "server2", "server3", "lb1", "lb2"],
    "switches": ["s1", "s2", "s3"],
    "links": [{"src": "server1", "dst": "s1"}, {"src": "server2", "dst": "s1"},
              {"src": "server3", "dst": "s1"}, {"src": "lb1", "dst": "s2"},
              {"src": "lb2", "dst": "s3"}, {"src": "s1", "dst": "s2"},
              {"src": "s1", "dst": "s3"}]}
    '''

    metadata = {
        "category": "topology",
        "type": "load_balancing",
        "action": "create_topology",
        "difficulty": "advanced"
    }

    doc_id = add_network_document(sample_config, metadata)
    print(f"Added document with ID: {doc_id}")

    # Example: Retrieving context
    context = retrieve_network_context("创建负载均衡网络", top_k=2)
    print("Retrieved context:", context)