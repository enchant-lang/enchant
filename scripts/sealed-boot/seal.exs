# Seal a scratch copy of an SDK image: overlay edited host beams (with their
# floor manifest digests), then run the producer's sealing functions in this
# image, exactly as `selfbuild.bl` do-prime does at SDK build time.
#   boot-at.exs --script seal.exs IMG OVERLAY_DIR overlay
#   boot-at.exs --script seal.exs IMG OVERLAY_DIR image-metadata|none
# Two VMs: the overlay is written by one that never starts the language, and
# the sealing VM starts on the finished image (in one VM, the app start after
# rewriting its own floor refused the AOT producer proof).
[img, overlay, mode] = System.argv()
priv = Path.join(img, "priv")
seed = Path.join(priv, "bootstrap/seed")
manifest_path = Path.join(seed, "manifest.term")
{:ok, [manifest]} = :file.consult(String.to_charlist(manifest_path))
hex = fn b -> Base.encode16(:crypto.hash(:sha256, b), case: :lower) end
# The image keeps its ORIGINAL priv/host sources: `aot.bl` is a codegen input,
# so its edited text would rotate the compiler key and stale every unit. An
# overlaid host beam is therefore restamped with the shipped source's digest
# (`bl_source_hash`, the attribute the preinit floor proof compares). This is
# an experiment device for timing edited host CODE on an unchanged image; it is
# never an SDK and never qualifies a compiler.
leaves = %{"Elixir.BeamLisp.AOT.beam" => "aot.bl", "Elixir.BeamLisp.AOTCache.beam" => "aot_cache.bl",
           "Elixir.BeamLisp.Env.beam" => "env.bl", "Elixir.BeamLisp.Loader.beam" => "loader.bl",
           "Elixir.BeamLisp.Bootstrap.beam" => "bootstrap.bl", "Elixir.BeamLisp.BuildPlan.beam" => "build_plan.bl",
           "Elixir.BeamLisp.PackageAuthority.beam" => "package_authority.bl", "Elixir.BeamLisp.Reader.beam" => "reader.bl"}
restamp = fn name, bytes ->
  case Map.fetch(leaves, name) do
    :error -> bytes
    {:ok, leaf} ->
      shipped = hex.(File.read!(Path.join(priv, "host/" <> leaf)))
      {:ok, _, chunks} = :beam_lib.all_chunks(bytes)
      chunks = Enum.map(chunks, fn
        {~c"Attr", data} ->
          attrs = :erlang.binary_to_term(data)
          {~c"Attr", :erlang.term_to_binary(List.keystore(attrs, :bl_source_hash, 0, {:bl_source_hash, shipped}))}
        other -> other
      end)
      {:ok, rebuilt} = :beam_lib.build_module(chunks)
      rebuilt
  end
end
manifest =
  Enum.reduce(Path.wildcard(Path.join(overlay, "*.beam")), manifest, fn path, acc ->
    name = Path.basename(path)
    raw = File.read!(path)
    cond do
      not Map.has_key?(acc["modules"], name) -> acc
      acc["modules"][name] == hex.(raw) -> acc
      true ->
        bytes = restamp.(name, raw)
        File.write!(Path.join(seed, name), bytes)
        File.write!(Path.join(img, "ebin/" <> name), bytes)
        IO.puts("seal: overlay #{name}")
        put_in(acc, ["modules", name], hex.(bytes))
    end
  end)
File.write!(manifest_path, :io_lib.format(~c"~tp.~n", [manifest]))
if mode == "overlay", do: System.halt(0)
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
