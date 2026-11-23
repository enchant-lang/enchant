-module(u9_procs).
-export([start/0, stop/1]).
start() ->
    Tracer = spawn(fun() -> T = ets:new(u9_procs, [bag, public]), loop(T) end),
    register(u9_procs_tracer, Tracer),
    erlang:trace(all, true, [procs, timestamp, {tracer, Tracer}]),
    case catch erlang:trace(new_processes, true, [procs, timestamp, {tracer, Tracer}]) of _ -> ok end,
    ok.
loop(T) ->
    receive
        {trace_ts, P, spawn, Child, MFA, TS} ->
            ets:insert(T, {spawn, {parent_name(P), MFA}}), loop(T);
        {trace_ts, P, exit, Reason, TS} ->
            ets:insert(T, {exit, {parent_name(P), class(Reason)}}), loop(T);
        {trace_ts, P, register, Name, TS} ->
            ets:insert(T, {register, Name}), loop(T);
        {stop, From} -> From ! {done, ets:tab2list(T)}
    end.
parent_name(P) when is_pid(P) ->
    case erlang:process_info(P, registered_name) of {registered_name, N} -> N; _ -> {pid, node(P)} end;
parent_name(X) -> X.
class(normal) -> normal; class(shutdown) -> shutdown; class({shutdown, _}) -> shutdown; class(killed) -> killed; class(_) -> other.
stop(Path) ->
    catch erlang:trace(all, false, [procs]),
    u9_procs_tracer ! {stop, self()},
    Rows = receive {done, R} -> R after 5000 -> [] end,
    Fmt = fun({{A, B}}) -> io_lib:format("~p ~p~n", [A, B]); (_) -> "" end,
    Out = [io_lib:format("~p ~p~n", [K, V]) || {K, V} <- Rows],
    file:write_file(Path, Out), length(Rows).
