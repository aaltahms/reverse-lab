"""Agent-authored parsing candidate, reference source known; not decompiled."""
def reconstruct(data: bytes) -> int:
    if len(data) < 6:
        return 1
    magic, kind, high, low, size = data[:5]
    if magic != 165:
        return 2
    if kind not in range(8):
        return 3
    if size != len(data[5:-1]):
        return 4
    if sum(data[:-1]) % 256 != data[-1]:
        return 5
    sequence = int.from_bytes(bytes([high, low]), 'big')
    payload_sum = sum(data[5:-1]) % 256
    return 2**31 + kind * 2**24 + sequence * 256 + payload_sum


def faulty_endian(data: bytes) -> int:
    """Deliberate mutant: preserve validation but swap the sequence bytes."""
    recovered = reconstruct(data)
    if recovered < 2**31:
        return recovered
    sequence = int.from_bytes(data[2:4], 'little')
    return (recovered & 0xFF0000FF) | (sequence << 8)
