-module(ab_wall).
-export([start/1, stop/1, safe_stop/1]).
safe_stop(Path) -> try stop(Path) catch C:E:St -> file:write_file(Path, io_lib:format("~p ~p ~p~n", [C, E, St])) end.
%% Wall-clock durations of selected calls (call -> return_from) across all processes.
start(MFAs) ->
    Tracer = spawn(fun() -> T = ets:new(ab_wall, [public, set]), persistent_term:put(ab_wall_tab, T), collect(T, #{}) end),
    register(ab_wall_tracer, Tracer),
    erlang:trace(all, true, [call, timestamp, {tracer, Tracer}]),
    [erlang:trace_pattern(MFA, [{'_', [], [{return_trace}, {message, {caller}}]}], [local]) || MFA <- MFAs],
    ok.
key(gen, do_call, [Target | _]) -> {gen_call, name(Target)};
key('Elixir.BeamLisp.Env', acquire_local_lock, [Row]) -> {lock, lockname(element(1, Row))};
key('Elixir.BeamLisp.Env', with_local_lock, [_, LockKey, _]) -> {with_lock, lockname(LockKey)};
key(M, F, Args) -> {M, F, length(Args)}.
lockname(K) when is_tuple(K), tuple_size(K) > 0 -> list_to_tuple([case is_reference(X) orelse is_pid(X) of true -> '*'; false -> X end || X <- tuple_to_list(K)]);
lockname(K) -> K.
name(P) when is_pid(P) -> case erlang:process_info(P, registered_name) of {registered_name, N} -> N; _ -> pid end;
name(N) -> N.
collect(T, Open) ->
    receive
        {trace_ts, P, call, {M, F, A}, Caller, TS} ->
            K = {key(M, F, A), Caller},
            collect(T, maps:update_with({P, M, F, length(A)}, fun(L) -> [{K, TS} | L] end, [{K, TS}], Open));
        {trace_ts, P, call, {M, F, A}, TS} ->
            K = key(M, F, A), collect(T, maps:update_with({P, M, F, length(A)}, fun(L) -> [{K, TS} | L] end, [{K, TS}], Open));
        {trace_ts, P, return_from, {M, F, Ar}, _, TS} ->
            case maps:get({P, M, F, Ar}, Open, []) of
                [{K, T0} | Rest] ->
                    Us = timer:now_diff(TS, T0),
                    ets:update_counter(T, K, [{2, 1}, {3, Us}], {K, 0, 0}),
                    collect(T, Open#{{P, M, F, Ar} => Rest});
                [] -> collect(T, Open)
            end;
        {stop, From} ->
            From ! {done, lists:reverse(lists:keysort(3, ets:tab2list(T)))}
    end.
stop(Path) ->
    erlang:trace(all, false, [call]), erlang:trace_pattern({'_', '_', '_'}, false, [local]),
    ab_wall_tracer ! {stop, self()}, Rows = receive {done, R} -> R after 5000 -> [] end,
    file:write_file(Path, [io_lib:format("~p calls ~p ms ~p~n", [C, Us div 1000, K]) || {K, C, Us} <- Rows]).
