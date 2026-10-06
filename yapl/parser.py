# MIT License
#
# Copyright (c) 2025 AnonymousDapper

# pyright: reportImplicitOverride=false

from __future__ import annotations

__all__ = (
    "alpha",
    "and_",
    "apply",
    "between",
    "bind",
    "BytesParserInput",
    "choice",
    "crlf",
    "defer",
    "digit",
    "end_of_line",
    "eof",
    "Fail",
    "fail_with",
    "left",
    "lift2",
    "literal",
    "many",
    "many1",
    "map_",
    "newline",
    "none_of",
    "one_of",
    "opt",
    "or_",
    "Parser",
    "ParserError",
    "ParseResult",
    "ParserInput",
    "ParserValue",
    "pure",
    "regex",
    "regex_captures",
    "right",
    "sep_by",
    "sep_by1",
    "seq",
    "space",
    "spaces",
    "string_",
    "StringParserInput",
    "Succeed",
    "succeed_with",
    "times",
)

import inspect
import itertools
import re
import string as string_ops
from collections.abc import Iterable, Sequence
from typing import Any, Callable, TypeAlias, TypeVarTuple, Union, Unpack, cast

from .functional import (
    Err,
    F,
    Nested,
    Nothing,
    NothingType,
    Ok,
    Option,
    Result,
    Some,
    compose,
    cons,
    curry2,
    first,
    flatten,
    is_err,
    is_ok,
    is_some,
    partial,
    reduce,
    second,
)
from .utils.logging import Color, get_logger

logger = get_logger()

_DEPTH = 0
_COUNT = iter(itertools.count())

type ParseResult[S, T] = Result[ParserValue[S, T], ParserError[S]]

type InputStream[T] = Sequence[T]

# Position container
# ------------------


class LineCol:
    __slots__ = ("line", "column")
    line: int
    column: int

    def next_column(self):
        self.column += 1

    def next_line(self):
        self.line += 1
        self.column = 1

    def __init__(self, line: int, column: int):
        self.line = line
        self.column = column

    def __repr__(self):
        return f"<LineCol({self.line}, {self.column})>"


class ParserPosition[S]:
    __slots__ = ("current_item", "offset")
    current_item: Option[S]
    offset: int

    def __init__(self, current_item: Option[S], offset: int):
        self.current_item = current_item
        self.offset = offset

    def __repr__(self):
        return f"<ParserPosition({self.offset})>"


class StringParserPosition(ParserPosition[str]):
    __slots__ = ("current_item", "offset", "pos")
    current_item: Option[str]
    offset: int
    pos: LineCol

    def __init__(self, current_item: Option[str], offset: int, pos: LineCol):
        super().__init__(current_item, offset)
        self.pos = pos

    def __repr__(self):
        return (
            f"<StringParserPosition({self.offset}, L{self.pos.line}:{self.pos.column})"
        )


# Input stream handler
# --------------------


class ParserInput[S]:
    __slots__ = ("source", "source_len", "index")
    source: InputStream[S]
    source_len: int
    index: int

    def __init__(self, source: InputStream[S]):
        self.source = source
        self.source_len = len(source)
        self.index = 0

    def get_position(self):
        return ParserPosition(
            self.index > 0 and Some(self.source[self.index]) or Nothing, self.index
        )

    def peek(self) -> Option[S]:
        if self.index < self.source_len:
            return Some(self.source[self.index])

        return Nothing

    def next(self) -> Option[S]:
        char = self.peek()

        if is_some(char):
            self.index += 1

        return char

    def mark(self):
        """Mark the parser's current position and return a closure to restore it"""
        # logger.log(f"{self.index}")
        temp = self.index

        def restore():
            self.index = temp

        return restore

    def consume(self, amount: int):
        # logger.log(amount)

        for _k in range(amount):
            _ = self.next()

    def get_view(self, length: int = 0) -> InputStream[S]:
        # view the rest of the input stream by default
        # and prevent negative indexing
        end = length and self.index + max(0, length) or self.source_len

        # logger.log("view", length, f"{self.index}:{end}")
        return self.source[self.index : end]


