# The store launcher's start_app! split at its stage boundaries (ms since VM
# start, on stderr as `k1 STAGE MS`), then `bl.cli` runs the given argv.
st = :erlang.system_info(:start_time)
ms = fn -> System.convert_time_unit(System.monotonic_time() - st, :native, :millisecond) end
mark = fn n -> IO.puts(:stderr, "k1 #{n} #{ms.()}") end
mark.("exs")
Application.load(:beam_lisp)
for app <- Application.spec(:beam_lisp, :applications), do: {:ok, _} = Application.ensure_all_started(app)
mark.("deps")
{:ok, _} = Application.ensure_all_started(:beam_lisp)
mark.("beam_lisp")
BeamLisp.Loader.ensure_loaded("vm.native")
BeamLisp.Ns.Rt.invoke(BeamLisp.Env.fetch!("vm.native", "build-all!"), [])
mark.("build-all")
BeamLisp.Loader.ensure_loaded("bl.cli")
mark.("bl.cli")
r = BeamLisp.Ns.Rt.invoke(BeamLisp.Env.fetch!("bl.cli", "run-argv"), [System.argv()])
mark.("run")
System.halt(r)
