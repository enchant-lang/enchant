// Isolate two compiler decisions on one preallocated, single-channel CPU frame.
// Replay command and measurement boundaries are in journal/03-live-compiler.bl.org.
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef uint8_t byte;
struct frame {
    byte *back, *front1, *alpha1, *front2, *alpha2, *tmp, *out;
    size_t n;
};

static inline byte wide(byte s, byte d, byte a) {
    return ((unsigned)a * s + (255u - a) * d) / 255u;
}

static inline byte narrow(byte s, byte d, byte a) {
    uint16_t n = a * s + (255 - a) * d;
    uint16_t t = n + 1u;
    uint16_t sum = t + (t >> 8);
    return sum >> 8;
}

// The baseline explicitly materializes its intermediate, as a caller of two
// separately compiled passes would. All three runners exclude allocation.
__attribute__((noipa))
static void layer(byte *restrict out, const byte *s, const byte *d,
                  const byte *a, size_t n) {
    for (size_t i = 0; i < n; ++i) out[i] = wide(s[i], d[i], a[i]);
}

static void materialized(struct frame *f) {
    layer(f->tmp, f->front1, f->back, f->alpha1, f->n);
    layer(f->out, f->front2, f->tmp, f->alpha2, f->n);
}

#define FUSED_LOOP(normalize) \
    for (size_t i = 0; i < n; ++i) { \
        byte middle = normalize(s1[i], d[i], a1[i]); \
        out[i] = normalize(s2[i], middle, a2[i]); \
    }

// The output owns a fresh allocation, which justifies restrict on this pointer.
#define INPUTS byte *restrict out, const byte *d, const byte *s1, const byte *a1, \
               const byte *s2, const byte *a2, size_t n
#define ARGS(f) (f)->out, (f)->back, (f)->front1, (f)->alpha1, (f)->front2, (f)->alpha2, (f)->n
__attribute__((noipa)) static void wide_loop(INPUTS) { FUSED_LOOP(wide) }
__attribute__((noipa)) static void narrow_loop(INPUTS) { FUSED_LOOP(narrow) }
static void fused_wide(struct frame *f) { wide_loop(ARGS(f)); }
static void fused_narrow(struct frame *f) { narrow_loop(ARGS(f)); }

static uint64_t now_ns(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts)) abort();
    return (uint64_t)ts.tv_sec * 1000000000u + ts.tv_nsec;
}

static void measure(size_t n) {
    byte *arena = calloc(n, 8);
    if (!arena) abort();
    struct frame f = {arena, arena+n, arena+2*n, arena+3*n, arena+4*n,
                      arena+5*n, arena+6*n, n};
    byte *reference = arena + 7*n;
    uint32_t seed = 42;
    for (size_t i = 0; i < 5*n; ++i) {
        seed = seed * 1664525u + 1013904223u;
        arena[i] = seed >> 24;
    }
    void (*runners[])(struct frame *) = {materialized, fused_wide, fused_narrow};
    const char *names[] = {"materialized", "fused-wide", "fused-narrow"};
    // Independent slow quotient specification outside timing; catches swapped
    // layers even if the three candidate loops make the same mistake.
    for (size_t i = 0; i < n; ++i) {
        unsigned y = f.back[i];
        for (int k = 0; k < 2; ++k) {
            unsigned s = (k ? f.front2 : f.front1)[i];
            unsigned a = (k ? f.alpha2 : f.alpha1)[i];
            long sum = (long)y * 255 + ((long)s - y) * a;
            unsigned q = (unsigned)(sum / 255);
            if (!(255L*q <= sum && sum < 255L*(q+1))) abort();
            y = q;
        }
        reference[i] = y;
    }
    for (int round = -1; round < 9; ++round) {
        for (int slot = 0; slot < 3; ++slot) {
            int k = (slot + round + 3) % 3;
            memset(f.out, 0xa5, n);
            uint64_t start = now_ns();
            runners[k](&f);
            uint64_t elapsed = now_ns() - start;
            if (memcmp(f.out, reference, n)) abort();
            if (round >= 0) printf("%zu,%d,%s,%llu\n", n, round, names[k],
                                   (unsigned long long)elapsed);
        }
    }
    free(arena);
}

int main(void) {
    puts("pixels,round,variant,ns");
    measure(129u*73u);
    measure(1920u*1080u);
    return 0;
}
