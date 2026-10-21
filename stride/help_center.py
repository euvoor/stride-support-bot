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

STOP = {"a", "an", "the", "i", "can", "do", "you", "my", "is", "to", "after", "what", "how"}


def words(text):
    return {w.strip("?.,!$").lower() for w in text.split()} - STOP


def search_help_center(question, k=3):
    q = words(question)
    ranked = sorted(DOCS, key=lambda d: len(q & words(d)), reverse=True)
    return ranked[:k]
