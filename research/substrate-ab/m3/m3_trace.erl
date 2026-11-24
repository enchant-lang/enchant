-module(m3_trace).
-export([start/0]).
%% M3: a boot-time call timeline. Started with ERL_AFLAGS="-pa DIR -s m3_trace start"
%% and M3_TRACE_OUT=FILE. Every call of a traced function (all functions of the
%% modules below, local calls included) that lasts at least M3_TRACE_MIN_US
%% (default 20000) is appended to FILE as
%%   start_us_since_epoch \t dur_us \t pid \t depth \t M:F/A \t first-arg
%% Patterns are (re)applied every 5 ms for the first 120 s, since the modules
%% load lazily. Nothing happens without M3_TRACE_OUT.
-define(MODS, []).
-define(MFAS, [{'Elixir.BeamLisp.Loader', do_load, 3}, {'Elixir.BeamLisp.Loader', ensure_loaded, 1},
               {'Elixir.BeamLisp.AOT', 'compile_sdk_source!', 3},
               {'Elixir.BeamLisp.Compiler', eval_string, 3},
               {'Elixir.BeamLisp.Ns.Body.Vm.Session', start, 2},
               {'Elixir.BeamLisp.Ns.Body.Vm.Session', 'boot-realm-services!', 2},
               {'Elixir.BeamLisp.Ns.Body.Vm.Session', 'request-handler', 2},
               {'Elixir.BeamLisp.Ns.Body.Vm.Session', 'publish-self!', 3},
               {'Elixir.BeamLisp.Ns.Body.Vm.Net', listen, 3},
               {'Elixir.BeamLisp.Ns.Body.Vm.Net', 'serve-conn', 5},
               {'Elixir.BeamLisp.Ns.Body.Vm.Manager', start, 0},
               {'Elixir.BeamLisp.Ns.Body.Vm.Manager', run, 3},
               {'Elixir.BeamLisp.Ns.Body.Vm.Realm', open, 2},
               {'Elixir.BeamLisp.Ns.Body.Vm.Realm', 'start-services!', 1},
               {'Elixir.BeamLisp.Ns.Body.Bl.Daemon', 'handle-in-vm', 3},
               {'Elixir.BeamLisp.Ns.Body.Bl.Dev-overlay', 'sync!', 1},
               {'Elixir.BeamLisp.Ns.Body.Bl.Cli', 'run-argv', 1},
               {'Elixir.BeamLisp.Ns.Body.Bl.Test', run, 2},
               {'Elixir.BeamLisp.Ns.Body.Bl.Test', 'isolated-result', 2},
               {'Elixir.BeamLisp.Env', 'ensure_sdk_owner_registry!', 0},
               {'Elixir.BeamLisp.Env', 'retain_sdk_runtime!', 0},
               {'Elixir.BeamLisp.Env', 'refresh_sdk_runtime!', '_'},
               {'Elixir.BeamLisp.AOT', 'sdk_runtime_inventory_uncached!', 1},
               {'Elixir.BeamLisp.AOT', 'preload_sdk_image_closure!', 1},
               {'Elixir.BeamLisp.Ns.Body.Vm.Owner', start, 0},
               {global, random_sleep, 1}]).
