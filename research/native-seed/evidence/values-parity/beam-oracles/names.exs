
parent = self()
holder = spawn(fn ->
  Process.register(self(), :parity_srv)
  send(parent, :parity_ready)
  receive do :die -> :ok end
end)
receive do :parity_ready -> :ok after 2000 -> :ok end
mref = Process.monitor(holder)
whereis_live = case Process.whereis(:parity_srv) do nil -> "nil"; _ -> "pid" end
double = try do
    Process.register(self(), :parity_srv)
    "accepted"
  catch
    _, _ -> "refused"
  end
send(holder, :die)
receive do {:DOWN, ^mref, :process, _, _} -> :ok after 2000 -> :ok end
whereis_dead = case Process.whereis(:parity_srv) do nil -> "nil"; _ -> "pid" end
bounded = try do
    GenServer.call(spawn(fn -> receive do :never -> :ok end end), :x, 30)
    "answered"
  catch
    :exit, _ -> "exits"
  end
IO.puts("NAMES-PARITY whereis-live " <> whereis_live)
IO.puts("NAMES-PARITY double-register " <> double)
IO.puts("NAMES-PARITY whereis-dead " <> whereis_dead)
IO.puts("NAMES-PARITY call-bounded " <> bounded)
