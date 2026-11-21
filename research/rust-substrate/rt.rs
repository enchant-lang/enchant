//! Runtime for the Scheme subset the native seed emits, without a collector:
//! every heap value is reference counted. Single threaded.
#![allow(warnings)]
use std::cell::{Cell, RefCell, UnsafeCell};
use std::collections::HashMap;
use std::ffi::{c_char, c_void, CString};
use std::hash::{Hash, Hasher};
use std::panic::{catch_unwind, resume_unwind, AssertUnwindSafe};
use std::rc::{Rc, Weak};

pub struct Clo { pub name: &'static str, pub f: Box<dyn Fn(&[&V]) -> V> }
pub struct SStr(pub UnsafeCell<Vec<char>>);
pub struct SVec(pub UnsafeCell<Vec<V>>);
pub struct PairS(pub V, pub V);
pub struct VCell(UnsafeCell<V>);
pub type Bx = Rc<VCell>;
pub struct Table { kind: u8, map: RefCell<HashMap<HKey, (u64, V)>>, seq: Cell<u64> }
pub enum Port { Out(RefCell<String>), Stdout, Stderr, In(RefCell<(Vec<char>, usize)>) }

#[derive(Clone)]
pub enum V {
    Fix(i64), Bool(bool), Char(char), Sym(u32), Null, Void, Eof, Unbound, Flo(f64), Ptr(usize),
    Big(Rc<i128>), Rat(Rc<(i64, i64)>), Str(Rc<SStr>), Pair(Rc<PairS>), Vec(Rc<SVec>), Proc(Rc<Clo>),
    Table(Rc<Table>), Port(Rc<Port>), Err(Rc<(V, V)>),
}

impl Drop for PairS {
    // Unlink a long cdr chain iteratively; the derived drop would recurse per element.
    fn drop(&mut self) {
        let mut next = std::mem::replace(&mut self.1, V::Null);
        loop {
            match next {
                V::Pair(rc) => match Rc::try_unwrap(rc) {
                    Ok(mut p) => { next = std::mem::replace(&mut p.1, V::Null); }
                    Err(_) => break,
                },
                _ => break,
            }
        }
    }
}
impl SStr { #[inline] pub fn c(&self) -> &mut Vec<char> { unsafe { &mut *self.0.get() } } }
impl SVec { #[inline] pub fn v(&self) -> &mut Vec<V> { unsafe { &mut *self.0.get() } } }
impl VCell {
    #[inline] pub fn get(&self) -> V { unsafe { (*self.0.get()).clone() } }
    #[inline] pub fn set(&self, v: V) { unsafe { let old = std::mem::replace(&mut *self.0.get(), v); drop(old); } }
}
#[inline] pub fn bx(v: V) -> Bx { Rc::new(VCell(UnsafeCell::new(v))) }

// ---- globals, symbols, constants --------------------------------------------------------
const GCAP: usize = 1 << 20;
static mut G: Vec<V> = Vec::new();
static mut GRAVE: Vec<V> = Vec::new();
static mut K: Vec<V> = Vec::new();
static mut GNAME: Option<HashMap<String, usize>> = None;
static mut GSTAT: &[bool] = &[];
static mut GN: Vec<String> = Vec::new();
static mut SYMN: Vec<&'static str> = Vec::new();
static mut SYMI: Option<HashMap<&'static str, u32>> = None;
static mut OUTS: Vec<V> = Vec::new();
static mut STDOUT: String = String::new();
static mut ARGS: Vec<String> = Vec::new();
static mut NEXT_ID: u64 = 0;
pub static mut STATS: [u64; 8] = [0; 8]; // throws, evals, eval ns, interpreted calls, interpreted ns (outermost), depth
#[inline] fn stat(i: usize, n: u64) { unsafe { (*(&raw mut STATS))[i] += n; } }
fn now_ns() -> u64 { static mut T0: Option<std::time::Instant> = None; unsafe { let t = &mut *(&raw mut T0); t.get_or_insert_with(std::time::Instant::now).elapsed().as_nanos() as u64 } }
struct Interp(bool, u64);
impl Interp { #[inline] fn enter() -> Interp { unsafe { let s = &mut *(&raw mut STATS); s[3] += 1; s[5] += 1; if s[5] == 1 && s[6] == 1 { Interp(true, now_ns()) } else { Interp(false, 0) } } } }
impl Drop for Interp { fn drop(&mut self) { unsafe { let s = &mut *(&raw mut STATS); s[5] -= 1; if self.0 { s[4] += now_ns() - self.1; } } } }

#[inline] pub fn g(i: usize) -> &'static V { unsafe { &*(*(&raw const G)).as_ptr().add(i) } }
pub fn gset(i: usize, v: V) {
    unsafe {
        let slot = (*(&raw mut G)).as_mut_ptr().add(i);
        let old = std::mem::replace(&mut *slot, v);
        match old { V::Unbound | V::Void => {}, o => (*(&raw mut GRAVE)).push(o) }
    }
}
#[inline] pub fn kc(i: usize) -> &'static V { unsafe { &*(*(&raw const K)).as_ptr().add(i) } }
pub fn global_slot(name: &str) -> usize {
    unsafe {
        let m = (*(&raw mut GNAME)).as_mut().unwrap();
        if let Some(i) = m.get(name) { return *i; }
        let gv = &mut *(&raw mut G);
        if gv.len() >= GCAP { panic!("global table full"); }
        gv.push(V::Unbound); m.insert(name.to_string(), gv.len() - 1); gv.len() - 1
    }
}
fn gset_dynamic(i: usize, v: V) {
    unsafe { let gs: &[bool] = *(&raw const GSTAT); if i < gs.len() && gs[i] { eprintln!("rust-substrate: dynamic rebinding of direct function {}", { let n: &Vec<String> = &*(&raw const GN); n[i].clone() }); } }
    gset(i, v)
}
pub fn intern(s: &str) -> u32 {
    unsafe {
        let m = (*(&raw mut SYMI)).as_mut().unwrap();
        if let Some(i) = m.get(s) { return *i; }
        let leaked: &'static str = Box::leak(s.to_string().into_boxed_str());
        let n = &mut *(&raw mut SYMN);
        n.push(leaked); m.insert(leaked, (n.len() - 1) as u32); (n.len() - 1) as u32
    }
}
#[inline] pub fn sym_name(i: u32) -> &'static str { unsafe { let n: &Vec<&'static str> = &*(&raw const SYMN); n[i as usize] } }
pub fn setup(gnames: &[&str], gstatic: &'static [bool], syms: &[&str], ksrc: &[&str], args: Vec<String>) {
    unsafe {
        if std::env::var("RS_STATS").is_ok() { (*(&raw mut STATS))[6] = 1; }
        SYMI = Some(HashMap::new()); GNAME = Some(HashMap::new()); GSTAT = gstatic; ARGS = args;
        for s in syms { intern(s); }
        let gv = &mut *(&raw mut G);
        gv.reserve_exact(GCAP);
        for (i, n) in gnames.iter().enumerate() { (*(&raw mut GN)).push(n.to_string()); gv.push(V::Unbound); (*(&raw mut GNAME)).as_mut().unwrap().insert(n.to_string(), i); }
        let k = &mut *(&raw mut K);
        for s in ksrc {
            let chars: Vec<char> = s.chars().collect(); let mut pos = 0;
            k.push(read_datum(&chars, &mut pos));
        }
    }
}
pub fn finish() { flush_stdout(); unsafe { if (*(&raw const STATS))[6] == 1 { let s = &*(&raw const STATS); eprintln!("rust-substrate stats: throws {}  evals {} ({:.2} s)  interpreted calls {} ({:.2} s inclusive, outermost)", s[0], s[1], s[2] as f64 / 1e9, s[3], s[4] as f64 / 1e9); } } }
fn flush_stdout() {
    unsafe { use std::io::Write; let s = &mut *(&raw mut STDOUT); let _ = std::io::stdout().write_all(s.as_bytes()); let _ = std::io::stdout().flush(); s.clear(); }
}

// ---- procedures and control -------------------------------------------------------------
#[inline] pub fn mk<F: Fn(&[&V]) -> V + 'static>(f: F) -> V { V::Proc(Rc::new(Clo { name: "", f: Box::new(f) })) }
pub fn mkn<F: Fn(&[&V]) -> V + 'static>(name: &'static str, f: F) -> V { V::Proc(Rc::new(Clo { name, f: Box::new(f) })) }
pub fn mkrec<F: Fn(&V, &[&V]) -> V + 'static>(f: F) -> V {
    V::Proc(Rc::new_cyclic(|w: &Weak<Clo>| {
        let w = w.clone();
        Clo { name: "", f: Box::new(move |a: &[&V]| { let me = V::Proc(w.upgrade().unwrap()); f(&me, a) }) }
    }))
}
#[inline] pub fn call(f: &V, a: &[&V]) -> V { match f { V::Proc(c) => (c.f)(a), _ => not_proc(f) } }
#[cold] fn not_proc(f: &V) -> V { fail("attempt to apply non-procedure", &[f]) }
struct Thrown(V);
unsafe impl Send for Thrown {}
struct Escape(u64, V);
unsafe impl Send for Escape {}
#[cold] pub fn throw(v: V) -> ! { stat(0, 1); resume_unwind(Box::new(Thrown(v))) }
#[cold] pub fn fail(msg: &str, irritants: &[&V]) -> V { throw(V::Err(Rc::new((mkstr(msg), list_from(irritants))))) }
#[cold] pub fn arity_error(n: usize) -> V { fail("wrong number of arguments", &[&V::Fix(n as i64)]) }
pub fn p_error(a: &[&V]) -> V { throw(V::Err(Rc::new((a[0].clone(), list_from(&a[1..]))))) }
pub fn p_raise(v: &V) -> V { throw(v.clone()) }
pub fn p_with_exception_catcher(handler: &V, thunk: &V) -> V {
    match catch_unwind(AssertUnwindSafe(|| call(thunk, &[]))) {
        Ok(v) => v,
        Err(p) => match p.downcast::<Thrown>() { Ok(t) => call(handler, &[&t.0]), Err(p) => resume_unwind(p) },
    }
}
pub fn p_call_with_current_continuation(f: &V) -> V {
    let id = unsafe { NEXT_ID += 1; NEXT_ID };
    let k = mk(move |a: &[&V]| -> V { resume_unwind(Box::new(Escape(id, if a.is_empty() { V::Void } else { a[0].clone() }))) });
    match catch_unwind(AssertUnwindSafe(|| call(f, &[&k]))) {
        Ok(v) => v,
        Err(p) => match p.downcast::<Escape>() {
            Ok(e) => if e.0 == id { e.1.clone() } else { resume_unwind(e) },
            Err(p) => resume_unwind(p),
        },
    }
}
pub fn p_dynamic_wind(before: &V, thunk: &V, after: &V) -> V {
    call(before, &[]);
    let r = catch_unwind(AssertUnwindSafe(|| call(thunk, &[])));
    call(after, &[]);
    match r { Ok(v) => v, Err(p) => resume_unwind(p) }
}
pub fn p_make_parameter(v: &V) -> V {
    let cell = bx(v.clone());
    mk(move |a: &[&V]| -> V { if a.is_empty() { cell.get() } else { cell.set(a[0].clone()); V::Void } })
}
pub fn p_apply(f: &V, l: &V) -> V { let xs = list_vec(l); let r: Vec<&V> = xs.iter().collect(); call(f, &r) }
/// Run `f`; an uncaught Scheme exception is printed and becomes exit status 70.
pub fn run_top<F: FnOnce()>(f: F) -> i32 {
    match catch_unwind(AssertUnwindSafe(f)) {
        Ok(()) => { finish(); 0 }
        Err(p) => {
            finish();
            match p.downcast::<Thrown>() {
                Ok(t) => { let mut s = String::new(); show_exception(&t.0, &mut s); eprint!("uncaught: {}", s); 70 }
                Err(p) => { if p.downcast_ref::<Escape>().is_some() { eprintln!("continuation invoked after its extent"); } 71 }
            }
        }
    }
}

// ---- predicates ---------------------------------------------------------------------------
#[inline] pub fn truthy(v: &V) -> bool { !matches!(v, V::Bool(false)) }
#[inline] pub fn is_false(v: &V) -> bool { matches!(v, V::Bool(false)) }
#[inline] pub fn is_sym(v: &V, i: u32) -> bool { matches!(v, V::Sym(j) if *j == i) }
#[inline] pub fn is_fix(v: &V, i: i64) -> bool { matches!(v, V::Fix(j) if *j == i) }
#[inline] pub fn pb_eq_p(a: &V, b: &V) -> bool {
    match (a, b) {
        (V::Fix(x), V::Fix(y)) => x == y, (V::Sym(x), V::Sym(y)) => x == y, (V::Bool(x), V::Bool(y)) => x == y,
        (V::Char(x), V::Char(y)) => x == y, (V::Null, V::Null) | (V::Void, V::Void) | (V::Eof, V::Eof) | (V::Unbound, V::Unbound) => true,
        (V::Vec(x), V::Vec(y)) => Rc::ptr_eq(x, y), (V::Pair(x), V::Pair(y)) => Rc::ptr_eq(x, y),
        (V::Str(x), V::Str(y)) => Rc::ptr_eq(x, y), (V::Proc(x), V::Proc(y)) => Rc::ptr_eq(x, y),
        (V::Table(x), V::Table(y)) => Rc::ptr_eq(x, y), (V::Port(x), V::Port(y)) => Rc::ptr_eq(x, y),
        (V::Big(x), V::Big(y)) => Rc::ptr_eq(x, y), (V::Rat(x), V::Rat(y)) => Rc::ptr_eq(x, y),
        (V::Err(x), V::Err(y)) => Rc::ptr_eq(x, y), (V::Flo(x), V::Flo(y)) => x.to_bits() == y.to_bits(),
        (V::Ptr(x), V::Ptr(y)) => x == y, _ => false,
    }
}
pub fn pb_eqv_p(a: &V, b: &V) -> bool {
    match (a, b) { (V::Big(x), V::Big(y)) => **x == **y, (V::Rat(x), V::Rat(y)) => **x == **y, _ => pb_eq_p(a, b) }
}
pub fn pb_equal_p(a: &V, b: &V) -> bool {
    let (mut a, mut b) = (a.clone(), b.clone());
    loop {
        match (&a, &b) {
            (V::Pair(x), V::Pair(y)) => {
                if Rc::ptr_eq(x, y) { return true; }
                if !pb_equal_p(&x.0, &y.0) { return false; }
                let (na, nb) = (x.1.clone(), y.1.clone()); a = na; b = nb;
            }
            (V::Str(x), V::Str(y)) => return x.c() == y.c(),
            (V::Vec(x), V::Vec(y)) => { let (x, y) = (x.v(), y.v()); return x.len() == y.len() && x.iter().zip(y.iter()).all(|(p, q)| pb_equal_p(p, q)); }
            _ => return pb_eqv_p(&a, &b),
        }
    }
}
#[inline] pub fn pb_null_p(v: &V) -> bool { matches!(v, V::Null) }
#[inline] pub fn pb_pair_p(v: &V) -> bool { matches!(v, V::Pair(_)) }
#[inline] pub fn pb_vector_p(v: &V) -> bool { matches!(v, V::Vec(_)) }
#[inline] pub fn pb_procedure_p(v: &V) -> bool { matches!(v, V::Proc(_)) }
#[inline] pub fn pb_string_p(v: &V) -> bool { matches!(v, V::Str(_)) }
#[inline] pub fn pb_symbol_p(v: &V) -> bool { matches!(v, V::Sym(_)) }
#[inline] pub fn pb_boolean_p(v: &V) -> bool { matches!(v, V::Bool(_)) }
#[inline] pub fn pb_fixnum_p(v: &V) -> bool { matches!(v, V::Fix(i) if *i >= -(1 << 60) && *i < (1 << 60)) }
#[inline] pub fn pb_exact_integer_p(v: &V) -> bool { matches!(v, V::Fix(_) | V::Big(_)) }
pub fn pb_integer_p(v: &V) -> bool { match v { V::Fix(_) | V::Big(_) => true, V::Flo(f) => f.fract() == 0.0 && f.is_finite(), _ => false } }
pub fn pb_number_p(v: &V) -> bool { matches!(v, V::Fix(_) | V::Big(_) | V::Flo(_) | V::Rat(_)) }
pub fn pb_exact_p(v: &V) -> bool { match v { V::Fix(_) | V::Big(_) | V::Rat(_) => true, V::Flo(_) => false, _ => { fail("exact?: not a number", &[v]); false } } }
pub fn pb_list_p(v: &V) -> bool { let mut x = v; loop { match x { V::Null => return true, V::Pair(p) => x = &p.1, _ => return false } } }
pub fn pb_zero_p(v: &V) -> bool { match v { V::Fix(i) => *i == 0, V::Flo(f) => *f == 0.0, _ => false } }
pub fn pb_even_p(v: &V) -> bool { int(v) % 2 == 0 }
#[inline] pub fn pb_eof_object_p(v: &V) -> bool { matches!(v, V::Eof) }
#[inline] pub fn pb_uninterned_symbol_p(_v: &V) -> bool { false }
#[inline] pub fn pb_not(v: &V) -> bool { is_false(v) }
#[inline] pub fn pb_hhunbound_p(v: &V) -> bool { matches!(v, V::Unbound) }
#[inline] pub fn pb_chareq_p(a: &V, b: &V) -> bool { ch(a) == ch(b) }
#[inline] pub fn pb_charlteq_p(a: &V, b: &V) -> bool { ch(a) <= ch(b) }
#[inline] pub fn pb_chargteq_p(a: &V, b: &V) -> bool { ch(a) >= ch(b) }
pub fn pb_stringeq_p(a: &V, b: &V) -> bool { st(a).c() == st(b).c() }

// ---- numbers ------------------------------------------------------------------------------
#[cold] fn bad(what: &str, v: &V) -> ! { fail(what, &[v]); unreachable!() }
#[inline] fn fx(v: &V) -> i64 { match v { V::Fix(i) => *i, _ => bad("not a fixnum", v) } }
fn int(v: &V) -> i128 { match v { V::Fix(i) => *i as i128, V::Big(b) => **b, V::Flo(f) if f.fract() == 0.0 => *f as i128, _ => bad("not an integer", v) } }
fn norm(i: i128) -> V { if i >= i64::MIN as i128 && i <= i64::MAX as i128 { V::Fix(i as i64) } else { V::Big(Rc::new(i)) } }
fn f64of(v: &V) -> f64 { match v { V::Fix(i) => *i as f64, V::Big(b) => **b as f64, V::Flo(f) => *f, V::Rat(r) => r.0 as f64 / r.1 as f64, _ => bad("not a number", v) } }
fn inexact(a: &V, b: &V) -> bool { matches!(a, V::Flo(_) | V::Rat(_)) || matches!(b, V::Flo(_) | V::Rat(_)) }
fn ck(r: Option<i128>) -> V { match r { Some(i) => norm(i), None => panic!("integer beyond 128 bits") } }
#[inline] pub fn num_add(a: &V, b: &V) -> V {
    if let (V::Fix(x), V::Fix(y)) = (a, b) { if let Some(r) = x.checked_add(*y) { return V::Fix(r); } }
    if inexact(a, b) { V::Flo(f64of(a) + f64of(b)) } else { ck(int(a).checked_add(int(b))) }
}
#[inline] pub fn num_sub(a: &V, b: &V) -> V {
    if let (V::Fix(x), V::Fix(y)) = (a, b) { if let Some(r) = x.checked_sub(*y) { return V::Fix(r); } }
    if inexact(a, b) { V::Flo(f64of(a) - f64of(b)) } else { ck(int(a).checked_sub(int(b))) }
}
#[inline] pub fn num_mul(a: &V, b: &V) -> V {
    if let (V::Fix(x), V::Fix(y)) = (a, b) { if let Some(r) = x.checked_mul(*y) { return V::Fix(r); } }
    if inexact(a, b) { V::Flo(f64of(a) * f64of(b)) } else { ck(int(a).checked_mul(int(b))) }
}
fn gcd(a: i128, b: i128) -> i128 { let (mut a, mut b) = (a.abs(), b.abs()); while b != 0 { let t = a % b; a = b; b = t; } a }
pub fn num_div(a: &V, b: &V) -> V {
    if inexact(a, b) { return V::Flo(f64of(a) / f64of(b)); }
    let (x, y) = (int(a), int(b));
    if y == 0 { return fail("division by zero", &[a]); }
    if x % y == 0 { return norm(x / y); }
    let d = gcd(x, y); let (mut n, mut m) = (x / d, y / d); if m < 0 { n = -n; m = -m; }
    V::Rat(Rc::new((n as i64, m as i64)))
}
pub fn p_add(a: &[&V]) -> V { match a.len() { 0 => V::Fix(0), 2 => num_add(a[0], a[1]), _ => { let mut r = a[0].clone(); for x in &a[1..] { r = num_add(&r, x); } r } } }
pub fn p_mul(a: &[&V]) -> V { match a.len() { 0 => V::Fix(1), 2 => num_mul(a[0], a[1]), _ => { let mut r = a[0].clone(); for x in &a[1..] { r = num_mul(&r, x); } r } } }
pub fn p_sub(a: &[&V]) -> V { match a.len() { 1 => num_sub(&V::Fix(0), a[0]), 2 => num_sub(a[0], a[1]), _ => { let mut r = a[0].clone(); for x in &a[1..] { r = num_sub(&r, x); } r } } }
pub fn p_div(a: &[&V]) -> V { match a.len() { 1 => num_div(&V::Fix(1), a[0]), _ => { let mut r = a[0].clone(); for x in &a[1..] { r = num_div(&r, x); } r } } }
fn cmp(a: &V, b: &V) -> std::cmp::Ordering {
    if let (V::Fix(x), V::Fix(y)) = (a, b) { return x.cmp(y); }
    if inexact(a, b) { f64of(a).partial_cmp(&f64of(b)).unwrap_or(std::cmp::Ordering::Greater) } else { int(a).cmp(&int(b)) }
}
#[inline] pub fn pb_lt(a: &V, b: &V) -> bool { cmp(a, b).is_lt() }
#[inline] pub fn pb_gt(a: &V, b: &V) -> bool { cmp(a, b).is_gt() }
#[inline] pub fn pb_lteq(a: &V, b: &V) -> bool { cmp(a, b).is_le() }
#[inline] pub fn pb_gteq(a: &V, b: &V) -> bool { cmp(a, b).is_ge() }
#[inline] pub fn pb_eq(a: &V, b: &V) -> bool { cmp(a, b).is_eq() }
#[inline] pub fn pb_fxlt(a: &V, b: &V) -> bool { fx(a) < fx(b) }
#[inline] pub fn pb_fxgt(a: &V, b: &V) -> bool { fx(a) > fx(b) }
#[inline] pub fn pb_fxlteq(a: &V, b: &V) -> bool { fx(a) <= fx(b) }
#[inline] pub fn pb_fxgteq(a: &V, b: &V) -> bool { fx(a) >= fx(b) }
#[inline] pub fn pb_fxeq(a: &V, b: &V) -> bool { fx(a) == fx(b) }
#[inline] pub fn p_fxadd(a: &V, b: &V) -> V { V::Fix(fx(a).wrapping_add(fx(b))) }
#[inline] pub fn p_fxsub(a: &V, b: &V) -> V { V::Fix(fx(a).wrapping_sub(fx(b))) }
#[inline] pub fn p_fxmul(a: &V, b: &V) -> V { V::Fix(fx(a).wrapping_mul(fx(b))) }
#[inline] pub fn p_fxquotient(a: &V, b: &V) -> V { V::Fix(fx(a) / fx(b)) }
#[inline] pub fn p_fxmin(a: &V, b: &V) -> V { V::Fix(fx(a).min(fx(b))) }
pub fn p_quotient(a: &V, b: &V) -> V { let y = int(b); if y == 0 { return fail("quotient: division by zero", &[a]); } norm(int(a) / y) }
pub fn p_remainder(a: &V, b: &V) -> V { let y = int(b); if y == 0 { return fail("remainder: division by zero", &[a]); } norm(int(a) % y) }
pub fn p_modulo(a: &V, b: &V) -> V { let y = int(b); if y == 0 { return fail("modulo: division by zero", &[a]); } norm(int(a).rem_euclid(y) + if y < 0 && int(a).rem_euclid(y) != 0 { y } else { 0 }) }
pub fn p_expt(a: &V, b: &V) -> V {
    if let (false, V::Fix(e)) = (inexact(a, b), b) { if *e >= 0 { return ck(int(a).checked_pow(*e as u32)); } }
    V::Flo(f64of(a).powf(f64of(b)))
}
pub fn p_abs(a: &V) -> V { match a { V::Flo(f) => V::Flo(f.abs()), _ => norm(int(a).abs()) } }
pub fn p_max(a: &V, b: &V) -> V { if cmp(a, b).is_ge() { a.clone() } else { b.clone() } }
pub fn p_min(a: &V, b: &V) -> V { if cmp(a, b).is_le() { a.clone() } else { b.clone() } }
pub fn p_exact_to_inexact(a: &V) -> V { V::Flo(f64of(a)) }
pub fn p_inexact_to_exact(a: &V) -> V { match a { V::Flo(f) if f.fract() == 0.0 => norm(*f as i128), V::Flo(_) => panic!("inexact->exact of a fraction"), _ => a.clone() } }
pub fn p_truncate(a: &V) -> V { match a { V::Flo(f) => V::Flo(f.trunc()), V::Rat(r) => V::Fix(r.0 / r.1), _ => a.clone() } }
pub fn p_floor(a: &V) -> V { match a { V::Flo(f) => V::Flo(f.floor()), V::Rat(r) => V::Fix(r.0.div_euclid(r.1)), _ => a.clone() } }
pub fn p_numerator(a: &V) -> V { match a { V::Rat(r) => V::Fix(r.0), _ => a.clone() } }
pub fn p_denominator(a: &V) -> V { match a { V::Rat(r) => V::Fix(r.1), _ => V::Fix(1) } }
pub fn p_arithmetic_shift(a: &V, b: &V) -> V { let (x, k) = (int(a), fx(b)); if k >= 0 { ck(x.checked_mul(1i128.checked_shl(k as u32).expect("shift"))) } else { norm(x >> ((-k).min(127) as u32)) } }
pub fn p_bitwise_not(a: &V) -> V { norm(!int(a)) }
fn fmt_flo(f: f64, out: &mut String) {
    if f.is_nan() { out.push_str("+nan.0") } else if f.is_infinite() { out.push_str(if f > 0.0 { "+inf.0" } else { "-inf.0" }) }
    else if f.fract() == 0.0 && f.abs() < 1e21 { out.push_str(&format!("{:.1}", f)) } else { out.push_str(&format!("{}", f)) }
}
fn radix_str(mut x: i128, r: i128) -> String {
    if x == 0 { return "0".into(); }
    let neg = x < 0; let mut d = Vec::new();
    while x != 0 { d.push(std::char::from_digit((x % r).unsigned_abs() as u32, r as u32).unwrap()); x /= r; }
    if neg { d.push('-'); }
    d.iter().rev().collect()
}
pub fn p_number_to_string(a: &[&V]) -> V {
    let r = if a.len() > 1 { fx(a[1]) as i128 } else { 10 };
    match a[0] { V::Flo(f) => { let mut s = String::new(); fmt_flo(*f, &mut s); mkstr(&s) }, V::Rat(q) => mkstr(&format!("{}/{}", q.0, q.1)), v => mkstr(&radix_str(int(v), r)) }
}
pub fn parse_number(s: &str) -> Option<V> {
    if s.is_empty() { return None; }
    let b = s.as_bytes();
    let digits = if b[0] == b'-' || b[0] == b'+' { &s[1..] } else { s };
    if !digits.is_empty() && digits.bytes().all(|c| c.is_ascii_digit()) { return s.trim_start_matches('+').parse::<i128>().ok().map(norm); }
    if s == "+inf.0" { return Some(V::Flo(f64::INFINITY)); }
    if s == "-inf.0" { return Some(V::Flo(f64::NEG_INFINITY)); }
    if let Some((n, d)) = s.split_once('/') { if let (Ok(n), Ok(d)) = (n.parse::<i64>(), d.parse::<i64>()) { if d != 0 { return Some(num_div(&V::Fix(n), &V::Fix(d))); } } }
    if digits.bytes().next().map_or(false, |c| c.is_ascii_digit() || c == b'.') && digits.bytes().any(|c| c.is_ascii_digit())
        && digits.bytes().all(|c| c.is_ascii_digit() || matches!(c, b'.' | b'e' | b'E' | b'-' | b'+')) { return s.parse::<f64>().ok().map(V::Flo); }
    None
}
pub fn p_string_to_number(a: &V) -> V { let s: String = st(a).c().iter().collect(); parse_number(&s).unwrap_or(V::Bool(false)) }

