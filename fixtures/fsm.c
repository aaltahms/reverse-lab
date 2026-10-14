#include <stddef.h>
#include <stdint.h>

/* States: 0 locked, 1 armed, 2 open, 3 fault. Events: 0 timeout,
   1 arm, 2 unlock, 3 reset. Unknown event or premature unlock faults.
   Fault persists until reset. Result: invalid_count<<16 | changes<<8 | state. */
uint32_t evaluate(const uint8_t *data, size_t length) {
    uint32_t state = 0, changes = 0, invalid = 0;
    for (size_t i = 0; i < length; ++i) {
        uint32_t before = state;
        uint8_t event = data[i];
        if (event > 3) { ++invalid; state = 3; }
        else if (event == 3) state = 0;
        else if (state != 3) {
            if (event == 0) state = 0;
            else if (event == 1 && state == 0) state = 1;
            else if (event == 2) state = state == 1 || state == 2 ? 2 : 3;
        }
        if (state != before) ++changes;
    }
    return (invalid << 16) | (changes << 8) | state;
}