class StringParserInput(ParserInput[str]):
    __slots__ = ("source", "source_len", "index", "pos")
    source: InputStream[str]
    source_len: int
    index: int
    pos: LineCol

    def __init__(self, source: InputStream[str]):
        super().__init__(source)
        self.pos = LineCol(1, 1)

    def get_position(self):
        # type mismatch: InputStream does not implement .split

        # fmt: off
        return StringParserPosition(
            Some(self.source.split("\n")[ # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType, reportUnknownArgumentType]
                self.pos.line - 1
            ]),
            self.index,
            self.pos,
        )
        # fmt: off

    def next(self) -> Option[str]:
        if self.index < self.source_len:
            val = self.source[self.index]

            self.index += 1

            if val == "\n":  # adjust line position for newlines
                self.pos.next_line()
            else:
                self.pos.next_column()
            return Some(val)

        return Nothing

    def mark(self):
        """Mark the parser's current position and return a closure to restore it"""
        # logger.log(f"[string] {self.index} {self.pos}")
        temp = self.index, self.pos

        def restore():
            # logger.log(f"[string] {self.index} {self.pos} to {temp[0]} {temp[1]}")
            self.index, self.pos = temp

        return restore

    def get_string_view(self, length: int = 0) -> str:
        end = length and self.index + max(0, length) or self.source_len

        # logger.log("str view", length, f"{self.index}:{end}")
        obj = cast(object, self.source[self.index : end])

        return cast(str, obj)


class BytesParserInput(ParserInput[bytes]):
    __slots__ = ("source", "source_len", "index")
    source: InputStream[bytes]
    source_len: int
    index: int

    def __init__(self, source: InputStream[bytes]):
        super().__init__(source)

    def get_bytes_view(self, length: int = 0) -> bytes:
        end = length and self.index + max(0, length) or self.source_len

        # logger.log("str view", length, f"{self.index}:{end}")
        obj = cast(object, self.source[self.index : end])

        return cast(bytes, obj)


# Error and Value handlers
# ------------------------


class ParserError[S]:
    __slots__ = ("label", "msg", "position", "consumed")
    label: str
    msg: str
    position: ParserPosition[S]
    consumed: bool

    def __init__(
        self, label: str, msg: str, position: ParserPosition[S], consumed: bool = False
    ):
        self.label = label
        self.msg = msg
        self.position = position
        self.consumed = consumed

    def with_msg(self, msg: str):
        self.msg = msg
        return self

    def set_consumed(self, c: bool):
        self.consumed = c

    def print_err(self):
        pos = self.position
        if isinstance(pos, StringParserPosition):
            linecol = pos.pos
            print(
                f"Error at parser {self.label}, Line {linecol.line} Column {linecol.column}:\n\t| {pos.current_item.unwrap_or('')}\n\t  {'^':>{linecol.column}} {self.msg}"  # pyright: ignore[reportArgumentType]
            )

        else:
            print(
                f"Error at parser {self.label}, token #{pos.offset+1} {pos.current_item!r} : {self.msg}"
            )

    def __repr__(self):
        return f"<ParserError([{self.consumed and '+' or '-'}] {self.label} @ {self.position!r})>"


class ParserValue[S, T]:
    __slots__ = ("item", "remains", "consumed")
    item: T
    remains: ParserInput[S]
    consumed: bool

    def __init__(self, item: T, input_: ParserInput[S], consumed: bool = True):
        self.item = item
        self.remains = input_
        self.consumed = consumed

    def set_consumed(self, c: bool):
        self.consumed = c

    def __repr__(self):
        return f"<ParserValue([{self.consumed and '+' or '-'}]: {self.item!r})>"


# Parser Base
# -----------