// ---- pairs and lists ------------------------------------------------------------------------
#[inline] pub fn p_cons(a: &V, b: &V) -> V { V::Pair(Rc::new(PairS(a.clone(), b.clone()))) }
#[inline] fn cons(a: V, b: V) -> V { V::Pair(Rc::new(PairS(a, b))) }
#[inline] fn pr(v: &V) -> &PairS { match v { V::Pair(p) => p, _ => bad("not a pair", v) } }
#[inline] pub fn p_car(v: &V) -> V { pr(v).0.clone() }
#[inline] pub fn p_cdr(v: &V) -> V { pr(v).1.clone() }
pub fn p_cadr(v: &V) -> V { pr(&pr(v).1).0.clone() }
pub fn p_cddr(v: &V) -> V { pr(&pr(v).1).1.clone() }
pub fn p_caddr(v: &V) -> V { pr(&pr(&pr(v).1).1).0.clone() }
pub fn p_cadddr(v: &V) -> V { pr(&pr(&pr(&pr(v).1).1).1).0.clone() }
pub fn p_caar(v: &V) -> V { pr(&pr(v).0).0.clone() }
pub fn p_cdar(v: &V) -> V { pr(&pr(v).0).1.clone() }
pub fn p_cadar(v: &V) -> V { pr(&pr(&pr(v).0).1).0.clone() }
pub fn list_from(a: &[&V]) -> V { let mut r = V::Null; for x in a.iter().rev() { r = cons((*x).clone(), r); } r }
fn list_of(a: Vec<V>) -> V { let mut r = V::Null; for x in a.into_iter().rev() { r = cons(x, r); } r }
pub fn list_vec(l: &V) -> Vec<V> { let mut out = Vec::new(); let mut x = l; loop { match x { V::Pair(p) => { out.push(p.0.clone()); x = &p.1; } V::Null => return out, _ => bad("not a proper list", l) } } }
pub fn p_list(a: &[&V]) -> V { list_from(a) }
pub fn p_length(l: &V) -> V { let mut n = 0; let mut x = l; loop { match x { V::Pair(p) => { n += 1; x = &p.1; } V::Null => return V::Fix(n), _ => bad("length: not a proper list", l) } } }
pub fn p_reverse(l: &V) -> V { let mut r = V::Null; let mut x = l; loop { match x { V::Pair(p) => { r = cons(p.0.clone(), r); x = &p.1; } V::Null => return r, _ => bad("reverse: improper list", l) } } }
pub fn p_append(a: &[&V]) -> V {
    if a.is_empty() { return V::Null; }
    let mut r = a[a.len() - 1].clone();
    for l in a[..a.len() - 1].iter().rev() { for x in list_vec(l).into_iter().rev() { r = cons(x, r); } }
    r
}
pub fn p_list_ref(l: &V, i: &V) -> V { let mut x = l; for _ in 0..fx(i) { x = &pr(x).1; } pr(x).0.clone() }
fn mem(x: &V, l: &V, eq: fn(&V, &V) -> bool) -> V { let mut c = l.clone(); loop { let n = match &c { V::Pair(p) => { if eq(x, &p.0) { return c.clone(); } p.1.clone() } _ => return V::Bool(false) }; c = n; } }
pub fn p_memq(x: &V, l: &V) -> V { mem(x, l, pb_eq_p) }
pub fn p_memv(x: &V, l: &V) -> V { mem(x, l, pb_eqv_p) }
pub fn p_member(x: &V, l: &V) -> V { mem(x, l, pb_equal_p) }
pub fn p_assoc(x: &V, l: &V) -> V { let mut c = l; loop { match c { V::Pair(p) => { if pb_equal_p(x, &pr(&p.0).0) { return p.0.clone(); } c = &p.1; } _ => return V::Bool(false) } } }
pub fn p_map(f: &V, l: &V) -> V { let mut out = Vec::new(); let mut x = l; while let V::Pair(p) = x { out.push(call(f, &[&p.0])); x = &p.1; } list_of(out) }
pub fn p_for_each(f: &V, l: &V) -> V { let mut x = l.clone(); loop { let n = match &x { V::Pair(p) => { call(f, &[&p.0]); p.1.clone() } _ => return V::Void }; x = n; } }

