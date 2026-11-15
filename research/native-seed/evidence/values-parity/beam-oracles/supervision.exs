
defmodule SW do
  use GenServer
  def start_link(tag), do: GenServer.start_link(__MODULE__, tag)
  def init(tag), do: {:ok, tag}
  def handle_cast(:crash, _tag), do: exit(:crash)
  def handle_cast(:exit_normal, _tag), do: {:stop, :normal, nil}
end

defmodule SUP do
  def child(id, restart \\ :permanent), do: Supervisor.child_spec({SW, id}, id: id, restart: restart)
  def pids(sup), do: Map.new(Supervisor.which_children(sup), fn {id, pid, _, _} -> {id, pid} end)
  def settle, do: Process.sleep(60)
  def running?(p), do: is_pid(p) and Process.alive?(p)
  def cell(x, y), do: (if x == y, do: "same", else: "changed")
end

Process.flag(:trap_exit, true)

{:ok, s} = Supervisor.start_link([SUP.child(:a), SUP.child(:b), SUP.child(:c)], strategy: :one_for_one)
m0 = SUP.pids(s); Process.exit(m0[:b], :kill); SUP.settle(); m1 = SUP.pids(s)
IO.puts("SUP-PARITY one-for-one-others-stable #{m1[:a] == m0[:a] and m1[:c] == m0[:c]}")
IO.puts("SUP-PARITY one-for-one-dead-changed #{m1[:b] != m0[:b]}")

{:ok, f} = Supervisor.start_link([SUP.child(:a), SUP.child(:b), SUP.child(:c)], strategy: :one_for_all)
f0 = SUP.pids(f); Process.exit(f0[:b], :kill); SUP.settle(); f1 = SUP.pids(f)
IO.puts("SUP-PARITY one-for-all-all-changed #{f1[:a] != f0[:a] and f1[:b] != f0[:b] and f1[:c] != f0[:c]}")

{:ok, r} = Supervisor.start_link([SUP.child(:a), SUP.child(:b), SUP.child(:c)], strategy: :rest_for_one)
r0 = SUP.pids(r); Process.exit(r0[:a], :kill); SUP.settle(); r1 = SUP.pids(r)
IO.puts("SUP-PARITY rest-for-one-first-all-changed #{r1[:a] != r0[:a] and r1[:b] != r0[:b] and r1[:c] != r0[:c]}")
Process.exit(r1[:c], :kill); SUP.settle(); r2 = SUP.pids(r)
IO.puts("SUP-PARITY rest-for-one-last-only-changed #{r2[:a] == r1[:a] and r2[:b] == r1[:b] and r2[:c] != r1[:c]}")

{:ok, t} = Supervisor.start_link([SUP.child(:t, :transient)], strategy: :one_for_one)
t0 = SUP.pids(t); Process.exit(t0[:t], :kill); SUP.settle(); t1 = SUP.pids(t)
IO.puts("SUP-PARITY transient-crash-restarted #{SUP.running?(t1[:t]) and t1[:t] != t0[:t]}")
GenServer.cast(t1[:t], :exit_normal); SUP.settle(); t2 = SUP.pids(t)
IO.puts("SUP-PARITY transient-normal-not-restarted #{not SUP.running?(t2[:t])}")

{:ok, x} = Supervisor.start_link([SUP.child(:x, :temporary)], strategy: :one_for_one)
x0 = SUP.pids(x); Process.exit(x0[:x], :kill); SUP.settle(); x1 = SUP.pids(x)
IO.puts("SUP-PARITY temporary-crash-not-restarted #{not SUP.running?(x1[:x])}")

{:ok, p} = Supervisor.start_link([SUP.child(:p, :permanent)], strategy: :one_for_one)
p0 = SUP.pids(p); GenServer.cast(p0[:p], :exit_normal); SUP.settle(); p1 = SUP.pids(p)
IO.puts("SUP-PARITY permanent-normal-restarted #{SUP.running?(p1[:p]) and p1[:p] != p0[:p]}")

{:ok, m} = Supervisor.start_link([SUP.child(:s)], strategy: :one_for_one, max_restarts: 2, max_seconds: 60)
ref = Process.monitor(m)
for _ <- 1..5 do
  if Process.alive?(m) do
    case SUP.pids(m)[:s] do
      q when is_pid(q) -> Process.exit(q, :kill)
      _ -> :ok
    end
  end
  SUP.settle()
end
reason = receive do {:DOWN, ^ref, :process, _, rr} -> rr after 2000 -> :no_down end
IO.puts("SUP-PARITY max-restarts-escalates #{reason != :no_down}")

# The selected TRACE: rest_for_one, crash the first child then the last, and
# report per step which incarnations changed.
{:ok, tt} = Supervisor.start_link([SUP.child(:a), SUP.child(:b), SUP.child(:c)], strategy: :rest_for_one)
q0 = SUP.pids(tt)
Process.exit(q0[:a], :kill); SUP.settle(); q1 = SUP.pids(tt)
IO.puts("SUP-TRACE 1 #{SUP.cell(q0[:a], q1[:a])} #{SUP.cell(q0[:b], q1[:b])} #{SUP.cell(q0[:c], q1[:c])}")
Process.exit(q1[:c], :kill); SUP.settle(); q2 = SUP.pids(tt)
IO.puts("SUP-TRACE 2 #{SUP.cell(q1[:a], q2[:a])} #{SUP.cell(q1[:b], q2[:b])} #{SUP.cell(q1[:c], q2[:c])}")
