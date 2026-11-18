// width is the packed row stride in channels. Each group owns one tile.
__kernel void render(__global const uchar *src, __global uchar *dst,
                     uint width, uint height) {
  size_t x = get_global_id(0), y = get_global_id(1);
  if (x < width && y < height) {
    size_t i = y * width + x;
    dst[i] = (uchar)PIXEL(src[i]);
  }
}
