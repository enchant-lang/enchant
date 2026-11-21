// Entry: the translated stage runs on one thread with a large stack, since
// Scheme recursion depth becomes Rust stack depth.
#![allow(warnings)]
mod rt;
#[path = "gen/mod.rs"]
mod generated;

// A size-class free-list allocator for small objects (build with --cfg rs_fastalloc).
#[cfg(rs_fastalloc)]
mod fastalloc {
    use std::alloc::{GlobalAlloc, Layout, System};
    use std::sync::atomic::{AtomicBool, Ordering};
    pub struct Fast;
    const CLASSES: usize = 32;
    const CHUNK: usize = 1 << 20;
    static LOCK: AtomicBool = AtomicBool::new(false);
    static mut FREE: [*mut u8; CLASSES] = [std::ptr::null_mut(); CLASSES];
    static mut BUMP: usize = 0;
    static mut END: usize = 0;
    #[inline] fn lock() { while LOCK.compare_exchange_weak(false, true, Ordering::Acquire, Ordering::Relaxed).is_err() { std::hint::spin_loop(); } }
    #[inline] fn unlock() { LOCK.store(false, Ordering::Release); }
    unsafe impl GlobalAlloc for Fast {
        #[inline] unsafe fn alloc(&self, l: Layout) -> *mut u8 { unsafe {
            if l.size() > CLASSES * 16 || l.align() > 16 { return System.alloc(l); }
            let c = (l.size().max(1) + 15) / 16 - 1;
            lock();
            let slot = (&raw mut FREE).cast::<*mut u8>().add(c);
            let head = *slot;
            let p = if !head.is_null() { *slot = *(head as *mut *mut u8); head } else {
                let size = (c + 1) * 16;
                if END - BUMP < size {
                    let chunk = System.alloc(Layout::from_size_align_unchecked(CHUNK, 16));
                    if chunk.is_null() { unlock(); return chunk; }
                    BUMP = chunk as usize; END = BUMP + CHUNK;
                }
                let p = BUMP as *mut u8; BUMP += size; p
            };
            unlock(); p
        } }
        #[inline] unsafe fn dealloc(&self, p: *mut u8, l: Layout) { unsafe {
            if l.size() > CLASSES * 16 || l.align() > 16 { return System.dealloc(p, l); }
            let c = (l.size().max(1) + 15) / 16 - 1;
            lock();
            let slot = (&raw mut FREE).cast::<*mut u8>().add(c);
            *(p as *mut *mut u8) = *slot; *slot = p;
            unlock();
        } }
    }
}
#[cfg(rs_fastalloc)]
#[global_allocator]
static ALLOC: fastalloc::Fast = fastalloc::Fast;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let stack: usize = std::env::var("RS_STACK_MB").ok().and_then(|s| s.parse().ok()).unwrap_or(4096);
    let code = std::thread::Builder::new()
        .stack_size(stack << 20)
        .spawn(move || {
            rt::setup(generated::GNAMES, generated::GSTATIC, generated::SYMS, generated::KSRC, args);
            rt::run_top(|| generated::init())
        })
        .unwrap()
        .join()
        .unwrap_or(72);
    std::process::exit(code);
}