// ---- vectors --------------------------------------------------------------------------------
#[inline] fn vc(v: &V) -> &mut Vec<V> { match v { V::Vec(x) => x.v(), _ => bad("not a vector", v) } }
fn mkvec(v: Vec<V>) -> V { V::Vec(Rc::new(SVec(UnsafeCell::new(v)))) }
pub fn p_vector(a: &[&V]) -> V { mkvec(a.iter().map(|x| (*x).clone()).collect()) }
#[inline] pub fn p_vector_ref(v: &V, i: &V) -> V { let x = vc(v); let i = fx(i) as usize; if i < x.len() { x[i].clone() } else { fail("vector-ref: index out of range", &[v]) } }
#[inline] pub fn p_vector_length(v: &V) -> V { V::Fix(vc(v).len() as i64) }
pub fn p_vector_set_x(v: &V, i: &V, x: &V) -> V { let s = vc(v); let i = fx(i) as usize; if i >= s.len() { return fail("vector-set!: index out of range", &[v]); } let old = std::mem::replace(&mut s[i], x.clone()); drop(old); V::Void }
pub fn p_make_vector(a: &[&V]) -> V { mkvec(vec![if a.len() > 1 { a[1].clone() } else { V::Fix(0) }; fx(a[0]) as usize]) }
pub fn p_list_to_vector(l: &V) -> V { mkvec(list_vec(l)) }
pub fn p_vector_to_list(v: &V) -> V { let mut r = V::Null; for x in vc(v).iter().rev() { r = cons(x.clone(), r); } r }
pub fn p_vector_copy(v: &V) -> V { mkvec(vc(v).clone()) }
pub fn p_subvector(v: &V, s: &V, e: &V) -> V { mkvec(vc(v)[fx(s) as usize..fx(e) as usize].to_vec()) }
pub fn p_subvector_move_x(v1: &V, s1: &V, e1: &V, v2: &V, s2: &V) -> V {
    let tmp: Vec<V> = vc(v1)[fx(s1) as usize..fx(e1) as usize].to_vec(); let d = vc(v2); let s2 = fx(s2) as usize;
    for (k, x) in tmp.into_iter().enumerate() { d[s2 + k] = x; }
    V::Void
}