class Parser[S, T]:
    __slots__ = ("fn", "label")

    type ParserFn = F[ParserInput[S], ParseResult[S, T]]

    fn: ParserFn
    label: Option[str]

    def __init__(self, fn: ParserFn, label: str | None = None):
        self.fn = fn
        self.label = label and Some(label) or Nothing

    def named(self, label: str):
        self.label = Some(label)
        return self

    def get_label(self) -> str:
        return self.label.unwrap_or(
            "??"  # pyright: ignore[reportReturnType, reportArgumentType]
        )

    def run(self, i: ParserInput[S]):
        global _DEPTH
        next(_COUNT)
        _log_context_ = "Parser<run>"
        _log_color_ = Color.AltRed
        restore = i.mark()

        logger.log(f"{' '*_DEPTH}\\({_DEPTH}) Label: {self.get_label()}")
        logger.log(f"{' '*_DEPTH}\\({_DEPTH})        {i.get_view()!r}")
        _DEPTH += 1

        result = self.fn(i)

        _DEPTH -= 1
        logger.log(f"{' '*_DEPTH}/({_DEPTH}) Result: {result!r}")

        # fmt: off
        # automatic backtracking for non-consuming parsers
        if result.is_ok_and(
            lambda v: not v.consumed  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
        ) or result.is_err_and(
            lambda e: not e.consumed  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
        ):
            restore()

        # fmt: on

        return result

    def with_[a](self, other: F[T, a]):
        """`self.with_(other)`

        Equivalent to `map_(other, self)`"""
        return map_(other, self)

    def as_[a](self, v: a) -> Parser[S, a]:
        """`self.as_(v)`

        Equivalent to `map_(() -> v, self)`"""
        return map_(lambda _: v, self)

    def expect[a](self, other: Parser[S, a]):
        """`expect` sequentially composes `other` to self
        and returns a new parser.
        This parser returns an error value if `other` fails,
        but does not consume the input stream for that run.

        This can be used to implement short-circuiting for
        complex parser chains."""

        def inner(xs: ParserInput[S]) -> ParseResult[S, T]:
            match self.run(xs):
                case Ok(v):
                    restore = xs.mark()
                    expected = other.run(xs)
                    restore()
                    if is_err(expected):
                        return Fail(
                            other.get_label(), f"expected {other.get_label()!r}", xs
                        )

                    else:
                        return Ok(v)
                case Err(e):
                    return Err(e)

        return Parser(inner, f"EXPECT {other.get_label()}")

    def filter[V](self: Parser[S, list[V]], f: F[V, bool]):
        """`filter` applies a filter predicate `f` to
        a parser producing a list of values.

        This method is only available on types
        `Parser[list[V]]`."""

        def inner(v: Iterable[V]):
            return list(filter(f, v))

        return map_(inner, self)

    def filter_option[V](self: Parser[S, list[Option[V]]]) -> Parser[S, list[V]]:
        """`filter_option` accepts a list of `Option[V]` types
        and returns a new list consisting of only the `Some` values.

        This method is only available on types
        `Parser[list[Option[V]]]`."""

        def inner(v: Iterable[Option[V]]) -> list[V]:
            return list(x.unwrap() for x in v if is_some(x))

        return map_(inner, self)

    def flatten[V](self: Parser[S, tuple[V] | V]):
        return map_(lambda t: list(flatten([t])), self)

    def __le__[a](self, f: F[T, Parser[S, a]]):
        """`self <= f`

        Equivalent to `bind(f, self)`"""
        return bind(f, self)

    def __matmul__[
        C, V
    ](self: Parser[S, tuple[Any, ...]], ctor: type[C]) -> Parser[S, C]:
        """`self @ ctor`

        Equivalent to `map_(v -> ctor(*v), self)`"""
        return map_(lambda v: ctor(*flatten(v)), self)

    def __rmul__[a](self, other: Parser[S, F[T, a]]):
        """`self * other`

        Equivalent to `apply(other, self)`"""
        return apply(other, self)

    def __and__[a](self, other: Parser[S, a]):
        """`self & other`

        Equivalent to `and_(self, other)`"""
        return and_(self, other)

    def __or__[a](self, other: Parser[S, a]):
        """`self | other`

        Equivalent to `or_(self, other)`"""
        return or_(self, other)

    def __lshift__[a](self, other: Parser[S, a]):
        """`self << other`

        Equivalent to `left(self, other)`"""
        return left(self, other)

    def __rshift__[a](self, other: Parser[S, a]):
        """`self >> other`

        Equivalent to `right(self, other)`"""
        return right(self, other)

    def __truediv__[a](self, other: Parser[S, a]):
        """`self / other`

        Equivalent to `sep_by(self, other)`"""

        return sep_by(self, other)

    def __floordiv__[a](self, other: Parser[S, a]):
        """`self // other`

        Equivalent to `sep_by1(self, other)`"""

        return sep_by1(self, other)

    def __getitem__(self, i: int | slice[int | None]):
        """`self[l : h]`

        Equivalent to `times(self, l, h)`"""

        if isinstance(i, slice):
            low, high = i.start or 0, i.stop
        else:
            low = high = i

        return times(self, low, high)

    def __invert__(self):
        """`~ self`

        Equivalent to `opt(self)`
        """
        return opt(self)

    def __pos__(self):
        """`+ self`

        Equivalent to `many(self)`
        """
        return many(self)


