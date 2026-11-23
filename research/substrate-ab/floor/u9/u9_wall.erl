-module(u9_wall).
-export([start/1, stop/1]).
%% Inclusive wall durations of selected calls across all processes.
start(MFAs) ->
    Tracer = spawn(fun() -> T = ets:new(u9_wall, [public, set]), persistent_term:put(u9_wall_tab, T), collect(T, #{}) end),
    register(u9_wall_tracer, Tracer),
    erlang:trace(all, true, [call, timestamp, {tracer, Tracer}]),
    persistent_term:put(u9_wall_mfas, MFAs),
    [erlang:trace_pattern(MFA, [{'_', [], [{return_trace}, {message, {caller}}]}], []) || MFA <- MFAs],
    ok.
key(M, F, A) when is_list(A) -> {M, F, length(A)};
key(M, F, A) -> {M, F, A}.
collect(T, Open) ->
    receive
        {trace_ts, P, call, {M, F, A}, Caller, TS} ->
            collect(T, maps:update_with({P, M, F, length(A)}, fun(L) -> [{Caller, TS} | L] end, [{Caller, TS}], Open));
        {trace_ts, P, call, {M, F, A}, TS} ->
            collect(T, maps:update_with({P, M, F, length(A)}, fun(L) -> [{none, TS} | L] end, [{none, TS}], Open));
        {trace_ts, P, return_from, {M, F, Ar}, _, TS} ->
            case maps:get({P, M, F, Ar}, Open, []) of
                [{Caller, T0} | Rest] ->
                    Us = timer:now_diff(TS, T0),
                    K = {key(M, F, Ar), Caller},
                    ets:update_counter(T, K, [{2, 1}, {3, Us}], {K, 0, 0}),
                    collect(T, Open#{{P, M, F, Ar} => Rest});
                [] -> collect(T, Open)
            end;
        {stop, From} -> From ! {done, lists:reverse(lists:keysort(3, ets:tab2list(T)))}
    end.
stop(Path) ->
    try
        erlang:trace(all, false, [call]),
        [erlang:trace_pattern(MFA, false, []) || MFA <- persistent_term:get(u9_wall_mfas, [])],
        u9_wall_tracer ! {stop, self()},
        Rows = receive {done, R} -> R after 10000 -> [] end,
        Tot = lists:sum([Us || {_, _, Us} <- Rows]),
        file:write_file(Path, [io_lib:format("~p calls ~p us ~p~n", [C, Us, K]) || {K, C, Us} <- lists:reverse(lists:keysort(3, Rows))] ++
                         [io_lib:format("TOTAL ~p us~n", [Tot])]),
        length(Rows)
    catch C:E:St -> file:write_file(Path, io_lib:format("ERROR ~p ~p ~p~n", [C, E, St])), 0 end.
