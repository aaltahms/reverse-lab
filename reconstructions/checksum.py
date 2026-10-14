"""Independent algebraic candidate, authored with reference source known."""
def reconstruct(data: bytes) -> int:
    window = data[:32]
    low = sum(window) % 255
    high = sum(value * (len(window) - index)
               for index, value in enumerate(window)) % 255
    return (high << 8) | low