# Value Helpers
# -------------


def Succeed[
    S, T
](v: T, xs: ParserInput[S], *, consumed: bool = True) -> ParseResult[S, T]:
    return Ok(ParserValue(v, xs, consumed))


def Fail[
    S, T
](label: str, msg: str, xs: ParserInput[S], *, consumed: bool = False) -> ParseResult[
    S, T
]:
    return Err(ParserError(label, msg, xs.get_position(), consumed))


# ===========
# Combinators
# ===========


def defer[S, a](f: F[Parser[S, a]]):
    """Given a `()->Parser[a]`,
    `defer` will evaluate this function lazily and
    enable recursive parsers.
    """

    def inner(xs: ParserInput[S]):
        return f().run(xs)

    return Parser(inner)


def satisfy[S](f: F[S, bool], label: str) -> Parser[S, S]:
    """Given a function `S->bool`,
    `satisfy` produces a `Parser[S]`.

    `satisfy` takes one item from the input stream,
    applies it to to `f`, and returns that item if
    `f` returns `True`.
    """

    def inner(xs: ParserInput[S]) -> ParseResult[S, S]:
        match xs.peek():
            case Some(v):
                if f(v):
                    _ = xs.next()
                    return Succeed(v, xs)
                else:
                    return Fail(label, f"Unexpected {v!r}", xs)

            case _:
                return Fail(label, f"end of input, expected {label}", xs)

    return Parser(inner, label)


def bind[S, a, b](f: F[a, Parser[S, b]], p: Parser[S, a]):
    """Given a `Parser[a]` and a function `a->Parser[b]`,
    `bind` produces a `Parser[b]`.
    This is also referred to as a monadic bind.

    `p <= f`
    """

    def inner(xs: ParserInput[S]) -> ParseResult[S, b]:
        match p.run(xs):
            case Err(e):
                return Err(e)
            case Ok(v):
                try:
                    p2 = f(v.item)
                except Exception as e:
                    return Fail(
                        f"<bind_inner {f.__name__}: `{inspect.getsource(f).strip()}`>",
                        f"bind call failed: {e}",
                        xs,
                    )

                else:
                    return p2.run(v.remains)

    return Parser(inner, f"[BIND {f.__qualname__} {p.get_label()}]")


def pure[S, a](x: a) -> Parser[S, a]:
    """`pure` lifts a standalone value `a`
    into a `Parser[a]`.
    """

    def inner(xs: ParserInput[S]) -> ParseResult[S, a]:
        return Succeed(x, xs)

    return Parser(inner, f"just {repr(x)}")