// ---- strings, symbols, characters -------------------------------------------------------------
#[inline] fn st(v: &V) -> &SStr { match v { V::Str(s) => s, _ => bad("not a string", v) } }
#[inline] fn ch(v: &V) -> char { match v { V::Char(c) => *c, _ => bad("not a character", v) } }
pub fn mkchars(c: Vec<char>) -> V { V::Str(Rc::new(SStr(UnsafeCell::new(c)))) }
pub fn mkstr(s: &str) -> V { mkchars(s.chars().collect()) }
pub fn rust_string(v: &V) -> String { st(v).c().iter().collect() }
#[inline] pub fn p_string_length(s: &V) -> V { V::Fix(st(s).c().len() as i64) }
#[inline] pub fn p_string_ref(s: &V, i: &V) -> V { let c = st(s).c(); let i = fx(i) as usize; if i < c.len() { V::Char(c[i]) } else { fail("string-ref: index out of range", &[s]) } }
pub fn p_substring(s: &V, a: &V, b: &V) -> V { let c = st(s).c(); let (a, b) = (fx(a) as usize, fx(b) as usize); if a > b || b > c.len() { return fail("substring: range", &[s]); } mkchars(c[a..b].to_vec()) }
pub fn p_string_append(a: &[&V]) -> V { let mut out = Vec::with_capacity(a.iter().map(|x| st(x).c().len()).sum()); for x in a { out.extend_from_slice(st(x).c()); } mkchars(out) }
pub fn p_string_set_x(s: &V, i: &V, c: &V) -> V { st(s).c()[fx(i) as usize] = ch(c); V::Void }
pub fn p_string_copy(s: &V) -> V { mkchars(st(s).c().clone()) }
pub fn p_string_to_list(s: &V) -> V { let mut r = V::Null; for c in st(s).c().iter().rev() { r = cons(V::Char(*c), r); } r }
pub fn p_list_to_string(l: &V) -> V { mkchars(list_vec(l).iter().map(ch).collect()) }
pub fn p_string(a: &[&V]) -> V { mkchars(a.iter().map(|x| ch(x)).collect()) }
pub fn p_make_string(a: &[&V]) -> V { mkchars(vec![if a.len() > 1 { ch(a[1]) } else { ' ' }; fx(a[0]) as usize]) }
pub fn p_string_to_symbol(s: &V) -> V { V::Sym(intern(&rust_string(s))) }
pub fn p_symbol_to_string(s: &V) -> V { match s { V::Sym(i) => mkstr(sym_name(*i)), _ => bad("not a symbol", s) } }
pub fn p_string_upcase(s: &V) -> V { mkchars(st(s).c().iter().flat_map(|c| c.to_uppercase()).collect()) }
pub fn p_string_downcase(s: &V) -> V { mkchars(st(s).c().iter().flat_map(|c| c.to_lowercase()).collect()) }
pub fn p_substring_move_x(s1: &V, a: &V, b: &V, s2: &V, d: &V) -> V {
    let tmp: Vec<char> = st(s1).c()[fx(a) as usize..fx(b) as usize].to_vec(); let dst = st(s2).c(); let d = fx(d) as usize;
    dst[d..d + tmp.len()].copy_from_slice(&tmp); V::Void
}
pub fn p_char_to_integer(c: &V) -> V { V::Fix(ch(c) as i64) }
pub fn p_integer_to_char(i: &V) -> V { V::Char(char::from_u32(fx(i) as u32).unwrap_or('\u{fffd}')) }
pub fn p_char_upcase(c: &V) -> V { V::Char(ch(c).to_uppercase().next().unwrap()) }

