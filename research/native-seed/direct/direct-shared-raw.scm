;; Append once after direct-machine.scm when the shared strict raw apply ABI
;; (native-raw-function? / native-raw-apply) is present in the frozen value host.
;; A C closure is this backend's actual raw function. Tagged multi dispatchers
;; remain tuples and callable maps/keywords remain non-functions.
(define native-c-original-raw-function? native-raw-function?)
(set! native-raw-function? (lambda (value)
 (or (native-c-closure? value) (native-c-original-raw-function? value))))