def map_[S, a, b](f: F[a, b], p: Parser[S, a]) -> Parser[S, b]:
    """Given a function `a->b` and a `Parser[a]`m
    `map` produces a `Parser[b]`.
    """
    return bind(compose(f, pure), p)


def apply[S, a, b](fp: Parser[S, F[a, b]], ap: Parser[S, a]) -> Parser[S, b]:
    """Given a `Parser[a->b]` and a `Parser[a]`,
    `apply` produces a `Parser[a]`.

    """
    return bind(lambda f: bind(lambda a: pure(f(a)), ap), fp)

    # fp <= (lambda f: ap <= (lambda a: pure(f(a))))


def lift2[S, a, b, c](f: F[a, b, c], ap: Parser[S, a], bp: Parser[S, b]):
    """Given a function `(a, b)->c` and a `Parser[a]`,
    `lift2` produces a `Parser[b]`.
    """
    return apply(apply(pure(curry2(f)), ap), bp)


def and_[S, a, b](p1: Parser[S, a], p2: Parser[S, b]) -> Parser[S, tuple[a, b]]:
    """Given a `Parser[a]` and a `Parser[b]`,
    `and_` produces a `Parser[a, b]`.

    `p1 & p2`
    """
    return bind(lambda p1r: bind(lambda p2r: pure((p1r, p2r)), p2), p1).named(
        f"{p1.get_label()} AND {p2.get_label()}"
    )

    # p1 <= (lambda p1r: p2 <= (lambda p2r: pure((p1r, pr2)))


def or_[S, a, b](p1: Parser[S, a], p2: Parser[S, b]) -> Parser[S, a | b]:
    """Given a `Parser[a]` and a `Parser[b]`,
    `or_` produces a `Parser[a | b]`.

    `p1 | p2`
    """

    def inner(xs: ParserInput[S]) -> ParseResult[S, a | b]:
        r1 = p1.run(xs)

        match r1:
            case Ok(v):
                return Ok(cast(ParserValue[S, a | b], v))

            case Err(_):
                r2 = p2.run(xs)
                return cast(ParseResult[S, a | b], r2)

    return Parser(inner, f"[{p1.get_label()} OR {p2.get_label()}]")


def opt[S, a](p: Parser[S, a], default: Option[a] = Nothing) -> Parser[S, Option[a]]:
    """Given a `Parser[a]` and optional default value `Option[a]`,
    `opt` attempts to match the parser, returning the default on failure.

    `~p`
    """

    some = p.with_(Some)

    return (or_(some, pure(default))).named(f"[OPT {p.get_label()}]")


def choice[S, a](*parsers: Parser[S, a]) -> Parser[S, a]:
    """Given a series of `Parser[a]`,
    `choice` produces a `Parser[a]`.

    This can be used to select any one parser from a given list.
    """
    return reduce(or_, parsers)


def seq[S, a](parsers: list[Parser[S, a]]) -> Parser[S, list[a]]:
    """Given a list of `Parser[a]`,
    `seq` produces a `Parser[list[a]]`.
    """
    match parsers:
        case [h, *t]:
            return lift2(cons, h, seq(t))
        case _:
            return pure([])


def left[S, a, b](p1: Parser[S, a], p2: Parser[S, b]):
    """Given a `Parser[a]` and a `Parser[b]`,
    `left` produces a `Parser[a]`.

    In other words, `left` takes two parsers, composes them sequentially,
    and discards the second result.

    `p1 << p2`
    """
    return (p1 & p2).with_(first).named("left")


def right[S, a, b](p1: Parser[S, a], p2: Parser[S, b]):
    """Given a `Parser[a]` and a `Parser[b]`,
    `right` produces a `Parser[b]`.

    In other words, `right` takes two parsers, composes them sequentially,
    and discards the first result.

    `p1 >> p2`
    """
    return (p1 & p2).with_(second).named("right")