// ---- tables ---------------------------------------------------------------------------------
pub struct HKey(u8, V);
fn hash_eq<H: Hasher>(v: &V, h: &mut H) {
    match v {
        V::Fix(i) => i.hash(h), V::Sym(i) => { 1u8.hash(h); i.hash(h) } V::Char(c) => c.hash(h), V::Bool(b) => b.hash(h),
        V::Flo(f) => f.to_bits().hash(h), V::Ptr(p) => p.hash(h),
        V::Str(x) => (Rc::as_ptr(x) as usize).hash(h), V::Pair(x) => (Rc::as_ptr(x) as usize).hash(h),
        V::Vec(x) => (Rc::as_ptr(x) as usize).hash(h), V::Proc(x) => (Rc::as_ptr(x) as *const u8 as usize).hash(h),
        V::Table(x) => (Rc::as_ptr(x) as usize).hash(h), V::Big(x) => x.hash(h), V::Rat(x) => x.hash(h), _ => 0u8.hash(h),
    }
}
fn hash_equal<H: Hasher>(v: &V, h: &mut H, depth: u32) {
    match v {
        V::Str(s) => s.c().hash(h),
        V::Pair(_) => { let mut x = v; let mut n = 0; while let V::Pair(p) = x { if n < 16 && depth < 4 { hash_equal(&p.0, h, depth + 1); } n += 1; x = &p.1; } n.hash(h) }
        V::Vec(s) => { let s = s.v(); s.len().hash(h); if depth < 4 { for x in s.iter().take(16) { hash_equal(x, h, depth + 1); } } }
        _ => hash_eq(v, h),
    }
}
impl Hash for HKey { fn hash<H: Hasher>(&self, h: &mut H) { match self.0 { 2 | 3 => hash_equal(&self.1, h, 0), _ => hash_eq(&self.1, h) } } }
impl PartialEq for HKey { fn eq(&self, o: &HKey) -> bool { match self.0 { 0 => pb_eq_p(&self.1, &o.1), 1 => pb_eqv_p(&self.1, &o.1), _ => pb_equal_p(&self.1, &o.1) } } }
impl Eq for HKey {}
pub fn p_make_table(a: &[&V]) -> V {
    let mut kind = 3u8; let mut i = 0;
    while i + 1 < a.len() {
        if let V::Sym(s) = a[i] { if sym_name(*s) == "test:" {
            kind = match a[i + 1] { V::Proc(c) => match c.name { "eq?" => 0, "eqv?" => 1, "string=?" => 2, "equal?" => 3, n => panic!("make-table: unsupported test {:?}", n) }, _ => panic!("make-table: test") };
        } }
        i += 2;
    }
    V::Table(Rc::new(Table { kind, map: RefCell::new(HashMap::new()), seq: Cell::new(0) }))
}
#[inline] fn tb(v: &V) -> &Table { match v { V::Table(t) => t, _ => bad("not a table", v) } }
pub fn p_table_ref(t: &V, k: &V, d: &V) -> V { let t = tb(t); match t.map.borrow().get(&HKey(t.kind, k.clone())) { Some(e) => e.1.clone(), None => d.clone() } }
pub fn p_table_set_x(a: &[&V]) -> V {
    let t = tb(a[0]); let key = HKey(t.kind, a[1].clone());
    let old = if a.len() > 2 { let n = t.seq.get(); t.seq.set(n + 1); t.map.borrow_mut().insert(key, (n, a[2].clone())) } else { t.map.borrow_mut().remove(&key) };
    drop(old); V::Void
}
pub fn p_table_for_each(f: &V, t: &V) -> V {
    let t = tb(t); let mut rows: Vec<(u64, V, V)> = t.map.borrow().iter().map(|(k, e)| (e.0, k.1.clone(), e.1.clone())).collect();
    rows.sort_by_key(|r| r.0);
    for r in rows { call(f, &[&r.1, &r.2]); }
    V::Void
}

