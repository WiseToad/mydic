def normalize_text(text: str) -> str:
    """Strip leading/trailing whitespace and collapse internal runs to a single space."""
    return " ".join(text.split())
