"""Corrected one-byte checksum."""
def evaluate(data: bytes) -> int:
    return sum(data) & 255
