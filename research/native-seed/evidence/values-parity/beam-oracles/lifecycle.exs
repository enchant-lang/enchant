
defmodule Parity do
  def mon(fun) do
    pid = spawn(fn -> receive do :go -> nil end; fun.() end)
    m = Process.monitor(pid)
    send(pid, :go)
    receive do {:DOWN, ^m, :process, ^pid, r} -> r after 5000 -> :timeout end
  end

  def explicit_kill do
    pid = spawn(fn -> receive do :never -> nil end end)
    m = Process.monitor(pid)
    :erlang.exit(pid, :kill)
    receive do {:DOWN, ^m, :process, ^pid, r} -> r after 5000 -> :timeout end
  end

  def link_nontrap(child) do
    me = self()
    pid = spawn(fn ->
      _c = spawn_link(child)
      r = receive do :never -> :survived after 400 -> :survived end
      send(me, {:r, r})
    end)
    m = Process.monitor(pid)
    receive do
      {:r, r} -> r
      {:DOWN, ^m, :process, ^pid, r} -> r
    after 5000 -> :timeout end
  end

  def link_trap(child) do
    me = self()
    spawn(fn ->
      Process.flag(:trap_exit, true)
      c = spawn_link(child)
      r = receive do {:EXIT, ^c, reason} -> reason after 3000 -> :no_exit end
      send(me, {:r, r})
    end)
    receive do {:r, r} -> r after 5000 -> :timeout end
  end

  def kill_linked_child_from_other do
    me = self()
    q = spawn(fn ->
      c = spawn_link(fn -> receive do :never -> nil end end)
      send(me, {:child, c})
      receive do :never -> nil end
    end)
    m = Process.monitor(q)
    child = receive do {:child, c} -> c after 3000 -> :no_child end
    :erlang.exit(child, :kill)
    receive do {:DOWN, ^m, :process, ^q, r} -> r after 5000 -> :timeout end
  end

  def self_normal, do: mon(fn -> :erlang.exit(self(), :normal) end)

  def self_normal_trap do
    me = self()
    spawn(fn ->
      Process.flag(:trap_exit, true)
      :erlang.exit(self(), :normal)
      r = receive do {:EXIT, _, reason} -> reason after 300 -> :no_message end
      send(me, {:r, r})
    end)
    receive do {:r, r} -> r after 3000 -> :timeout end
  end

  def other_normal do
    t = spawn(fn -> receive do :never -> :survived after 400 -> :survived end end)
    :erlang.exit(t, :normal)
    alive = Process.alive?(t)
    Process.exit(t, :kill)
    if alive, do: :survived, else: :died
  end

  def running_kill_linked do
    mon(fn ->
      c = spawn_link(fn -> receive do :never -> nil end end)
      :erlang.exit(c, :kill)
      receive do :never -> :survived after 400 -> :survived end
    end)
  end
end

emit = fn k, v -> IO.puts("EXIT-PARITY #{k} #{inspect(v)}") end
emit.("d1-explicit-kill", Parity.explicit_kill())
emit.("d1-exit1-kill", Parity.mon(fn -> exit(:kill) end))
emit.("d1-link-exit1-kill-nontrap", Parity.link_nontrap(fn -> exit(:kill) end))
emit.("d1-link-exit1-kill-trap", Parity.link_trap(fn -> exit(:kill) end))
emit.("d1-link-explicit-kill-nontrap", Parity.kill_linked_child_from_other())
emit.("d2-self-normal", Parity.self_normal())
emit.("d2-self-normal-trap", Parity.self_normal_trap())
emit.("d2-other-normal-nontrap", Parity.other_normal())
emit.("d2-link-normal-nontrap", Parity.link_nontrap(fn -> :ok end))
emit.("d2-link-normal-trap", Parity.link_trap(fn -> :ok end))
emit.("f2-linked-kill", Parity.running_kill_linked())
