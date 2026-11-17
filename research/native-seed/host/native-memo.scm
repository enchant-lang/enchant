;; The native counterpart of the lazy_memo NIF (native/lazy_memo, Rust).
;; Category (c) of speed/CONTRACT2.md: the memo CELL and nothing else. The
;; force protocol, the budget policy, cursors-as-sequences and delays are the
;; compiled BL of priv/host/{lazy_memo,lazy_seq,seq_cursor,delay,deferred}.bl.
;;
;; One Scheme procedure per NIF function that lazy_memo.bl calls, under the
;; NIF's own name. `erlang:load_nif/2` binds a library to the stubs of the
;; calling module; here the same binding happens when the compiled stub is
;; registered: `native-register!` of "host.lazy-memo/nif_*" publishes the
;; native procedure instead of the stub, so every linked caller, arity cell and
;; global view sees it (host-compiler.scm `native-link!`).
;;
;; A cell is a native reference (`erlang/is_reference` answers true, `=:=` is
;; identity) whose record lives in a weak table: #(id version state bytes).
;; There is one scheduler, so every lane is the fast lane and no lock exists.
;; The edge arguments (`deps`, `deps_mode`) are accepted and ignored: the BL
;; host passes none (big-O item M), so the graph the NIF would keep is empty
;; and `:cycle` is never an answer. Reclamation is Gambit's tracing GC, so the
;; cycle collector has nothing to do and reports itself on.
(define native-memo-ns "host.lazy-memo")
(define native-memo-cells (make-table test: eq? weak-keys: #t))
(define native-memo-next-id 0)
(define native-memo-live 0)
(define native-memo-retained 0)
(define native-memo-fast-lane 65536)
(define (native-memo-cell r)
 (or (table-ref native-memo-cells r #f) (native-badarg "not a lazy memo resource")))
(define (native-memo-new state deps bytes)
 (let ((r (native-make-reference)))
  (set! native-memo-next-id (+ native-memo-next-id 1))
  (set! native-memo-live (+ native-memo-live 1))
  (set! native-memo-retained (+ native-memo-retained bytes))
  (table-set! native-memo-cells r (vector native-memo-next-id 0 state bytes))
  r))
(define (native-memo-commit! cell state bytes)
 (set! native-memo-retained (+ native-memo-retained (- bytes (vector-ref cell 3))))
 (vector-set! cell 1 (+ 1 (vector-ref cell 1)))
 (vector-set! cell 2 state)
 (vector-set! cell 3 bytes))
(define (native-memo-notify! notifications)
 (for-each (lambda (n) (native-memo-actor-call "native-send!" (bl-nth n 0) (bl-nth n 1))) notifications))
(define (native-memo-read r) (vector-ref (native-memo-cell r) 2))
(define (native-memo-read-versioned r)
 (let ((cell (native-memo-cell r))) (bl-make-tuple (vector-ref cell 1) (vector-ref cell 2))))
(define (native-memo-exchange-version r expected replacement deps-mode bytes notifications)
 (let ((cell (native-memo-cell r)))
  (if (eqv? expected (vector-ref cell 1))
   (begin (native-memo-commit! cell replacement bytes) (native-memo-notify! notifications) (bl-key "ok"))
   (bl-key "retry"))))
(define (native-memo-exchange-admitted r expected replacement deps-mode bytes notifications budget)
 (let ((cell (native-memo-cell r)))
  (cond ((not (eqv? expected (vector-ref cell 1))) (bl-key "retry"))
   ((let ((growth (- bytes (vector-ref cell 3))))
     (and (> growth 0) (> (+ native-memo-retained growth) budget)))
    (bl-key "over_budget"))
   (else (native-memo-commit! cell replacement bytes) (native-memo-notify! notifications) (bl-key "ok")))))
(define (native-memo-compare-exchange r expected replacement deps bytes notifications)
 (let ((cell (native-memo-cell r)))
  (if (bl-key-equal? expected (vector-ref cell 2))
   (begin (native-memo-commit! cell replacement bytes) (native-memo-notify! notifications) (bl-key "ok"))
   (bl-key "retry"))))
(define (native-memo-put r value bytes)
 (native-memo-commit! (native-memo-cell r) value bytes) (bl-key "ok"))
(define (native-memo-tag state)
 (cond ((bl-tag? state 'tuple)
        (let ((items (vector-ref state 1)))
         (if (and (> (vector-length items) 0) (symbol? (vector-ref items 0))) (vector-ref items 0) (bl-key "other"))))
  ((symbol? state) state) ((boolean? state) state) ((bl-is-nil state) state)
  (else (bl-key "other"))))
(define (native-memo-peek r)
 (let ((cell (native-memo-cell r))) (bl-make-tuple (native-memo-tag (vector-ref cell 2)) (vector-ref cell 1))))
(define (native-memo-id r) (vector-ref (native-memo-cell r) 0))
(define (native-memo-resource-id term)
 (let ((cell (and (native-reference? term) (table-ref native-memo-cells term #f))))
  (if cell (vector-ref cell 0) bl-nil)))
(define (native-memo-stats)
 (bl-map (bl-key "live_cells") native-memo-live (bl-key "retained_bytes") native-memo-retained
  (bl-key "reserved_bytes") 0 (bl-key "cycle_enabled") #t (bl-key "cycle_runs") 0
  (bl-key "cycle_collected") 0))
;; Cursors: one root per walk, `{root, index}` tokens, 32 heads per chunk.
(define native-memo-cursors (make-table test: eq? weak-keys: #t))
(define (native-memo-cursor items deps bytes)
 (let ((r (native-make-reference)))
  (table-set! native-memo-cursors r
   (list->vector (let loop ((xs items) (out '()))
    (if (null? xs) (reverse (cons '() out))
     (loop (let skip ((xs xs) (k 32)) (if (or (= k 0) (null? xs)) xs (skip (cdr xs) (- k 1)))) (cons xs out))))))
  r))
(define (native-memo-token handle)
 (cond ((table-ref native-memo-cursors handle #f) => (lambda (p) (cons p 0)))
  ((and (bl-tag? handle 'tuple) (= 2 (vector-length (vector-ref handle 1)))
        (table-ref native-memo-cursors (bl-nth handle 0) #f))
   => (lambda (p) (cons p (bl-nth handle 1))))
  (else (native-badarg "not a cursor handle"))))
(define (native-memo-cursor-chunk handle)
 (let* ((t (native-memo-token handle)) (positions (car t)) (index (cdr t))
        (root (if (bl-tag? handle 'tuple) (bl-nth handle 0) handle)))
  (if (>= index (vector-length positions)) (native-badarg "cursor index"))
  (bl-make-tuple
   (let take ((xs (vector-ref positions index)) (k 32))
    (if (or (= k 0) (null? xs)) '() (cons (car xs) (take (cdr xs) (- k 1)))))
   (if (< (+ index 2) (vector-length positions)) (bl-make-tuple root (+ index 1)) bl-nil))))
;; `distinct`'s membership set.
(define (native-memo-seen-admit seen keys)
 (map (lambda (key) (let ((old (native-map-has? (vector-ref seen 1) key)))
  (if (not old) (vector-set! seen 1 (bl-assoc (vector-ref seen 1) key #t))) (not old))) keys))
(define (native-memo-unsupported name)
 (lambda arguments (native-raise (bl-key "error") (bl-tuple (list (bl-key "native_unsupported") name)) (native-capture-stack))))
(define native-memo-nifs
 (list
  (cons "nif_loaded?" (lambda () #t))
  (cons "nif_runtime_identity" (lambda () "native-lazy-memo-v1"))
  (cons "nif_file_lock" (native-memo-unsupported "nif_file_lock"))
  (cons "nif_file_claim" (native-memo-unsupported "nif_file_claim"))
  (cons "nif_file_claim_owned" (native-memo-unsupported "nif_file_claim_owned"))
  (cons "nif_file_unlock" (native-memo-unsupported "nif_file_unlock"))
  (cons "nif_new" native-memo-new) (cons "nif_new_fast" native-memo-new)
  (cons "nif_read" native-memo-read) (cons "nif_read_fast" native-memo-read)
  (cons "nif_read_versioned" native-memo-read-versioned) (cons "nif_read_versioned_fast" native-memo-read-versioned)
  (cons "nif_fast_lane_bytes" (lambda () native-memo-fast-lane))
  (cons "nif_set_fast_lane_bytes" (lambda (bytes) (set! native-memo-fast-lane bytes) (bl-key "ok")))
  (cons "nif_compare_exchange" native-memo-compare-exchange)
  (cons "nif_compare_exchange_fast" native-memo-compare-exchange)
  (cons "nif_exchange_version" native-memo-exchange-version)
  (cons "nif_exchange_version_fast" native-memo-exchange-version)
  (cons "nif_exchange_version_admitted" native-memo-exchange-admitted)
  (cons "nif_exchange_version_admitted_fast" native-memo-exchange-admitted)
  (cons "nif_put" native-memo-put) (cons "nif_put_fast" native-memo-put)
  (cons "nif_id" native-memo-id) (cons "nif_resource_id" native-memo-resource-id)
  (cons "nif_dependency_resource" (lambda (term) (if (table-ref native-memo-cells term #f) term bl-nil)))
  (cons "nif_stats" native-memo-stats) (cons "nif_peek" native-memo-peek)
  (cons "nif_retained_bytes" (lambda () native-memo-retained))
  (cons "nif_reserved_bytes" (lambda () 0))
  (cons "nif_cursor" native-memo-cursor)
  (cons "nif_cursor_chunk" native-memo-cursor-chunk) (cons "nif_cursor_chunk_fast" native-memo-cursor-chunk)
  (cons "nif_cursor_dirty_chunks" (lambda (handle) (native-memo-token handle) #f))
  (cons "nif_seen_new" (lambda () (vector 'seen (bl-empty-map))))
  (cons "nif_seen_admit" native-memo-seen-admit)
  (cons "nif_collect_cycles" (lambda () 0))
  (cons "nif_collector_status" (lambda () ""))))
;; A sealed image emits each definition's own binding and arity cells
;; (`v_<ns/name>`, `v_<ns/name>$N`) before registering it, and its local calls
;; read those cells directly. As erlang:load_nif replaces the module's own
;; functions on BEAM, the counterpart rebinds them too (dev images read the
;; registry through native-link!).
(define (native-memo-binding-name ns name)
 (string-append "v" (apply string-append
  (map (lambda (c) (string-append "_" (number->string (char->integer c))))
       (string->list (string-append ns "/" name))))))
(define (native-memo-rebind! symbol value)
 (let ((cell (##make-global-var symbol)))
  (if (not (##unbound? (##global-var-ref cell))) (##global-var-set! cell value))))
(define (native-memo-install-cells! ns name nif)
 (let ((binding (native-memo-binding-name ns name)))
  (native-memo-rebind! (string->symbol binding) nif)
  (let loop ((arity 0))
   (if (<= arity 8)
    (begin (native-memo-rebind! (string->symbol (string-append binding "$" (number->string arity))) nif)
           (loop (+ arity 1)))))))
(define native-register-without-memo-nifs native-register!)
(set! native-register! (lambda (ns name value)
 (native-register-without-memo-nifs ns name
  (if (string=? ns native-memo-ns)
   (let ((nif (assoc name native-memo-nifs)))
    (if nif (begin (native-memo-install-cells! ns name (cdr nif)) (cdr nif)) value))
   value))))

;; ── Erlang/OTP and Elixir BIFs the compiled lazy modules call ──────────────
;; Categories (b) and (d) of CONTRACT2.md: no BL source exists for these.
;;
;; Processes are the actor runtime's (priv/lib/js/actor/runtime.bl, compiled
;; into the `native.kernel` namespace of an actor program): `self` is the
;; host's frame identity, which that runtime sets to the running pid. A force
;; that finds a cell running under another actor WAITS, as on BEAM: the
;; compiled `wait_for_attempt` monitors the owner, records whom it waits on in
;; its own process dictionary, follows the wait-for chain through
;; `process_info` (a cycle raises `:recursive_force`), registers as a waiter
;; and blocks in `receive`; the owner's publication sends it the outcome, and
;; the owner's death sends it a DOWN. Every primitive below is the actor
;; runtime's own operation (category d), looked up when called, so the force
;; protocol itself stays the compiled BL of lazy_seq.bl.
;;
;; The compiler image has no actor runtime and one process (`self` is nil):
;; no cell can be running under another owner, so these are never reached
;; there, and they refuse as unavailable if they were.
(define (native-memo-bif! key value) (native-add-leaf! key value))
(define (native-memo-actor name)
 (let ((value (native-fetch-value "native.kernel" name #t)))
  (if (eq? value native-missing) #f value)))
(define (native-memo-actor-call name . arguments)
 (let ((f (native-memo-actor name)))
  (if f (bl-invoke f arguments)
   (native-raise (bl-key "error") (bl-tuple (list (bl-key "native_unsupported") name)) (native-capture-stack)))))
;; Each process has its own dictionary, as on BEAM: `get`/`put`/`erase`
;; (host-leaves.scm) read and write the running actor's map; outside any actor
;; (self nil) the image's single dictionary is used, as before. Another
;; process's dictionary is readable only through `process_info`, and only
;; while that process is alive.
(define native-memo-root-pdict native-pdict)
(define native-memo-dictionaries (make-table test: equal?))
(set! native-pdict
 (lambda value
  (let ((self (h-self)))
   (cond ((bl-is-nil self) (apply native-memo-root-pdict value))
    ((null? value) (table-ref native-memo-dictionaries self (bl-empty-map)))
    (else (table-set! native-memo-dictionaries self (car value)))))))
(define (native-memo-dictionary-of pid)
 (cond ((bl-key-equal? pid (h-self)) (native-pdict))
  ((and (not (bl-is-nil pid)) (native-memo-actor "rt-alive?")
        (bl-truthy (native-memo-actor-call "rt-alive?" pid)))
   (table-ref native-memo-dictionaries pid (bl-empty-map)))
  (else (table-set! native-memo-dictionaries pid) #f)))
(native-memo-bif! "erlang/self/0" (lambda () (h-self)))
(native-memo-bif! "erlang/node/0" (lambda () (bl-key "nonode@nohost")))
(native-memo-bif! "erlang/node/1" (lambda (pid) (bl-key "nonode@nohost")))
(native-memo-bif! "erlang/process_info/2"
 (lambda (pid item)
  (if (not (and (bl-tag? item 'tuple) (= 2 (vector-length (vector-ref item 1)))
                (eq? (bl-nth item 0) (bl-key "dictionary"))))
   (native-badarg "process_info item"))
  (let ((dictionary (native-memo-dictionary-of pid)))
   (if dictionary
    (bl-make-tuple item (bl-get dictionary (bl-nth item 1) (bl-key "undefined")))
    (bl-key "undefined")))))
;; An actor pid is the runtime's `[:pid runtime serial]` handle.
(native-replace-leaf! "erlang/is_pid/1"
 (let ((previous (native-leaf "erlang/is_pid/1")))
  (lambda (x)
   (if (native-memo-actor "rt-pid?") (bl-truthy (native-memo-actor-call "rt-pid?" x)) (previous x)))))
;; The runtime posts a monitor's DOWN as `[:down ref :process pid reason]`;
;; `receive_attempt` selects it by the monitor reference, not by the tag.
(native-memo-bif! "Elixir.Process/monitor/1"
 (lambda (pid) (native-memo-actor-call "native-monitor!" (bl-key "process") pid)))
(native-memo-bif! "Elixir.Process/demonitor/2"
 (lambda (ref options) (native-memo-actor-call "native-demonitor!" ref options)))
(native-memo-bif! "Elixir.Process/sleep/1" (native-memo-unsupported "Elixir.Process/sleep/1"))
(native-memo-bif! "erlang/load_nif/2" (native-memo-unsupported "erlang/load_nif/2"))
(native-memo-bif! "global/trans/2" (native-memo-unsupported "global/trans/2"))
(native-memo-bif! "erlang/nif_error/1"
 (lambda (reason) (native-raise (bl-key "error") reason (native-capture-stack))))
(native-memo-bif! "Elixir.System/monotonic_time/1"
 (lambda (unit) ((native-leaf "erlang/monotonic_time/1") unit)))
(native-memo-bif! "erlang/garbage_collect/0" (lambda () (##gc) #t))
(native-memo-bif! "erlang/system_info/1"
 (lambda (item) (if (eq? item (bl-key "wordsize")) 8 (native-badarg "system_info item"))))
(native-memo-bif! "Elixir.Application/get_env/3" (lambda (app key default) default))
(native-memo-bif! "Elixir.Integer/to_string/1" (lambda (n) (number->string n)))
(native-memo-bif! "Elixir.Path/join/2" (lambda (a b) (string-append a "/" b)))
(native-memo-bif! "Elixir.Enum/take/2"
 (lambda (xs n)
  (if (and (h-is-int n) (>= n 0)) (native-take (native-finite-items xs) n) (native-badarg "Enum.take count"))))
(native-memo-bif! "Elixir.Enumerable/impl_for/1"
 (lambda (x) (if (and (bl-tag? x 'map) (bl-is-nil (native-struct-module x))) (bl-key "Elixir.Enumerable.Map") bl-nil)))
;; `erlang/fun_info/2` is not defined here: the main thread adds one native
;; leaf for every host module at integration (speed/lazy/RESULT.md).
;; `erts_debug:flat_size/1`: the term's size in words, the estimate the budget
;; charges. A procedure is one word: native closures are opaque, so a pending
;; recipe is constant size. A reference stops the walk, as a resource does.
(native-memo-bif! "erts_debug/flat_size/1"
 (lambda (term)
  (let loop ((todo (list term)) (words 0))
   (if (null? todo) words
    (let ((x (car todo)) (rest (cdr todo)))
     (cond ((pair? x) (loop (cons (car x) (cons (cdr x) rest)) (+ words 2)))
      ((string? x) (loop rest (+ words 3 (quotient (string-length x) 8))))
      ((native-reference? x) (loop rest (+ words 1)))
      ((bl-tag? x 'tuple) (loop (append (bl-items x) rest) (+ words 1 (vector-length (vector-ref x 1)))))
      ((bl-tag? x 'map)
       (let ((pairs (native-map-pairs x)))
        (loop (append (apply append (map (lambda (p) (list (bl-nth p 0) (bl-nth p 1))) pairs)) rest)
              (+ words 3 (* 2 (length pairs))))))
      ((bl-tag? x 'vec) (loop (append (bl-items x) rest) (+ words 4)))
      (else (loop rest (+ words (if (and (integer? x) (not (fixnum? x))) 3 0))))))))))