def between[
    S, a, b, c
](p1: Parser[S, a], p2: Parser[S, b], p3: Parser[S, c]) -> Parser[S, b]:
    """Given a `Parser[a]`, a `Parser[b]`, and a `Parser[c]`,
    `between` produces a `Parser[b]`.

    In other words, `between` takes three parsers, attempts them sequentially,
    and returns only the middle result if all three succeed.
    """
    return p1 >> p2 << p3


def times[S, T](p: Parser[S, T], _min: int, _max: int | None = None):
    """Given a `Parser[T]`, and `min` / `max` integers,
    `times` attempts to apply this parser between `min` and `max` times.

    The upper limit is unbounded when `max` is None."""

    def inner(xs: ParserInput[S]) -> ParseResult[S, list[T]]:
        acc: list[T] = []

        for _ in range(_min):
            res1 = p.run(xs)
            if is_ok(res1):
                acc.append(res1.unwrap().item)
            else:
                # restore()
                return Fail(
                    p.get_label(),
                    f"parser failed calling times (min): {res1.unwrap_err()}",
                    xs,
                )

        # upper limit of the loop is unbounded if _max is None
        for _ in range(_max - _min) if _max is not None else itertools.count():
            res2 = p.run(xs)
            if is_ok(res2):
                acc.append(res2.unwrap().item)
            else:
                if res2.unwrap_err().consumed:
                    return Fail(
                        p.get_label(),
                        f"parser failed calling times (max): {res2.unwrap_err()}",
                        xs,
                        consumed=True,
                    )
                break

        return Succeed(acc, xs)

    return Parser(inner, f"[TIMES<{_min}:{_max}> {p.get_label()}]")


def many[S, T](p: Parser[S, T]):
    """Given a `Parser[T]`,
    `many` applies this parser as many times as possible,
    with a minimum of *zero*."""
    return times(p, 0, None)


def many1[S, T](p: Parser[S, T]):
    """Given a `Parser[T]`,
    `many` applies this parser as many times as possible,
    with a minimum of *one*."""
    return times(p, 1, None)


def sep_by[S, a, b](p: Parser[S, a], sep: Parser[S, b]) -> Parser[S, list[a]]:
    """Given a `Parser[a]` and `Parser[b]`,
    `sep_by` consumes as many occurences of `a` followed by `b` as possible,
    with a minimum of *zero*.

    Will always match an initial occurrence of `a`."""
    return (p & many(sep >> p)).with_(lambda pair: cons(*pair))


def sep_by1[S, a, b](p: Parser[S, a], sep: Parser[S, b]) -> Parser[S, list[a]]:
    """Given a `Parser[a]` and `Parser[b]`,
    `sep_by` consumes as many occurences of `a` followed by `b` as possible,
    with a minimum of *one*.

    Will always match an initial occurrence of `a`."""
    return (p & many1(sep >> p)).with_(lambda pair: cons(*pair))


# ==================
# Item-based Parsers
# ==================


def literal[S](v: S, label: str | None = None) -> Parser[S, S]:
    """`literal` accepts one item from the input if it matches `v`."""
    return satisfy(lambda x: x == v, label or repr(v))


def one_of[S](*vs: S) -> Parser[S, S]:
    """`one_of` accepts one item from the input if it
    is present in the set `vs`."""
    return satisfy(lambda x: x in vs, f"[ONE OF {vs!r}]")


def none_of[S](*vs: S) -> Parser[S, S]:
    """`none_of` accepts one item from the input if it
    is not present in the set `vs`."""
    return satisfy(lambda x: x not in vs, f"[NONE OF {vs!r}]")


def eof[S]() -> Parser[S, None]:
    """`eof` returns a empty `ParserValue` if the input is empty,
    and a `ParserError` if not."""

    def inner(xs: ParserInput[S]) -> ParseResult[S, None]:
        match xs.peek():
            case Some(v):
                return Fail("eof", "expected end of input", xs)

            case NothingType():
                _ = xs.next()
                return Succeed(None, xs)

    return Parser(inner, "eof")


