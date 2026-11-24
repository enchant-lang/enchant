-module(m1_sampler).
-export([start/1, stop/1]).
%% M1: samples the stack of every running/runnable process every 1 ms in the
%% warm VM. The window a sample belongs to is the content of a label file the
%% driver writes before each timed command (re-read every 10 ms), so marking
%% costs no extra request. At stop, each sample is put in the first bucket whose rule matches
%% any frame of its stack (rules below, most specific first), per window.
%% Derived from research/substrate-ab/floor/u9/u9_sampler.erl.
start(LabelFile) ->
    case whereis(m1_sampler) of undefined -> ok; Old -> exit(Old, kill) end,
    P = spawn(fun() -> T = ets:new(m1_samples, [bag, public]), loop(T, 0, LabelFile, <<"start">>) end),
    register(m1_sampler, P), ok.
label(File, Old) ->
    case file:read_file(File) of {ok, B} -> string:trim(B); _ -> Old end.
loop(T, N, F, W0) ->
    W = case N rem 10 of 0 -> label(F, W0); _ -> W0 end,
    receive
        {stop, From} -> From ! {samples, ets:tab2list(T), N}
    after 1 ->
        Me = self(),
        [case erlang:process_info(P, [status, current_stacktrace]) of
             [{status, S}, {current_stacktrace, St}] when S =:= running; S =:= runnable ->
                 ets:insert(T, {s, W, [frame(Fr) || Fr <- lists:sublist(St, 60)]});
             _ -> ok
         end || P <- erlang:processes(), P =/= Me],
        loop(T, N + 1, F, W)
    end.
frame({M, F, A, _}) -> {atom_to_binary(M), F, if is_list(A) -> length(A); true -> A end}.
%% Bucket rules: {Bucket, [module-name substrings]}. First rule with any
%% matching frame wins, so compile beats load beats run beats handler.
rules() ->
    [{compile, [<<"BeamLisp.Ns.Compiler">>, <<"BeamLisp.Ns.Body.Compiler">>, <<"BeamLisp.Compiler">>,
                <<"BeamLisp.AOT">>, <<"Lower">>, <<"Emit">>, <<"Macroexpand">>, <<"Expand">>,
                <<"compile">>, <<"v3_core">>, <<"beam_">>, <<"sys_core">>, <<"cerl">>, <<"BeamLisp.Reader">>]},
     {load, [<<"BeamLisp.Loader">>, <<"BeamLisp.Env">>, <<"code_server">>, <<"Dev.overlay">>, <<"Dev-overlay">>]},
     {test_or_run, [<<"Test">>, <<"test">>, <<"scene">>, <<"Scene">>, <<"m1">>]},
     {handler, [<<"Vm.">>, <<"Daemon">>, <<"Cli">>, <<"Realm">>, <<"Session">>]},
     {other, [<<>>]}].
matches(Stack, Subs) -> lists:any(fun({M, _, _}) -> lists:any(fun(S) -> S =:= <<>> orelse binary:match(M, S) =/= nomatch end, Subs) end, Stack).
bucket(Stack) -> hd([B || {B, Subs} <- rules(), matches(Stack, Subs)] ++ [other]).
fmt({M, F, A}) -> iolist_to_binary(io_lib:format("~s:~p/~p", [M, F, A])).
stop(Path) ->
    m1_sampler ! {stop, self()},
    receive {samples, Rows, N} ->
        Windows = lists:usort([W || {s, W, _} <- Rows]),
        Out = [begin
                   Stacks = [St || {s, W1, St} <- Rows, W1 =:= W],
                   Buckets = lists:foldl(fun(St, D) -> maps:update_with(bucket(St), fun(V) -> V + 1 end, 1, D) end, #{}, Stacks),
                   Self = count([[fmt(hd(St))] || St <- Stacks, St =/= []]),
                   Incl = count([lists:usort([fmt(Fr) || Fr <- St]) || St <- Stacks]),
                   [io_lib:format("== window ~s samples ~p~n", [W, length(Stacks)]),
                    [io_lib:format("bucket ~p ~p~n", [B, C]) || {B, C} <- lists:reverse(lists:keysort(2, maps:to_list(Buckets)))],
                    [io_lib:format("self ~p ~s~n", [C, K]) || {K, C} <- top(Self, 25)],
                    [io_lib:format("incl ~p ~s~n", [C, K]) || {K, C} <- top(Incl, 60)]]
               end || W <- Windows],
        file:write_file(Path, [io_lib:format("ticks ~p~n", [N]) | Out]),
        length(Rows)
    end.
count(Lists) -> lists:foldl(fun(Keys, D) -> lists:foldl(fun(K, E) -> maps:update_with(K, fun(V) -> V + 1 end, 1, E) end, D, Keys) end, #{}, Lists).
top(D, K) -> lists:sublist(lists:reverse(lists:keysort(2, maps:to_list(D))), K).
