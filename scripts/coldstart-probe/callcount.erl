-module(callcount).
-export([start/0]).
%% Call-count probe: counts calls to every function of every Elixir.BeamLisp.* module.
start() ->
    erlang:trace_pattern(on_load, true, [local, call_count]),
    Out = os:getenv("PROBE_OUT"),
    spawn(fun() -> loop(Out, #{}) end),
    ok.
loop(Out, Seen) ->
    Mods = [M || {M,_} <- code:all_loaded(), is_bl(M)],
    Seen2 = lists:foldl(fun(M, S) ->
        case maps:is_key(M, S) of true -> S;
          false -> erlang:trace_pattern({M,'_','_'}, true, [local, call_count]), S#{M => true} end end, Seen, Mods),
    dump(Out, Mods),
    timer:sleep(25),
    loop(Out, Seen2).
is_bl(M) -> lists:prefix("Elixir.BeamLisp", atom_to_list(M)).
dump(Out, Mods) ->
    Rows = lists:append([ [ {N, M, F, A} || {F,A} <- M:module_info(functions),
                              (N = case erlang:trace_info({M,F,A}, call_count) of {call_count, C} when is_integer(C), C > 0 -> C; _ -> 0 end) > 0 ] || M <- Mods ]),
    S = lists:sort(fun(A,B) -> A >= B end, Rows),
    file:write_file(Out ++ ".tmp", io_lib:format("~p.~n", [S])),
    file:rename(Out ++ ".tmp", Out).
