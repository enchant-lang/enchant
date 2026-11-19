;; These are module exports or aliases of existing first-party operations. Each
;; exception uses the same pinned host source at its own SDK module identity.
(native-add-leaf! "Elixir.Map/values/1" (native-leaf "maps/values/1"))
(native-add-leaf! "Elixir.BeamLisp.Reader/read_syntax/2" (native-global-exact "host.reader" "read_syntax"))
(for-each
 (lambda (item)
   (native-add-leaf! (string-append (cadr item) "/exception/1")
                     (native-global-exact (car item) "exception")))
 '(("host.reader-exception.syntax" "Elixir.BeamLisp.Reader.SyntaxError")
   ("host.reader-exception.limit" "Elixir.BeamLisp.Reader.AtomLimitError")))
