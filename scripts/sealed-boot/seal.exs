# Seal a scratch copy of an SDK image: overlay edited host beams (with their
# floor manifest digests), then run the producer's sealing functions in this
# image, exactly as `selfbuild.bl` do-prime does at SDK build time.
#   elixir -pa DEPS... -pa IMG/ebin seal.exs IMG OVERLAY_DIR [image-metadata|none]
[img, overlay, mode] = System.argv()
priv = Path.join(img, "priv")
seed = Path.join(priv, "bootstrap/seed")
manifest_path = Path.join(seed, "manifest.term")
{:ok, [manifest]} = :file.consult(String.to_charlist(manifest_path))
hex = fn b -> Base.encode16(:crypto.hash(:sha256, b), case: :lower) end
manifest =
  Enum.reduce(Path.wildcard(Path.join(overlay, "*.beam")), manifest, fn path, acc ->
    name = Path.basename(path)
    bytes = File.read!(path)
    cond do
      not Map.has_key?(acc["modules"], name) -> acc
      acc["modules"][name] == hex.(bytes) -> acc
      true ->
        File.write!(Path.join(seed, name), bytes)
        File.write!(Path.join(img, "ebin/" <> name), bytes)
        IO.puts("seal: overlay #{name}")
        put_in(acc, ["modules", name], hex.(bytes))
    end
  end)
File.write!(manifest_path, :io_lib.format(~c"~tp.~n", [manifest]))
{:ok, _} = Application.ensure_all_started(:beam_lisp)
t = fn label, f -> t0 = System.monotonic_time(:millisecond); r = f.(); IO.puts("seal: #{label} #{inspect(r)} in #{System.monotonic_time(:millisecond) - t0} ms"); r end
t.("prime-native-declarations", fn -> BeamLisp.AOT.prime_native_declarations!(priv) end)
t.("prime-seed-metadata", fn -> BeamLisp.AOT.prime_seed_metadata!(priv) end)
if mode == "image-metadata" do
  t.("prime-image-metadata", fn -> BeamLisp.AOT.prime_image_metadata!(priv) end)
  # The sealed rows must equal what this VM decodes from the same bytes.
  table = :erlang.binary_to_term(File.read!(BeamLisp.AOT.image_metadata_table_path(priv)))
  root = priv
  inv = BeamLisp.AOT.decode_sdk_inventory!(File.read!(Path.join(root, "sdk-code.term")))
  {same, differ} = Enum.reduce(table.rows, {0, 0}, fn {identity, entry}, {s, d} ->
    row = Map.fetch!(inv, identity)
    bytes = File.read!(Path.join(img, "ebin/" <> identity <> ".beam"))
    live = BeamLisp.AOT.decode_sdk_image_metadata!(identity, row, bytes)
    if :erlang.binary_to_term(entry.decoded) == live, do: {s + 1, d}, else: {s, d + 1}
  end)
  IO.puts("seal: image-metadata rows=#{map_size(table.rows)} of #{map_size(inv)} equal=#{same} differ=#{differ} bytes=#{File.stat!(BeamLisp.AOT.image_metadata_table_path(priv)).size}")
end
System.halt(0)
