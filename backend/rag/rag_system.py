"""
Simple RAG (Retrieval Augmented Generation) module for ResilM-IBN
This module provides document storage, retrieval, and integration with LLM calls.
"""
import os
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
import sqlite3
import hashlib
from datetime import datetime

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    logging.warning("sentence-transformers not installed. RAG functionality will be limited.")

class SimpleVectorDB:
    """Simple vector database using SQLite for storage"""

    def __init__(self, db_path: str = "rag_data.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize the database tables"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                embedding BLOB,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON documents(created_at)
        """)
        self.conn.commit()

    def add_document(self, content: str, metadata: Dict = None) -> str:
        """Add a document to the database"""
        doc_id = hashlib.md5((content + str(datetime.now())).encode()).hexdigest()

        # Calculate embedding if available
        embedding_blob = None
        if EMBEDDING_AVAILABLE:
            model = SentenceTransformer('all-MiniLM-L6-v2')  # Lightweight model
            embedding = model.encode([content])[0]
            embedding_blob = embedding.tobytes()

        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO documents (id, content, embedding, metadata) VALUES (?, ?, ?, ?)",
            (doc_id, content, embedding_blob, json.dumps(metadata or {}))
        )
        self.conn.commit()
        return doc_id

    def search_similar(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for similar documents to the query"""
        if not EMBEDDING_AVAILABLE:
            # Fallback to simple keyword search
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, content, metadata FROM documents WHERE content LIKE ? LIMIT ?",
                (f"%{query}%", top_k)
            )
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'content': row[1],
                    'metadata': json.loads(row[2]),
                    'similarity_score': 0.5  # Placeholder score
                })
            return results

        # Calculate query embedding
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = model.encode([query])[0]

        # Retrieve all embeddings from DB and calculate similarities
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, content, embedding, metadata FROM documents WHERE embedding IS NOT NULL")

        results = []
        for row in cursor.fetchall():
            stored_embedding = np.frombuffer(row[2], dtype=np.float32)
            similarity = np.dot(query_embedding, stored_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
            )
            results.append({
                'id': row[0],
                'content': row[1],
                'metadata': json.loads(row[3]),
                'similarity_score': float(similarity)
            })

        # Sort by similarity and return top_k
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:top_k]

    def close(self):
        """Close the database connection"""
        self.conn.close()


class RAGSystem:
    """Main RAG system for ResilM-IBN"""

    def __init__(self):
        self.vector_db = SimpleVectorDB()
        self.initialized = False

    def initialize_with_examples(self):
        """Initialize the RAG system with example network configurations"""
        if self.initialized:
            return

        examples = [
            {
                "content": "创建包含2台主机和1个交换机的简单网络拓扑。使用命令: {\"action\": \"create_topology\", \"hosts\": [\"h1\", \"h2\"], \"switches\": [\"s1\"], \"links\": [{\"src\": \"h1\", \"dst\": \"s1\"}, {\"src\": \"h2\", \"dst\": \"s1\"}]}",
                "metadata": {"category": "topology", "type": "simple"}
            },
            {
                "content": "创建包含3台主机和2个交换机的线性网络拓扑。使用命令: {\"action\": \"create_topology\", \"hosts\": [\"h1\", \"h2\", \"h3\"], \"switches\": [\"s1\", \"s2\"], \"links\": [{\"src\": \"h1\", \"dst\": \"s1\"}, {\"src\": \"h2\", \"dst\": \"s1\"}, {\"src\": \"s2\", \"dst\": \"s2\"}, {\"src\": \"s1\", \"dst\": \"s2\"}]}",
                "metadata": {"category": "topology", "type": "linear"}
            },
            {
                "content": "阻止h1和h2之间通信的流表规则。使用命令: {\"action\": \"install_flowtable\", \"switches\": [\"s1\"], \"match\": {\"dl_type\": 2048, \"nw_src\": \"10.0.0.1\", \"nw_dst\": \"10.0.0.2\", \"nw_proto\": 1}, \"actions\": \"DENY\", \"priority\": 100}",
                "metadata": {"category": "flow_control", "type": "blocking"}
            },
            {
                "content": "允许h1和h2之间通信的流表规则。使用命令: {\"action\": \"install_flowtable\", \"switches\": [\"s1\"], \"match\": {\"dl_type\": 2048, \"nw_src\": \"10.0.0.1\", \"nw_dst\": \"10.0.0.2\", \"nw_proto\": 1}, \"actions\": \"ALLOW\", \"priority\": 100}",
                "metadata": {"category": "flow_control", "type": "allowing"}
            },
            {
                "content": "测试h1和h2之间连通性的ping测试。使用命令: {\"action\": \"ping_test\", \"hosts\": [\"h1\", \"h2\"], \"extra\": {\"source\": \"h1\", \"target\": \"10.0.0.2\"}}",
                "metadata": {"category": "testing", "type": "connectivity"}
            },
            {
                "content": "限制h1到h2带宽为10Mbps。使用命令: {\"action\": \"limit_bandwidth\", \"src_host\": \"h1\", \"dst_host\": \"h2\", \"rate_mbps\": 10}",
                "metadata": {"category": "bandwidth", "type": "limiting"}
            },
            {
                "content": "清除交换机s1上的所有流表。使用命令: {\"action\": \"delete_flowtable\", \"switches\": [\"s1\"]}",
                "metadata": {"category": "flow_control", "type": "cleaning"}
            },
            {
                "content": "断开交换机s1和s2之间的链路。使用命令: {\"action\": \"link_down\", \"link\": [\"s1\", \"s2\"]}",
                "metadata": {"category": "topology", "type": "link_control"}
            },
            {
                "content": "恢复交换机s1和s2之间的链路。使用命令: {\"action\": \"link_up\", \"link\": [\"s1\", \"s2\"]}",
                "metadata": {"category": "topology", "type\": "link_control"}
            }
        ]

        for example in examples:
            self.vector_db.add_document(example["content"], example["metadata"])

        self.initialized = True
        logging.info("RAG system initialized with example configurations")

    def retrieve_context(self, query: str, top_k: int = 3) -> List[Dict]:
        """Retrieve relevant context for a query"""
        if not self.initialized:
            self.initialize_with_examples()
        return self.vector_db.search_similar(query, top_k)

    def augment_prompt(self, original_prompt: str, query: str) -> str:
        """Augment a prompt with retrieved context"""
        context_docs = self.retrieve_context(query)

        if not context_docs:
            return original_prompt

        # Format context as additional instructions
        context_str = "Additional context for network configuration:\n"
        for i, doc in enumerate(context_docs, 1):
            context_str += f"{i}. {doc['content']}\n"

        augmented_prompt = f"{original_prompt}\n\n{context_str}\nBased on the above context, please generate appropriate network configuration commands."
        return augmented_prompt


# Global RAG instance
rag_system = RAGSystem()