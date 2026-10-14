#include <stddef.h>
#include <stdint.h>

/* Wire: A5 kind seq_hi seq_lo payload_length payload... sum8.
   Success: bit31 | kind<<24 | sequence<<8 | payload_sum8.
   Error precedence: short=1, magic=2, kind=3, length=4, sum=5. */
uint32_t evaluate(const uint8_t *data, size_t length) {
    if (length < 6) return 1;
    if (data[0] != 0xA5) return 2;
    if (data[1] > 7) return 3;
    if (length != (size_t)data[4] + 6) return 4;
    uint32_t check = 0, payload = 0;
    for (size_t i = 0; i < length - 1; ++i) check += data[i];
    if ((check & 255) != data[length - 1]) return 5;
    for (size_t i = 5; i < length - 1; ++i) payload += data[i];
    uint32_t sequence = ((uint32_t)data[2] << 8) | data[3];
    return UINT32_C(0x80000000) | ((uint32_t)data[1] << 24)
           | (sequence << 8) | (payload & 255);
}
