-module(u9_sampler).
-export([start/0, stop/1]).
%% Samples the current stack of every running/runnable process every 1 ms.
start() ->
    P = spawn(fun() -> T = ets:new(u9_samples, [bag, public]), loop(T, 0) end),
    register(u9_sampler, P), ok.
loop(T, N) ->
    receive {stop, From} -> From ! {samples, ets:tab2list(T), N}
    after 1 ->
        Me = self(),
        [case erlang:process_info(P, [status, current_stacktrace, registered_name]) of
             [{status, S}, {current_stacktrace, St}, {registered_name, RN}] when S =:= running; S =:= runnable ->
                 ets:insert(T, {s, RN, P, lists:sublist(St, 12)});
             _ -> ok
         end || P <- erlang:processes(), P =/= Me],
        loop(T, N + 1)
    end.
fmt({M, F, A, _}) -> io_lib:format("~p:~p/~p", [M, F, if is_list(A) -> length(A); true -> A end]).
stop(Path) ->
    u9_sampler ! {stop, self()},
    receive {samples, Rows, N} ->
        Samples = [{RN, P, St} || {s, RN, P, St} <- Rows],
        Stacks = [St || {_, _, St} <- Samples],
        ProcCount = fun(KeyFun) -> lists:foldl(fun(S, D) -> K = KeyFun(S), maps:update_with(K, fun(V) -> V + 1 end, 1, D) end, #{}, Samples) end,
        TopP = lists:sublist(lists:reverse(lists:keysort(2, maps:to_list(ProcCount(fun({RN,_,_}) -> RN end)))), 25),
        Self = lists:foldl(fun(St, D) -> lists:foldl(fun(Fr, E) -> K = lists:flatten(fmt(Fr)), maps:update_with(K, fun(V) -> V + 1 end, 1, E) end, D, [hd(St) || St =/= []]) end, #{}, Stacks),
        Incl = lists:foldl(fun(St, D) -> lists:foldl(fun(K, E) -> maps:update_with(K, fun(V) -> V + 1 end, 1, E) end, D, lists:usort([lists:flatten(fmt(Fr)) || Fr <- St])) end, #{}, Stacks),
        Top = fun(D) -> lists:sublist(lists:reverse(lists:keysort(2, maps:to_list(D))), 40) end,
        Out = [io_lib:format("samples ~p ticks ~p~n== processes~n", [length(Samples), N]),
               [io_lib:format("~p ~p~n", [V, K]) || {K, V} <- TopP], "== self\n",
               [io_lib:format("~p ~s~n", [V, K]) || {K, V} <- Top(Self)], "== inclusive\n",
               [io_lib:format("~p ~s~n", [V, K]) || {K, V} <- Top(Incl)]],
        file:write_file(Path, Out), length(Samples)
    end.