def succeed_with[S, T](v: T) -> Parser[S, T]:
    """`succeed_with` simply returns a success value
    containing `v`.

    This can be used to provide a default for or-chains."""

    def inner(xs: ParserInput[S]):
        return Succeed(v, xs, consumed=False)

    return Parser(inner, "succeed_with")


def fail_with[S, T](msg: str) -> Parser[S, T]:
    """`fail_with` simply returns an error value
    containing the message `msg`."""

    def inner(xs: ParserInput[S]):
        return cast(ParseResult[S, T], Fail("fail_with", msg, xs))

    return Parser(inner, "fail_with")


# ==============
# String Parsers
# ==============


def string_(item: str) -> Parser[str, str]:
    """`string_` matches a multi-character string literal."""
    label = f"[STR {item!r}]"

    def inner(xs: StringParserInput) -> ParseResult[str, str]:
        item_len = len(item)
        to_test = xs.get_string_view(item_len)
        if to_test == item:
            xs.consume(item_len)
            return cast(ParseResult[str, str], Succeed(to_test, xs))

        elif item_len > len(to_test):
            return cast(
                ParseResult[str, str],
                Fail(label, "end of input, expected {item!r}", xs),
            )

        else:
            return cast(
                ParseResult[str, str], Fail(label, f"unexpected {to_test!r}", xs)
            )

    return Parser(inner, label)  # pyright: ignore[reportArgumentType]


def regex(pat: re.Pattern[str] | str) -> Parser[str, str]:
    """`regex` attempts to match a regex pattern against input stream,
    returning the entire match value on success."""
    label = f"[REGEX {pat!r}]"

    def inner(xs: StringParserInput) -> ParseResult[str, str]:

        match: re.Match[str] | None = re.match(pat, xs.get_string_view())

        if match is None:
            return cast(
                ParseResult[str, str],
                Fail(label, f"expected input matching {pat!r}", xs),
            )

        else:
            xs.consume(match.end())
            return Succeed(match[0], xs)

    return Parser(inner, label)  # pyright: ignore[reportArgumentType]


def regex_captures(pat: re.Pattern[str] | str, *groups: int) -> Parser[str, tuple[str]]:
    """`regex` attempts to match a regex pattern against input stream,
    returning the entire match value on success."""
    label = f"[REGEX CAP {pat!r}]"

    def inner(xs: StringParserInput) -> ParseResult[str, tuple[str]]:

        match: re.Match[str] | None = re.match(pat, xs.get_string_view())

        if match is None:
            return cast(
                ParseResult[str, tuple[str]],
                Fail(label, f"expected input matching {pat!r}", xs),
            )

        else:
            xs.consume(match.end())
            return cast(
                ParseResult[str, tuple[str]],
                Succeed(tuple(match[group] for group in groups), xs),
            )

    return Parser(inner, label)  # pyright: ignore[reportArgumentType]


def space() -> Parser[str, str]:
    """`space` matches a single whitespace character."""
    return satisfy(lambda v: v in string_ops.whitespace, "whitespace")


def spaces():
    """`spaces` matches zero or more whitespace characters."""
    return many(space())


def alpha() -> Parser[str, str]:
    """`alpha` matches a single alphabetic character."""
    return satisfy(lambda v: v in string_ops.ascii_letters, "alpha")


def digit() -> Parser[str, str]:
    """`digit` matches a single numeric character."""
    return satisfy(lambda v: v in string_ops.digits, "digit")


def newline():
    """`newline` matches a literal linefeed character."""
    return literal("\n", "newline")


def crlf():
    """`crlf` matches a carriage return followed by a linefeed."""
    return literal("\r") & newline()


def end_of_line():
    return (newline() | crlf()).named("end of line")
