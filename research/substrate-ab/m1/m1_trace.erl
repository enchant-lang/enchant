-module(m1_trace).
-export([start/2, stop/1]).
%% M1: which namespaces a command loads, restores from the AOT cache or
%% compiles, and how long each took. Traces the {M, F, Arity, ArgIndex} given (local calls
%% included) with return_trace across all processes. Every completed call is
%% recorded as {Window, M:F/A, FirstArg, Microseconds, ResultTag}; the window
%% is the content of the label file the driver writes before each timed
%% command. Stop writes one line per call, grouped by window.
start(MFAs, LabelFile) ->
    case whereis(m1_tracer) of undefined -> ok; Old -> exit(Old, kill) end,
    Tracer = spawn(fun() -> collect(LabelFile, #{}, []) end),
    register(m1_tracer, Tracer),
    erlang:trace(all, true, [call, timestamp, {tracer, Tracer}]),
    persistent_term:put(m1_trace_mfas, [{M, F, A} || {M, F, A, _} <- MFAs]),
    persistent_term:put(m1_trace_args, maps:from_list([{{M, F, A}, I} || {M, F, A, I} <- MFAs])),
    [erlang:trace_pattern({M, F, A}, [{'_', [], [{exception_trace}]}], [local]) || {M, F, A, _} <- MFAs],
    ok.
label(File) ->
    case file:read_file(File) of {ok, B} -> string:trim(B); _ -> <<"none">> end.
arg(MFA, Args) ->
    I = maps:get(MFA, persistent_term:get(m1_trace_args), 0),
    if I >= 1, I =< length(Args) -> show(lists:nth(I, Args)); true -> <<"-">> end.
show(A) when is_binary(A), byte_size(A) =< 200 -> A;
show(A) when is_binary(A) -> <<"<binary>">>;
show(A) when is_atom(A) -> atom_to_binary(A);
show(A) when is_list(A) -> try iolist_to_binary(A) catch _:_ -> <<"?">> end;
show(A) -> iolist_to_binary(io_lib:format("~0P", [A, 6])).
tag(R) when is_atom(R) -> R;
tag(R) when is_tuple(R), tuple_size(R) > 0, is_atom(element(1, R)) -> element(1, R);
tag(_) -> value.
collect(F, Open, Done) ->
    receive
        {trace_ts, P, call, {M, Fn, A}, TS} ->
            K = {P, M, Fn, length(A)},
            E = {TS, arg({M, Fn, length(A)}, A), label(F)},
            collect(F, maps:update_with(K, fun(L) -> [E | L] end, [E], Open), Done);
        {trace_ts, P, return_from, {M, Fn, Ar}, R, TS} ->
            K = {P, M, Fn, Ar},
            case maps:get(K, Open, []) of
                [{T0, Arg, W} | Rest] ->
                    collect(F, Open#{K => Rest}, [{W, {M, Fn, Ar}, Arg, timer:now_diff(TS, T0), tag(R)} | Done]);
                [] -> collect(F, Open, Done)
            end;
        {trace_ts, P, exception_from, {M, Fn, Ar}, _, TS} ->
            K = {P, M, Fn, Ar},
            case maps:get(K, Open, []) of
                [{T0, Arg, W} | Rest] ->
                    collect(F, Open#{K => Rest}, [{W, {M, Fn, Ar}, Arg, timer:now_diff(TS, T0), exception} | Done]);
                [] -> collect(F, Open, Done)
            end;
        {stop, From} -> From ! {done, lists:reverse(Done)};
        _ -> collect(F, Open, Done)
    end.
stop(Path) ->
    erlang:trace(all, false, [call]),
    [erlang:trace_pattern(MFA, false, [local]) || MFA <- persistent_term:get(m1_trace_mfas, [])],
    m1_tracer ! {stop, self()},
    Rows = receive {done, R} -> R after 10000 -> [] end,
    file:write_file(Path, [io_lib:format("~s\t~p:~p/~p\t~s\t~p\t~p~n", [W, M, Fn, Ar, Arg, Us, Tag])
                           || {W, {M, Fn, Ar}, Arg, Us, Tag} <- Rows]),
    length(Rows).
