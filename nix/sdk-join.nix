# The SDK image: the producer's library joined with the current native set.
#
# The library (payload + unit store) is a function of the sources, compiler,
# dependencies and the mandatory lazy_memo native; units are keyed on that
# native's build identity alone. The optional native hosts load from
# priv/native, whose physical file is their authority, and no SDK byte records
# them. So a native edit rebuilds the native set and this join only: copy the
# library payload, install the current natives, pack and verify the portable
# drop, and write the launchers. Nothing here runs the producer.
{ pkgs, library, natives, nativeCrates, drop-tools, buildCheckout, coordinator,
  compiler, dependencies, formalWorker, src, libraryIdentity }:
pkgs.runCommand "beam-lisp-sdk-image-0.1.0" {
  nativeBuildInputs = [ pkgs.jq pkgs.coreutils ];
  # A copy and a pack of an image the builder already produced.
  preferLocalBuild = true;
} ''
  sdk="$out"
  mkdir -p "$sdk"
  cp -a --reflink=auto --no-preserve=ownership ${library}/payload "$sdk/payload"
  chmod -R u+w "$sdk/payload"
  for application in "$sdk"/payload/lib/beam_lisp-*; do
    for crate in ${toString nativeCrates}; do
      install -m755 ${natives}/$crate.so "$application/priv/native/$crate.so"
    done
  done
  ln -s ${library}/unit-store "$sdk/unit-store"

  # The portable drop of exactly this payload, checked against its own trailer.
  ${drop-tools}/bin/drop pack --release "$sdk/payload" \
    --launcher ${drop-tools}/bin/drop-launcher --out "$sdk/bl"
  info=$(${drop-tools}/bin/drop inspect "$sdk/bl")
  offset=$(printf '%s\n' "$info" | sed -n 's/^payload: *offset=\([0-9]*\) len=.*/\1/p')
  length=$(printf '%s\n' "$info" | sed -n 's/^payload: *offset=[0-9]* len=\([0-9]*\) .*/\1/p')
  digest=$(printf '%s\n' "$info" | sed -n 's/^sha256: *\([0-9a-f]*\)$/\1/p')
  size=$(stat -c %s "$sdk/bl")
  test -n "$offset" -a -n "$length" -a -n "$digest"
  test "$size" -eq $((offset + length + 56))
  test "$(tail -c +$((offset + 1)) "$sdk/bl" | head -c "$length" | sha256sum | cut -d' ' -f1)" = "$digest"
  chmod 555 "$sdk/bl"

  ln -s payload/lib "$sdk/lib"
  for application in "$sdk"/lib/beam_lisp-*; do
    ln -s "lib/$(basename "$application")" "$sdk/image"
  done
  mkdir -p "$sdk/bin"
  cat > "$sdk/boot.exs" <<EOF
  # The platform owns the running Elixir installation and its CLI scripts.
  # The portable payload's ebin-only copy must not shadow that installation.
  elixir_ebin = :code.lib_dir(:elixir, :ebin)
  for path <- Path.wildcard("$sdk/lib/*/ebin"), do: Code.prepend_path(path)
  Code.prepend_path(elixir_ebin)
  Code.prepend_path("$sdk/image/ebin")
  :code.del_path(~c".")
  BeamLisp.Launcher.start_app!(System.argv(), %{})
  EOF
  cat > "$sdk/bin/bl" <<EOF
  #!${pkgs.runtimeShell}
  unset BL_INTERNAL_PRODUCER
  export PATH=${buildCheckout}/bin:\$PATH
  export BL_ARTIFACT_PLATFORM=${buildCheckout}/artifact-platform
  export BL_PREPARATION_COORDINATOR=${coordinator}
  export BL_SDK_PRODUCT="$sdk"
  export BL_ROOT="$sdk/image" BL_EBIN="$sdk/image/ebin" BL_BUILD_ID=src BEAM_LISP_DEV=0
  export BL_BIN=${buildCheckout}/bin/drop-launcher
  export BL_PREPARED_NATIVES="$(readlink -f ${buildCheckout}/native-products)"
  exec ${buildCheckout}/bin/elixir "$sdk/boot.exs" "\$@"
  EOF
  chmod 555 "$sdk/bin/bl"
  printf '%s\n' '${builtins.toJSON {
    version = 1;
    kind = "sdk";
    producerAPI = 2;
    compiler = toString compiler;
    dependencies = toString dependencies;
    platform = toString buildCheckout;
    coordinator = toString coordinator;
    formalWorker = toString formalWorker;
    library = toString library;
    inherit libraryIdentity;
    target = "x86_64-linux";
  }}' > "$sdk/artifact.json"
  jq --arg source "${src}" '. + {source: $source}' "$sdk/artifact.json" > "$sdk/artifact.tmp"
  mv "$sdk/artifact.tmp" "$sdk/artifact.json"
''
