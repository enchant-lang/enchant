-module(sampler).
-export([start/0]).
start() ->
    Out = os:getenv("PROBE_OUT"),
    Ms = case os:getenv("PROBE_MS") of false -> 2; S -> list_to_integer(S) end,
    spawn(fun() -> process_flag(priority, high), loop(Out, Ms, 0, #{}, #{}, #{}, 0, erlang:monotonic_time(millisecond)) end),
    ok.
loop(Out, Ms, N, Own, Incl, Attr, Samples, T0) ->
    timer:sleep(Ms),
    Self = self(),
    {Own2, Incl2, Attr2, S2} = lists:foldl(fun(P, {O, I, At, S}) when P =/= Self ->
        case erlang:process_info(P, [status, current_stacktrace]) of
            [{status, St}, {current_stacktrace, Stack}] when St =:= running; St =:= runnable ->
                Fs = [norm(M, F, A) || {M, F, A, _} <- Stack],
                Fs1 = lists:filter(fun(X) -> X =/= skip end, Fs),
                case Fs of
                    [] -> {O, I, At, S};
                    [Top | _] ->
                        O1 = maps:update_with(Top, fun(X) -> X + 1 end, 1, O),
                        I1 = lists:foldl(fun(X, Acc) -> maps:update_with(X, fun(Y) -> Y + 1 end, 1, Acc) end, I, lists:usort(Fs1)),
                        BL = [X || {Mod, _, _} = X <- Fs1, is_bl_mod(Mod)],
                        Key = {Top, lists:sublist(BL, 2)},
                        At1 = maps:update_with(Key, fun(Z) -> Z + 1 end, 1, At),
                        {O1, I1, At1, S + 1}
                end;
            _ -> {O, I, At, S}
        end;
        (_, Acc) -> Acc end, {Own, Incl, Attr, Samples}, erlang:processes()),
    case N rem 25 of
        0 -> Dump = #{own => lists:sort(fun({_, A}, {_, B}) -> A >= B end, maps:to_list(Own2)),
                      incl => lists:sort(fun({_, A}, {_, B}) -> A >= B end, maps:to_list(Incl2)),
                      attr => lists:sublist(lists:sort(fun({_, A}, {_, B}) -> A >= B end, maps:to_list(Attr2)), 400), samples => S2, ms => Ms, elapsed => erlang:monotonic_time(millisecond) - T0},
             file:write_file(Out ++ ".tmp", io_lib:format("~p.~n", [Dump])), file:rename(Out ++ ".tmp", Out);
        _ -> ok
    end,
    loop(Out, Ms, N + 1, Own2, Incl2, Attr2, S2, T0).
norm(M, F, A) ->
    FS = atom_to_list(F),
    Name = case FS of
        [$- | Rest] -> case string:split(Rest, "/") of [Base, _] -> Base; _ -> FS end;
        _ -> FS end,
    case atom_to_list(M) of
        "Elixir.BeamLisp." ++ R -> {R, Name, A};
        Other -> {Other, Name, A}
    end.
is_bl_mod(Mod) -> not lists:member(Mod, ["proc_lib","gen_server","gen","erlang","prim_file","file","file_server","code","code_server","crypto","beam_lib","beam_disasm","lists","maps","filelib","error_handler","Elixir.Enum","Elixir.Code","Elixir.Path.Wildcard","Elixir.File","Elixir.Map","Elixir.Kernel","erl_prim_loader"]).
