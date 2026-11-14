# Reuse the actual device/API/empty-VM probe, with a distinct derivation so a
# cached observation cannot be mistaken for a new sandbox capability check.
{ nonce }:
(import ./scalar-kvm-builder-probe.nix).overrideAttrs (_: {
  name = "formal-wide-kvm-sandbox-probe-${nonce}";
  probeNonce = nonce;
})
