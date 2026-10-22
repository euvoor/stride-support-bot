from openai import OpenAI

DOCS = [
    "Returns are accepted within 30 days of delivery.",
    "Shoes must be unworn and in the original box to be returned.",
    "Refunds go back to the original payment method within 5 business days.",
    "We ship to the United States and Canada.",
    "Standard shipping takes 3 to 5 business days.",
    "Express shipping takes 1 to 2 business days and costs $15.",
    "You can exchange shoes for a different size for free within 30 days.",
    "Gift cards cannot be returned or exchanged.",
]

_doc_vectors = None


def embed(texts):
    data = OpenAI().embeddings.create(model="text-embedding-3-small", input=texts).data
    return [d.embedding for d in data]


def search_help_center(question, k=3):
    # match by meaning, so "send them back" finds the return policy
    global _doc_vectors
    if _doc_vectors is None:
        _doc_vectors = embed(DOCS)
    q = embed([question])[0]
    scores = [sum(a * b for a, b in zip(q, v)) for v in _doc_vectors]
    ranked = sorted(zip(scores, DOCS), reverse=True)
    return [doc for _, doc in ranked[:k]]
