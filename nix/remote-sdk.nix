# The SDK a check host builds for a mirrored source (scripts/remote-check): the
# same production nix/ci-check.nix runs when it is given no SDK, kept as its own
# GC root so the host's next run names it as `previous` and restores every
# unchanged unit instead of shipping a 6.5 GB SDK closure to the host.
{ source, previous ? null }:
let input = import ./ci-check-source.nix { inherit source; };
in import (input + "/nix/sdk-artifact.nix") { source = toString input; inherit previous; }
