/* The generated channel functions and PIXEL are prepended by the driver. */
void render(const unsigned char *src, unsigned char *dst, unsigned width,
            unsigned height, unsigned tile, int threads) {
  #pragma omp parallel for collapse(2) num_threads(threads) if(threads > 1)
  for (unsigned by = 0; by < height; by += tile)
    for (unsigned bx = 0; bx < width; bx += tile)
      for (unsigned y = by; y < height && y < by + tile; ++y)
        for (unsigned x = bx; x < width && x < bx + tile; ++x) {
          unsigned i = y * width + x;
          dst[i] = PIXEL(src[i]);
        }
}