start() ->
    case os:getenv("M3_TRACE_OUT") of
        false -> ok;
        Out ->
            Min = case os:getenv("M3_TRACE_MIN_US") of false -> 20000; V -> list_to_integer(V) end,
            T0 = os:system_time(microsecond),
            Tracer = spawn(fun() ->
                {ok, F} = file:open(Out, [append, raw, binary]),
                file:write(F, io_lib:format("~p\t0\t-\t0\tvm-start\t~s~n", [T0, os:getpid()])),
                collect(F, Min, #{})
            end),
            erlang:trace(all, true, [call, timestamp, {tracer, Tracer}]),
            spawn(fun() -> patch(#{}, 24000) end),
            case os:getenv("M3_SAMPLE") of
                false -> ok;
                _ -> spawn(fun() -> sample(Out ++ ".samples", T0, #{}, 2400) end)
            end,
            ok
    end.
patch(_, 0) -> ok;
patch(Done, N) ->
    Done1 = lists:foldl(fun(M, D) ->
        case maps:is_key(M, D) orelse not erlang:module_loaded(M) of
            true -> D;
            false -> erlang:trace_pattern({M, '_', '_'}, [{'_', [], [{exception_trace}]}], [local]), D#{M => 1}
        end end, Done, ?MODS),
    Done2 = lists:foldl(fun({M, F, A} = MFA, D) ->
        case maps:is_key(MFA, D) orelse not erlang:module_loaded(M) of
            true -> D;
            false -> erlang:trace_pattern({M, F, A}, [{'_', [], [{exception_trace}]}], [local]), D#{MFA => 1}
        end end, Done1, ?MFAS),
    receive after 5 -> patch(Done2, N - 1) end.
us({Mega, S, Micro}) -> (Mega * 1000000 + S) * 1000000 + Micro.
show(A) when is_binary(A), byte_size(A) =< 120 -> A;
show(A) when is_binary(A) -> binary:part(A, 0, 120);
show(A) when is_atom(A) -> atom_to_binary(A);
show(A) -> iolist_to_binary(io_lib:format("~0P", [A, 4])).
collect(F, Min, Open) ->
    receive
        {trace_ts, P, call, {M, Fn, A}, TS} ->
            K = {P, M, Fn, length(A)},
            Arg = case A of [X | _] -> X; _ -> '-' end,
            E = {us(TS), Arg},
            collect(F, Min, maps:update_with(K, fun(L) -> [E | L] end, [E], Open));
        {trace_ts, P, Kind, {M, Fn, Ar}, _R, TS} when Kind =:= return_from; Kind =:= exception_from ->
            K = {P, M, Fn, Ar},
            case maps:get(K, Open, []) of
                [{T0, Arg} | Rest] ->
                    D = us(TS) - T0,
                    case D >= Min of
                        true -> file:write(F, io_lib:format("~p\t~p\t~p\t~p\t~s:~s/~p~s\t~s~n",
                                    [T0, D, P, length(Rest), M, Fn, Ar,
                                     case Kind of exception_from -> " EXC"; _ -> "" end,
                                     string:replace(show(Arg), "\n", " ", all)]));
                        false -> ok
                    end,
                    collect(F, Min, Open#{K => Rest});
                [] -> collect(F, Min, Open)
            end;
        _ -> collect(F, Min, Open)
    end.

sample(Out, T0, Acc, 0) ->
    file:write_file(Out, [io_lib:format("~p\t~s\t~s\t~p~n", [B, L, M, N]) || {{B, L, M}, N} <- lists:sort(maps:to_list(Acc))]);
sample(Out, T0, Acc, K) ->
    Me = self(),
    B = (os:system_time(microsecond) - T0) div 250000,
    Acc1 = lists:foldl(fun(P, A) ->
        case P =/= Me andalso erlang:process_info(P, [status, current_function, registered_name, dictionary, initial_call]) of
            [{status, S}, {current_function, CF}, {registered_name, R}, {dictionary, D}, {initial_call, IC}] when S =:= running; S =:= runnable ->
                L = case R of [] -> case lists:keyfind('$initial_call', 1, D) of {_, {M0, F0, _}} -> io_lib:format("~s:~s", [M0, F0]); _ -> {M1, F1, _} = IC, io_lib:format("~s:~s", [M1, F1]) end; _ -> atom_to_list(R) end,
                Mod = case CF of {CM, CFn, CA} -> io_lib:format("~s:~s/~p", [CM, CFn, CA]); _ -> "?" end,
                maps:update_with({B, lists:flatten(L), lists:flatten(Mod)}, fun(N) -> N + 1 end, 1, A);
            _ -> A
        end end, Acc, erlang:processes()),
    case K rem 40 of 0 -> sample(Out, T0, Acc1, 0); _ -> ok end,
    receive after 5 -> sample(Out, T0, Acc1, K - 1) end.
