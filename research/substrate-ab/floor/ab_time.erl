-module(ab_time).
-export([start/1, stop/2]).
%% call_time (own time, microseconds) for every function of the given modules.
start(Mods) ->
    [erlang:trace_pattern({M, '_', '_'}, true, [local, call_time]) || M <- Mods],
    T = spawn(fun() -> receive stop -> ok end end), register(ab_time_tracer, T),
    erlang:trace(all, true, [call, {tracer, T}]),
    persistent_term:put(ab_time_mods, Mods), ok.
stop(Path, Div) ->
    Mods = persistent_term:get(ab_time_mods),
    Rows = lists:append([[{Us, C, M, F, A} || {F, A} <- M:module_info(functions),
                          {call_time, L} <- [erlang:trace_info({M, F, A}, call_time)], is_list(L),
                          {C, Us} <- [lists:foldl(fun({_, C0, S, U}, {CA, UA}) -> {CA + C0, UA + S * 1000000 + U} end, {0, 0}, L)],
                          C > 0] || M <- Mods]),
    erlang:trace(all, false, [call]), ab_time_tracer ! stop,
    [erlang:trace_pattern({M, '_', '_'}, false, [local, call_time]) || M <- Mods],
    Total = lists:sum([U || {U, _, _, _, _} <- Rows]),
    file:write_file(Path, [io_lib:format("total_us_per_req ~.1f~n", [Total / Div]) |
      [io_lib:format("~.1f us ~.1f calls ~p:~p/~p~n", [Us / Div, C / Div, M, F, A]) || {Us, C, M, F, A} <- lists:reverse(lists:sort(Rows))]]).
