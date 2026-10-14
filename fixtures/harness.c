#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <inttypes.h>

uint32_t evaluate(const uint8_t *, size_t);
static int nibble(unsigned char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
static void respond(const unsigned char *line, size_t n, int overflow) {
    uint8_t bytes[64];
    if (overflow || !n) { puts("ERR"); return; }
    if (n == 1 && line[0] == '-') {
        printf("%" PRIu32 "\n", evaluate(bytes, 0)); return;
    }
    if (n % 2) { puts("ERR"); return; }
    for (size_t i = 0; i < n / 2; ++i) {
        int hi = nibble(line[i * 2]), lo = nibble(line[i * 2 + 1]);
        if (hi < 0 || lo < 0) { puts("ERR"); return; }
        bytes[i] = (uint8_t)((hi << 4) | lo);
    }
    printf("%" PRIu32 "\n", evaluate(bytes, n / 2));
}
/* Batch line protocol: '-' means empty; otherwise 1..64 bytes in hex.
   Consume invalid/overlong records without desynchronizing the next line. */
int main(void) {
    unsigned char line[128];
    size_t n = 0;
    int c, overflow = 0;
    while ((c = getchar()) != EOF) {
        if (c == '\n') { respond(line, n, overflow); n = 0; overflow = 0; }
        else if (n < sizeof line) line[n++] = (unsigned char)c;
        else overflow = 1;
    }
    if (n || overflow) respond(line, n, overflow);
    return ferror(stdin) ? 1 : 0;
}
