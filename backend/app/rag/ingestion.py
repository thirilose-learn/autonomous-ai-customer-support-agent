"""
Document Ingestion & Chunking Pipeline using LlamaIndex.
Loads markdown policy documents, extracts section hierarchy, and segments into semantic nodes.
"""

import os
import re
from typing import List, Dict, Any
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document

CATEGORY_MAP = {
    "return_policy.md": ("return", "Return Policy"),
    "refund_policy.md": ("refund", "Refund Policy"),
    "cancellation_policy.md": ("cancellation", "Cancellation Policy"),
    "shipping_policy.md": ("shipping", "Shipping & Delivery Policy"),
    "warranty_policy.md": ("warranty", "Warranty Policy"),
    "faqs.md": ("faqs", "Frequently Asked Questions"),
}


def extract_sections_from_markdown(text: str) -> List[Dict[str, Any]]:
    """
    Splits markdown into section blocks based on '## Heading' or '### Q' patterns
    to maintain section context for metadata enrichment.
    """
    lines = text.split("\n")
    sections = []
    current_heading = "General"
    current_lines = []

    for line in lines:
        if line.startswith("## ") or line.startswith("### "):
            if current_lines:
                sections.append({
                    "section": current_heading,
                    "content": "\n".join(current_lines).strip()
                })
                current_lines = []
            current_heading = line.lstrip("#").strip()
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({
            "section": current_heading,
            "content": "\n".join(current_lines).strip()
        })

    return sections


def load_and_chunk_knowledge_base(kb_dir: str) -> List[Dict[str, Any]]:
    """
    Reads all markdown policies from the knowledge base directory,
    chunks them using SentenceSplitter, and prepares records for embedding.
    """
    splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    all_chunks: List[Dict[str, Any]] = []

    for filename, (cat, title) in CATEGORY_MAP.items():
        file_path = os.path.join(kb_dir, filename)
        if not os.path.exists(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            full_text = f.read()

        sections = extract_sections_from_markdown(full_text)
        chunk_idx = 0

        for sec in sections:
            sec_content = sec["content"]
            if not sec_content or len(sec_content.strip()) < 10:
                continue

            sec_heading = sec["section"]
            doc = Document(text=sec_content)
            nodes = splitter.get_nodes_from_documents([doc])

            for node in nodes:
                node_text = node.get_content().strip()
                if not node_text:
                    continue

                chunk_idx += 1
                doc_id = f"{cat}_{chunk_idx:03d}"

                chunk_record = {
                    "doc_id": doc_id,
                    "policy_category": cat,
                    "title": title,
                    "section": sec_heading,
                    "content": node_text,
                    "metadata": {
                        "source_file": filename,
                        "category": cat,
                        "section": sec_heading,
                        "char_length": len(node_text),
                    },
                }
                all_chunks.append(chunk_record)

    return all_chunks
