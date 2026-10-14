"""Agent-authored table model of state transitions; reference source known."""
# Rows: locked, armed, open, fault. Columns: timeout, arm, unlock, reset.
TRANSITIONS = (
    (0, 1, 3, 0),
    (0, 1, 2, 0),
    (0, 2, 2, 0),
    (3, 3, 3, 0),
)


def reconstruct(data: bytes) -> int:
    state = changes = invalid = 0
    for event in data:
        next_state = TRANSITIONS[state][event] if event < 4 else 3
        changes += next_state != state
        invalid += event >= 4
        state = next_state
    return invalid * 65536 + changes * 256 + state
