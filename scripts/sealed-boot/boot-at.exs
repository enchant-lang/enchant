# boot.exs of a store SDK, with the image chosen by the environment:
#   K1_LIB=<sdk>/lib K1_IMAGE=<image dir> elixir boot-at.exs [--script FILE ARGS | bl ARGS]
# Same code-path order as the SDK's boot.exs; `--script FILE` evaluates FILE
# (seal.exs, the phase probe) instead of starting the CLI.
elixir_ebin = :code.lib_dir(:elixir, :ebin)
for path <- Path.wildcard(Path.join(System.fetch_env!("K1_LIB"), "*/ebin")), do: Code.prepend_path(path)
Code.prepend_path(elixir_ebin)
Code.prepend_path(Path.join(System.fetch_env!("K1_IMAGE"), "ebin"))
:code.del_path(~c".")
case System.argv() do
  ["--script", file | rest] -> System.argv(rest); Code.eval_file(file)
  argv -> BeamLisp.Launcher.start_app!(argv, %{})
end
