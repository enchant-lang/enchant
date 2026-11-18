"""Small OpenCL 1.2 binding for a real GPU. No software-device fallback."""
import ctypes as C
from contextlib import ExitStack
import os
from pathlib import Path

P, U, I, S, L = C.c_void_p, C.c_uint, C.c_int, C.c_size_t, C.c_ulonglong
ptr = C.POINTER


class Unavailable(RuntimeError):
    pass


class Device(ExitStack):
    def __init__(self, library, program):
        super().__init__()
        if Path('/run/opengl-driver/etc/OpenCL/vendors').is_dir():
            os.environ.setdefault('OCL_ICD_VENDORS', '/run/opengl-driver/etc/OpenCL/vendors')
        try:
            self.lib = C.CDLL(library)
        except OSError as e:
            raise Unavailable(str(e)) from e
        try:
            self.prepare(program)
        except BaseException:
            self.close()
            raise

    def bind(self, name, result, *args):
        fn = getattr(self.lib, 'cl' + name)
        fn.restype, fn.argtypes = result, args
        return fn

    @staticmethod
    def check(code):
        if code:
            raise RuntimeError(f'OpenCL returned {code}')

    def own(self, kind, handle, err):
        self.check(err.value)
        self.callback(self.bind('Release' + kind, I, P), handle)
        return handle

    def prepare(self, source):
        get = self.bind('GetPlatformIDs', I, U, ptr(P), ptr(U))
        n = U()
        code = get(0, None, C.byref(n))
        if code == -1001 or (code == 0 and not n.value):
            raise Unavailable("no OpenCL platform")
        self.check(code)
        platforms = (P * n.value)()
        self.check(get(n, platforms, None))
        device = P()
        for platform in platforms:
            code = self.bind('GetDeviceIDs', I, P, L, U, ptr(P), ptr(U))(platform, 4, 1, C.byref(device), None)
            if code != -1:
                self.check(code)
                break
        else:
            raise Unavailable("no CL_DEVICE_TYPE_GPU")
        info = self.bind('GetDeviceInfo', I, P, U, S, P, ptr(S))
        self.info = {}
        for key, field in [('device', 0x102b), ('driver', 0x102d)]:
            buf = C.create_string_buffer(1024)
            self.check(info(device, field, len(buf), buf, None))
            self.info[key] = buf.value.decode()
        err = I()
        self.ctx = self.own('Context', self.bind('CreateContext', P, P, U, ptr(P), P, P, ptr(I))(
            None, 1, C.byref(device), None, None, C.byref(err)), err)
        self.queue = self.own('CommandQueue', self.bind('CreateCommandQueue', P, P, P, L, ptr(I))(
            self.ctx, device, 0, C.byref(err)), err)
        src = C.c_char_p(source.encode())
        program = self.own('Program', self.bind('CreateProgramWithSource', P, P, U, ptr(C.c_char_p), ptr(S), ptr(I))(
            self.ctx, 1, C.byref(src), None, C.byref(err)), err)
        status = self.bind('BuildProgram', I, P, U, ptr(P), C.c_char_p, P, P)(program, 1, C.byref(device), b'-cl-std=CL1.2', None, None)
        if status:
            log = C.create_string_buffer(65536)
            self.bind('GetProgramBuildInfo', I, P, P, U, S, P, ptr(S))(program, device, 0x1183, len(log), log, None)
            raise RuntimeError(log.value.decode())
        self.kernel = self.own('Kernel', self.bind('CreateKernel', P, P, C.c_char_p, ptr(I))(program, b'render', C.byref(err)), err)
        self.buffer = self.bind('CreateBuffer', P, P, L, S, P, ptr(I))
        self.arg = self.bind('SetKernelArg', I, P, U, S, P)
        self.launch = self.bind('EnqueueNDRangeKernel', I, P, P, U, ptr(S), ptr(S), ptr(S), U, P, P)
        self.read = self.bind('EnqueueReadBuffer', I, P, P, U, S, S, P, U, P, P)

    def render(self, data, width, height, tile):
        if len(data) != width * height or not 1 <= tile <= 16:
            raise ValueError("invalid OpenCL launch geometry")
        if not data:
            return b''
        err = I()
        with ExitStack() as frame:
            def alloc(flags, host):
                buf = P(self.buffer(self.ctx, flags, len(data), host, C.byref(err)))
                self.check(err.value)
                frame.callback(self.bind('ReleaseMemObject', I, P), buf)
                return buf
            src, dst = alloc(4 | 32, C.c_char_p(data)), alloc(2, None)
            for index, val in enumerate((src, dst, U(width), U(height))):
                self.check(self.arg(self.kernel, index, C.sizeof(val), C.byref(val)))
            grid = (S * 2)(*((dim + tile - 1) // tile * tile for dim in (width, height)))
            self.check(self.launch(self.queue, self.kernel, 2, None, grid, (S * 2)(tile, tile), 0, None, None))
            out = C.create_string_buffer(len(data))
            self.check(self.read(self.queue, dst, 1, 0, len(data), out, 0, None, None))
            return out.raw
