-module(stacks).
-export([start/0]).
start() ->
    Out = os:getenv("PROBE_OUT"),
    spawn(fun() -> process_flag(priority, high), loop(Out, 0, #{}, 0) end),
    ok.
loop(Out, N, Acc, S) ->
    timer:sleep(1),
    Self = self(),
    {Acc2, S2} = lists:foldl(fun(P, {A, Sc}) when P =/= Self ->
        case erlang:process_info(P, [status, current_stacktrace]) of
            [{status, St}, {current_stacktrace, Stack}] when St =:= running; St =:= runnable ->
                Fs = [norm(M, F, Ar) || {M, F, Ar, _} <- Stack],
                Key = dedup(Fs),
                {maps:update_with(Key, fun(X) -> X + 1 end, 1, A), Sc + 1};
            _ -> {A, Sc}
        end;
        (_, Acc0) -> Acc0 end, {Acc, S}, erlang:processes()),
    case N rem 50 of
        0 -> file:write_file(Out ++ ".tmp", io_lib:format("~p.~n", [#{samples => S2, stacks => maps:to_list(Acc2)}])), file:rename(Out ++ ".tmp", Out);
        _ -> ok end,
    loop(Out, N + 1, Acc2, S2).
dedup([A, A | T]) -> dedup([A | T]);
dedup([A | T]) -> [A | dedup(T)];
dedup([]) -> [].
norm(M, F, _A) ->
    FS = atom_to_list(F),
    Name = case FS of
        [$- | Rest] -> case string:split(Rest, "/") of [Base, _] -> Base; _ -> FS end;
        _ -> FS end,
    ML = case atom_to_list(M) of "Elixir.BeamLisp." ++ R -> R; Other -> Other end,
    ML ++ ":" ++ Name.
