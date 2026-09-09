"""
Policy Knowledge Base RAG Tool.
Connects the Level 5 Agent to Level 4's pgvector knowledge retrieval service.
"""

from typing import Optional
from langchain_core.tools import tool, BaseTool
from app.rag.service import RAGRetrievalService


@tool
def search_policy_knowledge_base(query: str, category: Optional[str] = None) -> str:
    """
    Search official company policies and FAQs regarding returns, refunds, cancellations, shipping, warranties, and store guidelines.
    Args:
        query: The customer's policy question or keyword phrase (e.g., 'return window', 'shipping delay', 'refund method').
        category: Optional category filter: 'returns', 'refunds', 'cancellations', 'shipping', 'warranty', 'faqs'.
    """
    clean_cat = category.strip().lower() if category else None
    if clean_cat in ["all", "none", "null", ""]:
        clean_cat = None

    category_map = {
        "returns": "return",
        "return": "return",
        "refunds": "refund",
        "refund": "refund",
        "cancellations": "cancellation",
        "cancellation": "cancellation",
        "shipping": "shipping",
        "delivery": "shipping",
        "warranties": "warranty",
        "warranty": "warranty",
        "faqs": "faq",
        "faq": "faq",
    }
    if clean_cat:
        clean_cat = category_map.get(clean_cat, clean_cat)

    result = RAGRetrievalService.retrieve(
        query=query.strip(),
        category=clean_cat,
        top_k=3,
        threshold=0.50,  # Generous threshold for agent tool retrieval
    )

    matches = result.get("matches", [])
    # If category filter yielded 0 results, retry without filter
    if not matches and clean_cat:
        retry_result = RAGRetrievalService.retrieve(
            query=query.strip(),
            category=None,
            top_k=3,
            threshold=0.50,
        )
        matches = retry_result.get("matches", [])

    if not matches:
        return (
            f"No policy sections found matching '{query}'. "
            f"Please review standard store terms or request human agent assistance."
        )

    formatted_sections = []
    for idx, m in enumerate(matches, 1):
        formatted_sections.append(
            f"[{idx}] Category: {m['policy_category'].upper()} | Section: {m['section'] or m['title']}\n"
            f"Relevance Score: {m['similarity_score']:.2f}\n"
            f"Excerpt: {m['content']}"
        )

    return f"Retrieved {len(matches)} policy excerpt(s):\n\n" + "\n\n".join(formatted_sections)


def get_policy_tools() -> list[BaseTool]:
    """Returns the policy knowledge base tool list."""
    return [search_policy_knowledge_base]
