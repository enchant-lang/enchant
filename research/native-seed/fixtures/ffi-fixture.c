#include <stdint.h>
#include <time.h>
#include <errno.h>
uint64_t bl_fixture_blocking(uint64_t milliseconds) {
  struct timespec remaining = {milliseconds / 1000, (milliseconds % 1000) * 1000000};
  while (nanosleep(&remaining, &remaining) != 0 && errno == EINTR) {}
  return milliseconds + 1;
}
