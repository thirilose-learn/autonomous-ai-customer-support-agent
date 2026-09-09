import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.rag.service import RAGRetrievalService

test_queries = [
    ("How many days do I have to return an order?", "return"),
    ("When will my refund show on my credit card statement?", "refund"),
    ("Can I cancel my order after it has shipped?", "cancellation"),
    ("What should I do if my package is lost in transit?", "shipping"),
    ("Does the warranty cover accidental drops or spills?", "warranty"),
    ("What payment methods do you accept?", None),
]

print("=" * 70)
print("SEMANTIC RETRIEVAL QUALITY EVALUATION (BAAI/bge-small-en-v1.5)")
print("=" * 70)

for query, category in test_queries:
    t0 = time.time()
    res = RAGRetrievalService.retrieve(query=query, category=category, top_k=3, threshold=0.0)
    elapsed = (time.time() - t0) * 1000
    print(f'\nQuery: "{query}"')
    print(f"Category filter: {category} | Roundtrip Latency: {elapsed:.1f}ms")
    for idx, m in enumerate(res["matches"], 1):
        score = m["similarity_score"]
        status = "PASSED (>= 0.65)" if score >= 0.65 else "BELOW 0.65 THRESHOLD"
        print(f'  Match {idx}: [{m["policy_category"]}] "{m["title"]}" -> Section: "{m.get("section")}"')
        print(f"    Cosine Similarity: {score:.4f} [{status}]")
        print(f'    Excerpt: {m["content"][:130]}...')