// ---- output ---------------------------------------------------------------------------------
pub fn show(v: &V, out: &mut String, write: bool) {
    match v {
        V::Fix(i) => out.push_str(&i.to_string()), V::Big(b) => out.push_str(&b.to_string()),
        V::Rat(r) => out.push_str(&format!("{}/{}", r.0, r.1)), V::Flo(f) => fmt_flo(*f, out),
        V::Bool(b) => out.push_str(if *b { "#t" } else { "#f" }), V::Null => out.push_str("()"),
        V::Void => out.push_str("#<void>"), V::Eof => out.push_str("#!eof"), V::Unbound => out.push_str("#<unbound>"),
        V::Sym(i) => out.push_str(sym_name(*i)),
        V::Char(c) => if write { out.push_str("#\\"); out.push(*c) } else { out.push(*c) },
        V::Str(s) => if write {
            out.push('"');
            for c in s.c().iter() { match c { '"' => out.push_str("\\\""), '\\' => out.push_str("\\\\"), '\n' => out.push_str("\\n"), '\t' => out.push_str("\\t"), '\r' => out.push_str("\\r"), c => out.push(*c) } }
            out.push('"')
        } else { out.extend(s.c().iter()) },
        V::Pair(_) => {
            out.push('('); let mut x = v; let mut first = true;
            loop { match x { V::Pair(p) => { if !first { out.push(' '); } first = false; show(&p.0, out, write); x = &p.1; } V::Null => break, o => { out.push_str(" . "); show(o, out, write); break } } }
            out.push(')')
        }
        V::Vec(s) => { out.push_str("#("); for (i, x) in s.v().iter().enumerate() { if i > 0 { out.push(' '); } show(x, out, write); } out.push(')') }
        V::Proc(_) => out.push_str("#<procedure>"), V::Table(_) => out.push_str("#<table>"), V::Port(_) => out.push_str("#<port>"),
        V::Ptr(p) => out.push_str(&format!("#<pointer {:x}>", p)), V::Err(_) => { out.push_str("#<error "); show_exception(v, out); out.push('>') }
    }
}
pub fn show_exception(e: &V, out: &mut String) {
    match e {
        V::Err(r) => { show(&r.0, out, false); for x in list_vec(&r.1) { out.push(' '); show(&x, out, true); } out.push('\n') }
        _ => { show(e, out, true); out.push('\n') }
    }
}
fn emit(port: Option<&V>, f: &dyn Fn(&mut String)) {
    let cur; let p = match port { Some(p) => p, None => { cur = p_current_output_port(); &cur.clone() } };
    match p {
        V::Port(p) => match &**p {
            Port::Out(s) => f(&mut s.borrow_mut()),
            Port::Stdout => unsafe { let s = &mut *(&raw mut STDOUT); f(s); if s.len() > 1 << 16 { flush_stdout(); } },
            Port::Stderr => { let mut s = String::new(); f(&mut s); eprint!("{}", s) }
            Port::In(_) => panic!("output to an input port"),
        },
        _ => bad("not a port", p),
    }
}
pub fn p_display(a: &[&V]) -> V { emit(a.get(1).copied(), &|s| show(a[0], s, false)); V::Void }
pub fn p_write(a: &[&V]) -> V { emit(a.get(1).copied(), &|s| show(a[0], s, true)); V::Void }
pub fn p_newline(a: &[&V]) -> V { emit(a.get(0).copied(), &|s| s.push('\n')); V::Void }
pub fn p_write_char(a: &[&V]) -> V { emit(a.get(1).copied(), &|s| s.push(ch(a[0]))); V::Void }
pub fn p_write_substring(x: &V, a: &V, b: &V, port: &V) -> V { emit(Some(port), &|s| s.extend(st(x).c()[fx(a) as usize..fx(b) as usize].iter())); V::Void }
pub fn p_display_exception(e: &V, port: &V) -> V { emit(Some(port), &|s| show_exception(e, s)); V::Void }
pub fn p_open_output_string() -> V { V::Port(Rc::new(Port::Out(RefCell::new(String::new())))) }
pub fn p_get_output_string(p: &V) -> V { match p { V::Port(p) => match &**p { Port::Out(s) => mkstr(&s.borrow()), _ => panic!("get-output-string") }, _ => bad("not a port", p) } }
pub fn p_current_output_port() -> V { unsafe { let o = &*(&raw const OUTS); match o.last() { Some(p) => p.clone(), None => V::Port(Rc::new(Port::Stdout)) } } }
pub fn p_current_error_port() -> V { V::Port(Rc::new(Port::Stderr)) }
pub fn p_force_output(_p: &V) -> V { flush_stdout(); V::Void }
pub fn p_with_output_to_string(prefix: &V, thunk: &V) -> V {
    let port = p_open_output_string();
    p_display(&[prefix, &port]);
    unsafe { (*(&raw mut OUTS)).push(port.clone()); }
    let r = catch_unwind(AssertUnwindSafe(|| call(thunk, &[])));
    unsafe { (*(&raw mut OUTS)).pop(); }
    match r { Ok(_) => p_get_output_string(&port), Err(p) => resume_unwind(p) }
}
pub fn p_call_with_output_file(path: &V, f: &V) -> V {
    let port = p_open_output_string(); let r = call(f, &[&port]);
    if let V::Port(p) = &port { if let Port::Out(s) = &**p { std::fs::write(rust_string(path), s.borrow().as_bytes()).unwrap_or_else(|e| { fail(&format!("cannot write file: {}", e), &[path]); }); } }
    r
}
fn in_port(text: &str) -> V { V::Port(Rc::new(Port::In(RefCell::new((text.chars().collect(), 0))))) }
pub fn p_call_with_input_file(path: &V, f: &V) -> V {
    match std::fs::read_to_string(rust_string(path)) { Ok(t) => call(f, &[&in_port(&t)]), Err(e) => fail(&format!("cannot read file: {}", e), &[path]) }
}
pub fn p_open_input_string(s: &V) -> V { V::Port(Rc::new(Port::In(RefCell::new((st(s).c().clone(), 0))))) }
fn inp(p: &V) -> &RefCell<(Vec<char>, usize)> { match p { V::Port(p) => match &**p { Port::In(c) => c, _ => panic!("not an input port") }, _ => bad("not a port", p) } }
pub fn p_read_char(p: &V) -> V { let mut s = inp(p).borrow_mut(); if s.1 < s.0.len() { s.1 += 1; V::Char(s.0[s.1 - 1]) } else { V::Eof } }
pub fn p_read(p: &V) -> V { let mut s = inp(p).borrow_mut(); let (chars, pos) = &mut *s; let mut i = *pos; let v = read_datum(chars, &mut i); *pos = i; v }

