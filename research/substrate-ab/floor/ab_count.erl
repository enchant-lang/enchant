-module(ab_count).
-export([start/1, stop/2]).
%% Exact call counts (call_count) for every function of the given modules.
start(Mods) ->
    [erlang:trace_pattern({M, '_', '_'}, true, [local, call_count]) || M <- Mods],
    persistent_term:put(ab_count_mods, Mods), ok.
stop(Path, Div) ->
    Mods = persistent_term:get(ab_count_mods),
    Rows = lists:append([[{C, M, F, A} || {F, A} <- M:module_info(functions),
                          {call_count, C} <- [erlang:trace_info({M, F, A}, call_count)],
                          is_integer(C), C > 0] || M <- Mods]),
    [erlang:trace_pattern({M, '_', '_'}, false, [local, call_count]) || M <- Mods],
    file:write_file(Path, [io_lib:format("~.2f ~p:~p/~p~n", [C / Div, M, F, A]) || {C, M, F, A} <- lists:reverse(lists:sort(Rows))]).
