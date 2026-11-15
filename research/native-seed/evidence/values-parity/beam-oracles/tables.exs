
defmodule EtsParity do
  def heir_loop(parent) do
    receive do
      {:"ETS-TRANSFER", tid, from, data} ->
        send(parent, {:caught, tid, from, data})
        heir_loop(parent)
      {:give, tid, to} ->
        :ets.give_away(tid, to, :gift)
        send(parent, {:gave, tid})
        heir_loop(parent)
      :die -> :ok
    end
  end

  def probe(parent, tid) do
    v = fn f ->
      try do
        f.()
        :ok
      rescue
        _ -> :denied
      end
    end
    send(parent, {:probe, v.(fn -> :ets.lookup(tid, :k) end),
                  v.(fn -> :ets.insert(tid, {:p, 1}) end),
                  v.(fn -> :ets.give_away(tid, parent, :gift) end),
                  v.(fn -> :ets.delete(tid) end)})
  end

  def verdict(parent, mode, tid) do
    p = spawn(fn -> probe(parent, tid) end)
    {r, w, g, d} = receive do {:probe, a, b, c, e} -> {a, b, c, e} after 2000 -> {:none, :none, :none, :none} end
    Process.demonitor(Process.monitor(p), [:flush])
    IO.puts("TABLE-PARITY #{mode}-read-other #{r}")
    IO.puts("TABLE-PARITY #{mode}-write-other #{w}")
    IO.puts("TABLE-PARITY #{mode}-give-away-other #{g}")
    IO.puts("TABLE-PARITY #{mode}-destroy-other #{d}")
  end

  def run do
    parent = self()

    # an unheired owner dies: the table and its name go with it
    owner = spawn(fn ->
      t = :ets.new(:tbl_par_doomed, [:named_table])
      :ets.insert(t, {:k, 1})
      send(parent, {:ready, t})
      receive do :die -> :ok end
    end)
    tid = receive do {:ready, t} -> t after 2000 -> :none end
    ref = Process.monitor(owner)
    Process.exit(owner, :kill)
    receive do {:DOWN, ^ref, :process, _, _} -> :ok after 2000 -> :ok end
    IO.puts("TABLE-PARITY owner-death-destroys " <>
      (if :ets.info(tid) == :undefined, do: "destroyed", else: "alive"))
    IO.puts("TABLE-PARITY name-freed-on-destroy " <>
      (case :ets.whereis(:tbl_par_doomed) do :undefined -> "free"; _ -> "held" end))

    # an heir catches what a dead owner leaves, then hands it on
    heir = spawn(fn -> heir_loop(parent) end)
    o2 = spawn(fn ->
      t = :ets.new(:tbl_par_heired, [:set, {:heir, heir, :gift}])
      :ets.insert(t, {:k, 1})
      send(parent, {:ready2, t})
      receive do :die -> :ok end
    end)
    tid2 = receive do {:ready2, t} -> t after 2000 -> :none end
    ref2 = Process.monitor(o2)
    Process.exit(o2, :kill)
    receive do {:DOWN, ^ref2, :process, _, _} -> :ok after 2000 -> :ok end
    caught = receive do {:caught, t, from, data} -> {t, from, data} after 2000 -> {:none, :none, :none} end
    IO.puts("TABLE-PARITY heir-transfer " <> (if elem(caught, 0) == tid2, do: "transferred", else: "lost"))
    IO.puts("TABLE-PARITY heir-data #{caught |> elem(2)}")
    IO.puts("TABLE-PARITY heir-rows #{:ets.info(tid2, :size)}")
    IO.puts("TABLE-PARITY heir-owner " <> (if :ets.info(tid2, :owner) == heir, do: "heir", else: "other"))
    send(heir, {:give, tid2, parent})
    receive do {:gave, _} -> :ok after 2000 -> :ok end
    IO.puts("TABLE-PARITY give-away " <> (if :ets.info(tid2, :owner) == parent, do: "reclaimed", else: "other"))
    :ets.delete(tid2)
    send(heir, :die)

    # a duplicate name is refused; the first table stands
    kept = :ets.new(:tbl_par_kept, [:named_table])
    dup = try do
      :ets.new(:tbl_par_kept, [:named_table])
      "accepted"
    rescue
      _ -> "refused"
    end
    IO.puts("TABLE-PARITY duplicate-name #{dup}")
    :ets.delete(kept)

    # the counter (a key must exist there too), and the two answers a read can give
    ct = :ets.new(:tbl_par_ct, [:set, :public])
    :ets.insert(ct, {:n, 0})
    :ets.update_counter(ct, :n, 60)
    :ets.update_counter(ct, :n, 40)
    IO.puts("TABLE-PARITY update-counter-total #{:ets.lookup_element(ct, :n, 2)}")
    missing = try do
      :ets.update_counter(ct, :absent, 1)
      "accepted"
    rescue
      _ -> "refused"
    end
    IO.puts("TABLE-PARITY update-counter-missing-key #{missing}")
    :ets.insert(ct, {:nilrow, nil})
    IO.puts("TABLE-PARITY nil-row-present " <>
      (if :ets.lookup(ct, :nilrow) == [], do: "empty", else: "present"))
    IO.puts("TABLE-PARITY absent-row-empty " <>
      (if :ets.lookup(ct, :nope) == [], do: "empty", else: "present"))
    IO.puts("TABLE-PARITY lookup-shape-rows #{length(:ets.lookup(ct, :n))}")
    :ets.delete(ct)

    # the three access modes, seen from another process. A public table is a
    # WRITE all the way down, so the other process's :ets.delete/1 lands there.
    for mode <- [:private, :protected, :public] do
      t = :ets.new(:tbl_par_mode, [:set, mode])
      :ets.insert(t, {:k, 1})
      verdict(parent, mode, t)
      if :ets.info(t) != :undefined, do: :ets.delete(t)
    end
  end
end
EtsParity.run()