// ---- reader ---------------------------------------------------------------------------------
fn delim(c: char) -> bool { c.is_whitespace() || matches!(c, '(' | ')' | '[' | ']' | '"' | ';' | '\'') }
fn skip(t: &[char], i: &mut usize) {
    while *i < t.len() {
        if t[*i].is_whitespace() { *i += 1 } else if t[*i] == ';' { while *i < t.len() && t[*i] != '\n' { *i += 1 } } else { break }
    }
}
pub fn read_datum(t: &[char], i: &mut usize) -> V {
    skip(t, i);
    if *i >= t.len() { return V::Eof; }
    let c = t[*i];
    match c {
        '(' | '[' => {
            *i += 1; let mut items = Vec::new(); let mut tail = V::Null;
            loop {
                skip(t, i);
                if *i >= t.len() { panic!("read: unterminated list"); }
                if t[*i] == ')' || t[*i] == ']' { *i += 1; break; }
                if t[*i] == '.' && *i + 1 < t.len() && delim(t[*i + 1]) { *i += 1; tail = read_datum(t, i); continue; }
                items.push(read_datum(t, i));
            }
            let mut r = tail; for x in items.into_iter().rev() { r = cons(x, r); } r
        }
        '\'' => { *i += 1; let x = read_datum(t, i); cons(V::Sym(intern("quote")), cons(x, V::Null)) }
        '"' => {
            *i += 1; let mut out = Vec::new();
            while t[*i] != '"' {
                if t[*i] == '\\' {
                    let e = t[*i + 1];
                    if e == 'x' { let mut j = *i + 2; let mut n = 0u32; while t[j] != ';' { n = n * 16 + t[j].to_digit(16).unwrap(); j += 1; } out.push(char::from_u32(n).unwrap()); *i = j + 1; continue; }
                    out.push(match e { 'n' => '\n', 't' => '\t', 'r' => '\r', 'a' => '\u{7}', '0' => '\0', 'b' => '\u{8}', o => o }); *i += 2;
                } else { out.push(t[*i]); *i += 1; }
            }
            *i += 1; mkchars(out)
        }
        '#' if *i + 1 < t.len() && t[*i + 1] == '(' => { *i += 1; let l = read_datum(t, i); p_list_to_vector(&l) }
        '#' if *i + 1 < t.len() && t[*i + 1] == '\\' => {
            let mut j = *i + 3; while j < t.len() && !delim(t[j]) { j += 1 }
            let tok: String = t[*i + 2..j].iter().collect();
            if tok.chars().count() == 1 { *i = j; return V::Char(tok.chars().next().unwrap()); }
            let named = match tok.as_str() { "space" => Some(' '), "newline" | "linefeed" => Some('\n'), "tab" => Some('\t'), "nul" | "null" => Some('\0'), "return" => Some('\r'), "delete" | "rubout" => Some('\u{7f}'), "escape" | "esc" => Some('\u{1b}'), "backspace" => Some('\u{8}'), "alarm" => Some('\u{7}'), _ => None };
            if let Some(c) = named { *i = j; return V::Char(c); }
            if tok.starts_with('x') || tok.starts_with('U') { if let Ok(n) = u32::from_str_radix(&tok[1..], 16) { *i = j; return V::Char(char::from_u32(n).unwrap()); } }
            *i += 3; V::Char(t[*i - 1])
        }
        _ => {
            let mut j = *i; let mut name = String::new(); let mut bars = false;
            while j < t.len() && !delim(t[j]) {
                if t[j] == '|' { bars = true; j += 1; while t[j] != '|' { name.push(t[j]); j += 1 } j += 1 } else { name.push(t[j]); j += 1 }
            }
            *i = j;
            if bars { return V::Sym(intern(&name)); }
            match name.as_str() { "#t" | "#true" => V::Bool(true), "#f" | "#false" => V::Bool(false), "#!void" => V::Void, "#!eof" => V::Eof,
                _ => parse_number(&name).unwrap_or_else(|| V::Sym(intern(&name))) }
        }
    }
}

