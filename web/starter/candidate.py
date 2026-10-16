"""Starter with a deliberate missing-wrap bug. Compare ff ff to expose it."""
def evaluate(data: bytes) -> int:
    return sum(data)
