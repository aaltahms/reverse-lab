#include <stddef.h>
#include <stdint.h>

/* Return the sum of the input bytes, reduced to one byte. */
uint32_t evaluate(const uint8_t *data, size_t length) {
    uint32_t sum = 0;
    for (size_t i = 0; i < length; ++i) sum += data[i];
    return sum & 255u;
}