// ---- eval: a closure-compiling interpreter for the Scheme the compiler emits at run time ------------
pub struct Frame { vals: UnsafeCell<Vec<V>>, up: Option<Rc<Frame>> }
impl Frame { #[inline] fn v(&self) -> &mut Vec<V> { unsafe { &mut *self.vals.get() } } }
type Code = Rc<dyn Fn(&Option<Rc<Frame>>) -> V>;
struct Scope { names: Vec<u32>, up: Option<Rc<Scope>> }
fn lookup(sc: &Option<Rc<Scope>>, s: u32) -> Option<(usize, usize)> {
    let mut d = 0; let mut c = sc;
    while let Some(x) = c { if let Some(i) = x.names.iter().rposition(|n| *n == s) { return Some((d, i)); } d += 1; c = &x.up; }
    None
}
#[inline] fn frame_at(env: &Option<Rc<Frame>>, d: usize) -> &Frame { let mut f = env.as_ref().unwrap(); for _ in 0..d { f = f.up.as_ref().unwrap(); } f }
fn head_is(x: &V, name: &str) -> bool { matches!(x, V::Sym(s) if sym_name(*s) == name) }
fn symid(x: &V) -> u32 { match x { V::Sym(s) => *s, _ => bad("eval: expected a symbol", x) } }
fn comp_body(xs: &[V], sc: &Option<Rc<Scope>>) -> Code {
    if xs.len() == 1 { return comp(&xs[0], sc); }
    let cs: Vec<Code> = xs.iter().map(|x| comp(x, sc)).collect();
    Rc::new(move |e| { let n = cs.len(); for c in &cs[..n - 1] { c(e); } cs[n - 1](e) })
}
fn comp_lambda(formals: &V, body: &[V], sc: &Option<Rc<Scope>>) -> (usize, bool, Code) {
    let mut names = Vec::new(); let mut rest = false; let mut x = formals;
    loop { match x { V::Pair(p) => { names.push(symid(&p.0)); x = &p.1; } V::Null => break, V::Sym(s) => { names.push(*s); rest = true; break } _ => bad("eval: formals", formals) } }
    let n = if rest { names.len() - 1 } else { names.len() };
    let inner = Some(Rc::new(Scope { names, up: sc.clone() }));
    (n, rest, comp_body(body, &inner))
}
fn enter(n: usize, rest: bool, a: &[&V], env: &Option<Rc<Frame>>) -> Option<Rc<Frame>> {
    let mut vals: Vec<V> = Vec::with_capacity(n + 1);
    for x in &a[..n] { vals.push((*x).clone()); }
    if rest { vals.push(list_from(&a[n..])); }
    Some(Rc::new(Frame { vals: UnsafeCell::new(vals), up: env.clone() }))
}
fn sym_list(names: &[&str]) -> V { V::Sym(intern(names[0])) }
fn comp(x: &V, sc: &Option<Rc<Scope>>) -> Code {
    match x {
        V::Sym(s) => {
            let s = *s;
            if let Some((d, i)) = lookup(sc, s) { return Rc::new(move |e| frame_at(e, d).v()[i].clone()); }
            let name = sym_name(s);
            if name.ends_with(':') { return Rc::new(move |_| V::Sym(s)); }
            let slot = global_slot(name);
            Rc::new(move |_| match g(slot) { V::Unbound => fail("unbound variable", &[&V::Sym(s)]), v => v.clone() })
        }
        V::Pair(p) => {
            let items = list_vec(x); let h = &items[0];
            if let V::Sym(hs) = h { if lookup(sc, *hs).is_none() {
                match sym_name(*hs) {
                    "quote" => { let v = items[1].clone(); return Rc::new(move |_| v.clone()); }
                    "if" => {
                        let c = comp(&items[1], sc); let a = comp(&items[2], sc);
                        let b: Code = if items.len() > 3 { comp(&items[3], sc) } else { Rc::new(|_| V::Void) };
                        return Rc::new(move |e| if truthy(&c(e)) { a(e) } else { b(e) });
                    }
                    "define" => {
                        let (name, val): (u32, Code) = match &items[1] {
                            V::Pair(t) => { let (n, rest, body) = comp_lambda(&t.1, &items[2..], sc); (symid(&t.0), Rc::new(move |e| { let (body, env) = (body.clone(), e.clone()); mk(move |a: &[&V]| -> V { if a.len() < n || (!rest && a.len() != n) { return arity_error(a.len()); } { let _i = Interp::enter(); body(&enter(n, rest, a, &env)) } }) })) }
                            t => (symid(t), comp(&items[2], sc)),
                        };
                        if sc.is_some() { panic!("eval: internal define is not supported"); }
                        let slot = global_slot(sym_name(name));
                        return Rc::new(move |e| { gset_dynamic(slot, val(e)); V::Void });
                    }
                    "set!" => {
                        let val = comp(&items[2], sc); let s = symid(&items[1]);
                        if let Some((d, i)) = lookup(sc, s) { return Rc::new(move |e| { let v = val(e); { let old = std::mem::replace(&mut frame_at(e, d).v()[i], v); drop(old); } V::Void }); }
                        let slot = global_slot(sym_name(s));
                        return Rc::new(move |e| { gset_dynamic(slot, val(e)); V::Void });
                    }
                    "lambda" => {
                        let (n, rest, body) = comp_lambda(&items[1], &items[2..], sc);
                        return Rc::new(move |e| { let (body, env) = (body.clone(), e.clone()); mk(move |a: &[&V]| -> V { if a.len() < n || (!rest && a.len() != n) { return arity_error(a.len()); } { let _i = Interp::enter(); body(&enter(n, rest, a, &env)) } }) });
                    }
                    "case-lambda" => {
                        let cls: Vec<(usize, bool, Code)> = items[1..].iter().map(|cl| { let c = list_vec(cl); comp_lambda(&c[0], &c[1..], sc) }).collect();
                        let cls = Rc::new(cls);
                        return Rc::new(move |e| { let (cls, env) = (cls.clone(), e.clone()); mk(move |a: &[&V]| -> V {
                            for (n, rest, body) in cls.iter() { if a.len() == *n || (*rest && a.len() >= *n) { { let _i = Interp::enter(); return body(&enter(*n, *rest, a, &env)); } } }
                            arity_error(a.len()) }) });
                    }
                    "begin" => { if items.len() == 1 { return Rc::new(|_| V::Void); } return comp_body(&items[1..], sc); }
                    "let" if matches!(items[1], V::Sym(_)) => {
                        // (let name ((v init) ...) body) = ((letrec ((name (lambda (v ...) body))) name) init ...)
                        let name = symid(&items[1]); let binds: Vec<Vec<V>> = list_vec(&items[2]).iter().map(list_vec).collect();
                        let inits: Vec<Code> = binds.iter().map(|b| comp(&b[1], sc)).collect();
                        let rs = Some(Rc::new(Scope { names: vec![name], up: sc.clone() }));
                        let formals = list_of(binds.iter().map(|b| b[0].clone()).collect());
                        let (n, rest, body) = comp_lambda(&formals, &items[3..], &rs);
                        return Rc::new(move |e| {
                            let fr = Some(Rc::new(Frame { vals: UnsafeCell::new(vec![V::Void]), up: e.clone() }));
                            let (body2, env2) = (body.clone(), Rc::downgrade(fr.as_ref().unwrap()));
                            let f = mk(move |a: &[&V]| -> V { if a.len() != n { return arity_error(a.len()); } { let _i = Interp::enter(); body2(&enter(n, rest, a, &env2.upgrade())) } });
                            fr.as_ref().unwrap().v()[0] = f.clone();
                            let vals: Vec<V> = inits.iter().map(|c| c(e)).collect(); let refs: Vec<&V> = vals.iter().collect();
                            call(&f, &refs)
                        });
                    }
                    "let" | "letrec" | "letrec*" => {
                        let rec = sym_name(*hs) != "let";
                        let binds: Vec<Vec<V>> = list_vec(&items[1]).iter().map(list_vec).collect();
                        let inner = Some(Rc::new(Scope { names: binds.iter().map(|b| symid(&b[0])).collect(), up: sc.clone() }));
                        let inits: Vec<Code> = binds.iter().map(|b| comp(&b[1], if rec { &inner } else { sc })).collect();
                        let body = comp_body(&items[2..], &inner);
                        if rec { return Rc::new(move |e| {
                            let fr = Some(Rc::new(Frame { vals: UnsafeCell::new(vec![V::Void; inits.len()]), up: e.clone() }));
                            for (i, c) in inits.iter().enumerate() { let v = c(&fr); fr.as_ref().unwrap().v()[i] = v; }
                            body(&fr) }); }
                        return Rc::new(move |e| { let vals: Vec<V> = inits.iter().map(|c| c(e)).collect(); body(&Some(Rc::new(Frame { vals: UnsafeCell::new(vals), up: e.clone() }))) });
                    }
                    "let*" => {
                        let binds = list_vec(&items[1]);
                        if binds.len() <= 1 { let mut f = vec![V::Sym(intern("let")), items[1].clone()]; f.extend_from_slice(&items[2..]); return comp(&list_of(f), sc); }
                        let mut inner = vec![V::Sym(intern("let*")), list_of(binds[1..].to_vec())]; inner.extend_from_slice(&items[2..]);
                        let outer = vec![V::Sym(intern("let")), list_of(vec![binds[0].clone()]), list_of(inner)];
                        return comp(&list_of(outer), sc);
                    }
                    "and" | "or" => {
                        let is_and = sym_name(*hs) == "and"; let cs: Vec<Code> = items[1..].iter().map(|x| comp(x, sc)).collect();
                        return Rc::new(move |e| { let mut r = V::Bool(is_and); for c in &cs { r = c(e); if truthy(&r) != is_and { return r; } } r });
                    }
                    "cond" => {
                        let mut cls: Vec<(Option<Code>, Option<Code>)> = Vec::new();
                        for cl in &items[1..] { let c = list_vec(cl);
                            if head_is(&c[0], "else") { cls.push((None, Some(comp_body(&c[1..], sc)))); } else { cls.push((Some(comp(&c[0], sc)), if c.len() > 1 { Some(comp_body(&c[1..], sc)) } else { None })); } }
                        return Rc::new(move |e| { for (t, b) in &cls { match t { None => return b.as_ref().unwrap()(e), Some(t) => { let v = t(e); if truthy(&v) { return match b { Some(b) => b(e), None => v }; } } } } V::Void });
                    }
                    "case" => {
                        let key = comp(&items[1], sc); let mut cls: Vec<(Option<Vec<V>>, Code)> = Vec::new();
                        for cl in &items[2..] { let c = list_vec(cl); cls.push((if head_is(&c[0], "else") { None } else { Some(list_vec(&c[0])) }, comp_body(&c[1..], sc))); }
                        return Rc::new(move |e| { let k = key(e); for (ds, b) in &cls { if ds.as_ref().map_or(true, |ds| ds.iter().any(|d| pb_eqv_p(d, &k))) { return b(e); } } V::Void });
                    }
                    _ => {}
                }
            } }
            let f = comp(h, sc); let args: Vec<Code> = items[1..].iter().map(|x| comp(x, sc)).collect();
            match args.len() {
                0 => Rc::new(move |e| call(&f(e), &[])),
                1 => { let a0 = args[0].clone(); Rc::new(move |e| { let fv = f(e); let x = a0(e); call(&fv, &[&x]) }) }
                2 => { let (a0, a1) = (args[0].clone(), args[1].clone()); Rc::new(move |e| { let fv = f(e); let x = a0(e); let y = a1(e); call(&fv, &[&x, &y]) }) }
                3 => { let (a0, a1, a2) = (args[0].clone(), args[1].clone(), args[2].clone()); Rc::new(move |e| { let fv = f(e); let x = a0(e); let y = a1(e); let z = a2(e); call(&fv, &[&x, &y, &z]) }) }
                _ => Rc::new(move |e| { let fv = f(e); let vals: Vec<V> = args.iter().map(|c| c(e)).collect(); let refs: Vec<&V> = vals.iter().collect(); call(&fv, &refs) }),
            }
        }
        V::Null => panic!("eval: empty application"),
        other => { let v = other.clone(); Rc::new(move |_| v.clone()) }
    }
}
pub fn p_eval(form: &V, _env: &V) -> V { let t = now_ns(); let r = comp(form, &None)(&None); stat(1, 1); stat(2, now_ns() - t); r }
pub fn p_interaction_environment() -> V { V::Void }

// ---- system -----------------------------------------------------------------------------------
pub fn p_command_line() -> V { unsafe { list_of((*(&raw const ARGS)).iter().map(|s| mkstr(s)).collect()) } }
pub fn p_getenv(name: &V, default: &V) -> V { match std::env::var(rust_string(name)) { Ok(v) => mkstr(&v), Err(_) => default.clone() } }
pub fn p_current_time() -> V { V::Flo(std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64()) }
pub fn p_time_to_seconds(t: &V) -> V { t.clone() }
pub fn p_hhgc() -> V { V::Void }
pub fn p_hhmake_global_var(s: &V) -> V { s.clone() }
pub fn p_hhglobal_var_ref(s: &V) -> V { match s { V::Sym(i) => g(global_slot(sym_name(*i))).clone(), _ => bad("global-var-ref", s) } }
pub fn p_hhglobal_var_set_x(s: &V, v: &V) -> V { match s { V::Sym(i) => { gset_dynamic(global_slot(sym_name(*i)), v.clone()); V::Void } _ => bad("global-var-set!", s) } }

// ---- foreign calls ----------------------------------------------------------------------------
pub fn c_string(v: &V) -> CString { CString::new(rust_string(v).replace('\0', "")).unwrap() }
pub fn c_int(v: &V) -> i64 { int(v) as i64 }
pub fn c_f64(v: &V) -> f64 { f64of(v) }
pub fn c_ptr(v: &V) -> *mut c_void { match v { V::Ptr(p) => *p as *mut c_void, _ => std::ptr::null_mut() } }
pub fn from_ptr(p: *mut c_void) -> V { if p.is_null() { V::Bool(false) } else { V::Ptr(p as usize) } }
