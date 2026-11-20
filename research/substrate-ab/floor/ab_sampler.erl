-module(ab_sampler).
-export([start/0, stop/1]).
%% Samples current stacks of running/runnable processes every millisecond.
start() ->
    P = spawn(fun() -> T = ets:new(ab_samples, [bag, public]), loop(T, 0) end),
    register(ab_sampler, P), ok.
loop(T, N) ->
    receive {stop, From} -> From ! {samples, ets:tab2list(T), N}
    after 1 ->
        Me = self(),
        [case erlang:process_info(P, [status, current_stacktrace]) of
             [{status, S}, {current_stacktrace, St}] when S =:= running; S =:= runnable ->
                 ets:insert(T, {s, lists:sublist(St, 14)});
             _ -> ok
         end || P <- erlang:processes(), P =/= Me],
        loop(T, N + 1)
    end.
fmt({M, F, A, _}) -> io_lib:format("~p:~p/~p", [M, F, if is_list(A) -> length(A); true -> A end]).
stop(Path) ->
    ab_sampler ! {stop, self()},
    receive {samples, Rows, N} ->
        Stacks = [St || {s, St} <- Rows],
        Count = fun(Keys) -> lists:foldl(fun(K, D) -> maps:update_with(K, fun(V) -> V + 1 end, 1, D) end, #{}, Keys) end,
        Self = Count([lists:flatten(fmt(hd(St))) || St <- Stacks, St =/= []]),
        Incl = Count(lists:append([lists:usort([lists:flatten(fmt(Fr)) || Fr <- St]) || St <- Stacks])),
        Top = fun(D) -> lists:sublist(lists:reverse(lists:keysort(2, maps:to_list(D))), 60) end,
        Out = [io_lib:format("samples ~p ticks ~p~n== self~n", [length(Stacks), N]),
               [io_lib:format("~p ~s~n", [V, K]) || {K, V} <- Top(Self)], "== inclusive\n",
               [io_lib:format("~p ~s~n", [V, K]) || {K, V} <- Top(Incl)]],
        file:write_file(Path, Out), length(Stacks)
    end.
