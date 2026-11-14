#include <stdint.h>
#include <stdatomic.h>
#include <time.h>
#include <errno.h>

static atomic_int entered = 0;
static atomic_int released = 0;
static void delay(uint64_t milliseconds) {
  struct timespec remaining = {milliseconds / 1000, (milliseconds % 1000) * 1000000};
  while (nanosleep(&remaining, &remaining) != 0 && errno == EINTR) {}
}
uint64_t bl_fixture_gated(uint64_t milliseconds) {
  atomic_store_explicit(&entered, 1, memory_order_release);
  while (!atomic_load_explicit(&released, memory_order_acquire)) delay(1);
  delay(milliseconds);
  return milliseconds + 1;
}
uint64_t bl_fixture_entered(uint64_t ignored) {
  (void)ignored;
  return atomic_load_explicit(&entered, memory_order_acquire) != 0;
}
uint64_t bl_fixture_release(uint64_t value) {
  atomic_store_explicit(&released, 1, memory_order_release);
  return value;
}
