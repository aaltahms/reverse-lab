# Fixture contracts

All functions consume bytes and return a uint32. The executable harness limits inputs to 64 bytes. These are self-authored fixtures; no third-party proprietary target is included.

## Bounded checksum

For `n = min(length, 32)`, start with `a = b = 0`. For each byte: `a = (a + byte) mod 255`, `b = (b + a) mod 255`. Return `(b << 8) | a`. Empty returns zero. The candidate instead computes a simple byte sum and a positional weighted sum. Directed inputs exercise lengths 1/2/31/32/33/64 and bytes 0/1/254/255; a ramp checks mixed weights. `abcde` has checksum `0xc8f0` in the golden regression.

## Packet decoder

| Offset | Meaning |
| --- | --- |
| 0 | Magic `a5` |
| 1 | Kind, 0..7 |
| 2..3 | 16-bit sequence, big endian |
| 4 | Payload length |
| 5.. | Payload |
| final | Sum of all preceding bytes modulo 256 |

Exactly `6 + payload_length` bytes are required. With the 64-byte harness the maximum valid payload is 58 bytes. Check failures return, in precedence order: short header `1`, wrong magic `2`, invalid kind `3`, inconsistent length `4`, bad sum `5`. Success returns `0x80000000 | kind << 24 | sequence << 8 | (payload_sum & 255)`.

Directed tests include empty/short input, valid payload sizes 0/1/2/31/58, sequence values 0/1/255/256/0x1234/65535, error paths, truncated packets and trailing bytes. Seeded cases mix random bytes, valid generated packets, and one-bit mutations. Not every mutated packet is invalid: mutations can change semantics while preserving validity, so the compiled reference remains the oracle.

The faulty candidate validates correctly but reads the sequence as little endian. Equal high/low bytes conceal the fault; asymmetric sequence bytes expose it. `a503123400ee` returns reference `0x83123400`, mutant `0x83341200`.

## Lock state machine

States `0 locked`, `1 armed`, `2 open`, `3 fault`; initial state locked.

| State | Timeout (0) | Arm (1) | Unlock (2) | Reset (3) |
| --- | ---: | ---: | ---: | ---: |
| Locked | 0 | 1 | 3 | 0 |
| Armed | 0 | 1 | 2 | 0 |
| Open | 0 | 2 | 2 | 0 |
| Fault | 3 | 3 | 3 | 0 |

An event >=4 increments the invalid-input count and sets fault. Each actual change increments the transition count. Return `invalid_count << 16 | transitions << 8 | final_state`. The C fixture is branch-based; the Python candidate uses this table. Directed histories check successful unlocking, fault persistence, reset recovery, timeout, repeated invalid inputs, every two-event pair over 0..4, and length boundaries. The pair corpus does not constitute exhaustive sequence coverage.
