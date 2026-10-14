#include <stddef.h>
#include <stdint.h>

/* Fletcher-16 over at most 32 bytes. Empty input has checksum zero. */
uint32_t evaluate(const uint8_t *data, size_t length) {
    uint32_t a = 0, b = 0;
    size_t limit = length < 32 ? length : 32;
    for (size_t i = 0; i < limit; ++i) {
        a = (a + data[i]) % 255;
        b = (b + a) % 255;
    }
    return (b << 8) | a;
}
