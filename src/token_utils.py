import logging

logger = logging.getLogger(__name__)


def estimate_tokens(text: str, model: str = "gpt-4o") -> int:
    """Estimates the number of tokens in a text using tiktoken, with a fallback to crude character count."""
    try:
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("o200k_base")
        return len(enc.encode(text, disallowed_special=()))
    except Exception as e:
        logger.warning(f"Failed to estimate tokens using tiktoken, falling back to crude character count: {e}")
        return max(1, len(text) // 4) if text else 0
