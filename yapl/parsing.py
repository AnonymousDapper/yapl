# MIT License
#
# Copyright (c) 2025 AnonymousDapper

from __future__ import annotations

__all__ = (
    "Parser",
    "ParserError",
    "ParserValue",
    "ParserInput",
    "StringParserInput",
    "ParserPosition",
    "StringParserPosition",
    "ParseResult",
    "ParserLabel",
    "ParserErrorMsg",
    "print_result",
    "defer",
    "times",
    "many",
    "many1",
    "and_",
    "or_",
    "or_strict",
    "map_",
    "pure",
    "optional",
    "bind",
    "apply",
    "lift2",
    "seq",
    "left",
    "right",
    "sep_by",
    "sep_by1",
    "satisfy",
    "literal",
    "any_",
    "one_of",
    "none_of",
    "eof",
    "succeed_with",
    "fail_with",
    "between",
    "fix",
    "space",
    "spaces",
    "letter",
    "digit",
    "string",
    "newline",
    "crlf",
    "end_of_line",
    "binary",
    "octal",
    "hexadecimal",
    "decimal",
    "natural",
)

import itertools
from dataclasses import dataclass
from typing import Self, overload

from . import utils
from .utils import Err, F, Nothing, Ok, Option, Result, Some

type ParserLabel = str
type ParserErrorMsg = str

type ParseResult[S, T] = Result[ParserValue[S, T], ParserError[S]]


@dataclass
class ParserPosition[S]:
    __slots__ = ("current_item", "offset")

    current_item: S
    offset: int

    def __repr__(self):
        return f"ParserPosition({self.offset})"


@dataclass
class StringParserPosition(ParserPosition[str]):
    __slots__ = ("current_item", "offset", "line", "column")

    line: int
    column: int

    def __repr__(self):
        return f"StringParserPosition({self.offset}, L{self.line}:{self.column})"


class ParserInput[S]:
    __slots__ = ("source", "source_len", "index")

    def __init__(self, src: list[S]):
        self.source = src
        self.source_len = len(src)
        self.index = 0

    def get_position(self):
        return ParserPosition(self.source[self.index], self.index)

    def next(self) -> Option[S]:
        if self.index < self.source_len:
            val = self.source[self.index]
            self.index += 1
            return Some(val)

        return Nothing

    def peek(self) -> Option[S]:
        if self.index < self.source_len:
            return Some(self.source[self.index])

        return Nothing

    def store(self):
        temp = self.index

        def inner():
            self.index = temp

        return inner


class StringParserInput(ParserInput[str]):
    __slots__ = ("source", "source_len", "index", "line", "column")

    def __init__(self, src: str):
        self.source = src
        self.source_len = len(src)
        self.index = 0

        self.line = 1
        self.column = 1

    def get_position(self):
        return StringParserPosition(
            self.source.split("\n")[self.line - 1], self.index, self.line, self.column
        )

    def next(self) -> Option[str]:
        if self.index < self.source_len:
            self.column += 1
            if (val := self.source[self.index]) == "\n":
                self.line += 1
                self.column = 1

            self.index += 1
            return Some(val)

        return Nothing

    def peek(self) -> Option[str]:
        if self.index < self.source_len:
            return Some(self.source[self.index])

        return Nothing

    def store(self):
        temp = (self.index, self.line, self.column)

        def inner():
            self.index, self.line, self.column = temp

        return inner


class ParserError[S]:
    __slots__ = ("label", "msg", "position", "consumed")

    def __init__(
        self,
        label: ParserLabel,
        msg: ParserErrorMsg,
        position: ParserPosition[S],
        consumed: bool = True,
    ):
        self.label = label
        self.msg = msg
        self.position = position
        self.consumed = consumed

    def with_msg(self, msg: ParserErrorMsg) -> Self:
        self.msg = msg
        return self

    def set_consumed(self, c: bool):
        self.consumed = c

    def print_err(self):
        match self.position:
            case StringParserPosition(i, o, l, c):
                print(
                    f"Error at parser {self.label}, Line {l} Column {c}:\n\t| {i}\n\t  {'^':>{c}} {self.msg}"
                )
            case ParserPosition(i, o):
                print(f"Error at parser {self.label}, token #{o+1} {i!r} : {self.msg}")

    def __repr__(self):
        return f"ParserError([{self.consumed and '+' or '-'}] {self.label!r} @ {self.position!r})"


class ParserValue[S, T]:
    __slots__ = ("item", "remains", "consumed")

    def __init__(self, item: T, input_: ParserInput[S], consumed: bool = True):
        self.item = item
        self.remains = input_
        self.consumed = consumed

    def set_consumed(self, c: bool):
        self.consumed = c

    def __repr__(self):
        return f"ParserReturn([{self.consumed and '+' or '-'}]: {self.item!r})"


class AbstractParser[S, T, E]:
    __slots__ = ("fn", "label")

    type ParserFn = F[ParserInput[S], ParseResult[S, T]]

    fn: ParserFn
    label: Option[ParserLabel]

    def __init__(
        self,
        fn: ParserFn,
        name: str | None = None,
        *,
        label: Option[ParserLabel] = Nothing,
    ):
        self.fn = fn
        self.label = label

        if name is not None:
            self.fn.__name__ = name

    def named(self: Self, label: ParserLabel):
        self.label = Some(label)
        return self

    def get_label(self) -> ParserLabel:
        return self.label.unwrap_or("?")

    def run(self, i: ParserInput[S]):
        return self.fn(i)


class Parser[S, T](AbstractParser[S, T, ParserError[S]]):
    def __pos__(self):
        """+ a
        Matches one or more of a."""
        return many1(self)

    def __neg__(self):
        """- a
        Matches zero or more of a."""
        return many(self)

    def __invert__(self):
        """~ a
        Attempts to match a, returning Some if successful, Nothing otherwise."""
        return optional(self)

    def __or__(self, other: Parser[S, T]):
        """a | b
        Attempts to match a, and attempts b if a fails.

        If a fails and consumes input, the parser will backtrack and then attempt b.
        """
        return or_(self, other)

    def ___xor__(self, other: Parser[S, T]):
        """a ^ b
        Attempts to match a, and attempts b if a fails.

        If a fails and consumes input, this parser will NOT backtrack. Use with caution.
        """

        return or_strict(self, other)

    def __and__[a](self, other: Parser[S, a]):
        """a & b
        Matches a followed by b, keeping both results."""
        return and_(self, other)

    def __call__[a](self, f: F[T, a]):
        """a(f)
        Maps the result of a using function f."""
        return map_(f, self)

    def __rmatmul__[a](self, f: F[T, a]):
        """f @ a
        Maps the result of a using function f."""
        return map_(f, self)

    def __matmul__[a](self, f: F[T, a]):
        """a @ f
        Maps the result of a using function f."""
        return map_(f, self)

    def __pow__[b](self, other: Parser[S, F[T, b]]):
        """a ** b
        Applies the result of a to the result of b."""
        return apply(other, self)

    def __ge__[a](self, f: F[T, Parser[S, a]]):
        """a >= b
        Binds the result of a to a parser returned by b."""
        return bind(f, self)

    def __lt__[a](self, other: Parser[S, a]):
        """a < b
        Matches a followed by b, only keeping a."""
        return left(self, other)

    def __gt__[a](self, other: Parser[S, a]):
        """a > b
        Matches a followed by b, only keeping b."""
        return right(self, other)

    def __truediv__[a](self, other: Parser[S, a]):
        """a / b
        Matches zero or more of a separated by b."""
        return sep_by(self, other)

    def __floordiv__[a](self, other: Parser[S, a]):
        """a // b
        Matches one or more of a separated by b."""
        return sep_by1(self, other)

    def __mul__[a](self, other: a):
        return self > succeed_with(other)


def print_result[S, T](r: ParseResult[S, T]):
    match r:
        case Ok(v):
            print(f"Success: {v.item!r}")
            return v.item

        case Err(e):
            e.print_err()


## --------------------------
## Primitive Combinators
## --------------------------


def defer[S, T](f: F[Parser[S, T]]):
    """Given a parser-producing function, `defer` will not evaluate the function until the parser is run."""

    def inner(xs: ParserInput[S]):
        return f().run(xs)

    return Parser(inner, "defer")


def times[S, T](p: Parser[S, T], _min: int, _max: int | None = None):
    """Repeat a parser between `min` and `max` times.
    Note: `times` is unbounded when `max` is `None`
    """

    def inner(xs: ParserInput[S]) -> ParseResult[S, list[T]]:
        load = xs.store()
        acc = []
        for _ in range(_min):
            r = p.run(xs)
            if r.is_ok():
                acc.append(r.unwrap().item)
            else:
                load()
                return Err(r.unwrap_err())

        for _ in range(_max - _min) if _max is not None else itertools.count():
            r = p.run(xs)
            if r.is_ok():
                acc.append(r.unwrap().item)
            else:
                if r.unwrap_err().consumed:
                    return Err(r.unwrap_err())
                break

        return Ok(ParserValue(acc, xs, consumed=bool(_max)))

    return Parser(inner, "times")


def many[S, T](p: Parser[S, T]):
    """Repeat a parser zero or more times."""
    return times(p, 0, None)


def many1[S, T](p: Parser[S, T]):
    """Repeat a parser one or more times."""
    return times(p, 1, None)


def and_[S, a, b](p1: Parser[S, a], p2: Parser[S, b]):
    """Attempt two parsers in sequence and keep both results in a tuple."""

    def inner(xs: ParserInput[S]) -> ParseResult[S, tuple[a, b]]:
        load = xs.store()
        match p1.run(xs):
            case Err(e):
                load()
                return Err(e)
            case Ok(v):
                match p2.run(v.remains):
                    case Err(e):
                        load()
                        return Err(e)
                    case Ok(v2):
                        return Ok(ParserValue((v.item, v2.item), v2.remains))

    return Parser(inner, "and_")


def or_[S, a](p1: Parser[S, a], p2: Parser[S, a]):
    """Attempt parser a. If it fails, run parser b with full backtracking."""

    def inner(xs: ParserInput[S]) -> ParseResult[S, a]:
        load = xs.store()
        match p1.run(xs):
            case Ok(_) as r:
                return r
            case Err(e):
                load()
                return p2.run(xs)

    return Parser(inner, "or_")


def or_strict[S, a](p1: Parser[S, a], p2: Parser[S, a]):
    """Attempt parser a. If it fails without consuming input, run parser b without backtracking."""

    def inner(xs: ParserInput[S]) -> ParseResult[S, a]:
        match p1.run(xs):
            case Ok(_) as r:
                return r
            case Err(e):
                if not e.consumed:
                    return p2.run(xs)
                else:
                    return Err(e)

    return Parser(inner, "or_strict")


def map_[S, a, b](f: F[a, b], p: Parser[S, a]):
    """Attempt parser p and apply function f to the resultant value if succcessful."""

    def inner(xs: ParserInput[S]) -> ParseResult[S, b]:
        load = xs.store()
        match p.run(xs):
            case Ok(v):
                try:
                    new_v = f(v.item)
                except Exception as e:
                    load()
                    return Err(
                        ParserError(
                            p.get_label(), f"map call failed: {e}", xs.get_position()
                        )
                    )
                else:
                    return Ok(ParserValue(new_v, v.remains))

            case Err(e):
                load()
                return Err(e)

    return Parser(inner, "map_")


def pure[S, a](x: a) -> Parser[S, a]:
    """pure consumes no input and only returns the given value."""

    def inner(xs: ParserInput[S]):
        return Ok(ParserValue(x, xs, consumed=False))

    return Parser(inner, "pure")


def optional[S, a](p: Parser[S, a], default: Option[a] = Nothing):
    """Attempt parser p, returning `Some(value)` on success.
    On failure, optional returns the provided value (default Nothing)
    """
    some = map_(Some, p)
    none = pure(default)

    return or_(some, none).named(f"optional {p.get_label()}")


def bind[S, a, b](f: F[a, Parser[S, b]], p: Parser[S, a]):
    """Given a parser producing type a and a function of type a->Parser[b],
    `bind` returns a parser producing type b. (Monadic bind)
    """

    def inner(xs: ParserInput[S]) -> ParseResult[S, b]:
        load = xs.store()
        match p.run(xs):
            case Err(e):
                load()
                return Err(e)
            case Ok(v):
                try:
                    p2 = f(v.item)
                except Exception as e:
                    load()
                    return Err(
                        ParserError(
                            p.get_label(), f"bind call failed: {e}", xs.get_position()
                        )
                    )
                else:
                    return p2.run(v.remains)

    return Parser(inner, "bind")


def apply[S, a, b](fp: Parser[S, F[a, b]], xp: Parser[S, a]) -> Parser[S, b]:
    """Given a parser producing a function of type a->b and a parser producing type a,
    `apply` returns a parser producing type b.
    """
    return fp >= (lambda f: xp >= (lambda x: pure(f(x))))


def lift2[S, a, b, c](f: F[a, b, c], xp: Parser[S, a], yp: Parser[S, b]):
    """`lift2` applies a binary function of type (a, b)->c to two parsers,
    one producing type a and one producing type b and returns a parser
    producing type c.
    """
    return apply(apply(pure(utils.curry2(f)), xp), yp)


def seq[S, T](ps: list[Parser[S, T]]) -> Parser[S, list[T]]:
    """Given a list of parsers, `seq` returns a parser producing a list of the results."""

    match ps:
        case [h, *t]:
            return lift2(utils.cons, h, seq(t))
        case _:
            return pure([])


def left[S, a, b](p1: Parser[S, a], p2: Parser[S, b]) -> Parser[S, a]:
    """`left` matches two parsers in sequence and keeps only the result of the first."""
    return map_(utils.first, p1 & p2)


def right[S, a, b](p1: Parser[S, a], p2: Parser[S, b]) -> Parser[S, b]:
    """`right` matches two parsers in sequence and keeps only the result of the second."""
    return map_(utils.second, p1 & p2)


def sep_by[S, a, b](p: Parser[S, a], sep: Parser[S, b]) -> Parser[S, list[a]]:
    """`sep_by` matches zero or more occurrences of `p` separated by `sep`."""
    return (lambda pair: utils.cons(*pair)) @ (p & many(sep > p))


def sep_by1[S, a, b](p: Parser[S, a], sep: Parser[S, b]) -> Parser[S, list[a]]:
    """`sep_by1` matches one or more occurrences of `p` separated by `sep`."""
    return (lambda pair: utils.cons(*pair)) @ (p & many1(sep > p))


## --------------------------
## Source-aware Combinators
## --------------------------


def satisfy[S](f: F[S, bool], label: ParserLabel):
    """Accept one item from the input if it satisfies the predicate f."""

    def inner(xs: ParserInput[S]):
        match xs.peek():
            case Some(v):
                if f(v):
                    xs.next()
                    return Ok(ParserValue(v, xs))
                else:
                    return Err(
                        ParserError(
                            label,
                            f"Unexpected {v!r}",
                            xs.get_position(),
                            consumed=False,
                        )
                    )

            case _:
                return Err(
                    ParserError(
                        label,
                        f"end of input, expected {label}",
                        xs.get_position(),
                        consumed=False,
                    )
                )

    return Parser(inner, "satisfy")


def literal[S](v: S, label: ParserLabel | None = None):
    """Accept one item from the input if it matches the given value."""
    return satisfy(lambda x: x == v, label or repr(v))


def any_[S]() -> Parser[S, S]:
    """Accept any one item from the input."""
    return satisfy(lambda _: True, "anything")


def one_of[S](vs: list[S]) -> Parser[S, S]:
    """Accept one item from the input if it is one of the given values."""
    return satisfy(lambda x: x in vs, f"one of {vs}")


def none_of[S](vs: list[S]) -> Parser[S, S]:
    """Accept one item from the input if it is not one of the given values."""
    return satisfy(lambda x: x not in vs, f"none of {vs}")


def eof[S]():
    """Attempt to parse EOF, returning success if the input is empty."""

    def inner(xs: ParserInput[S]):
        match xs.peek():
            case Some(_):
                return Err(
                    ParserError(
                        "eof",
                        "expected end of input",
                        xs.get_position(),
                        consumed=False,
                    )
                )
            case _:
                xs.next()
                return Ok(ParserValue(None, xs))

    return Parser(inner, "eof")


## --------------------------
## Utility Combinators
## --------------------------


def succeed_with[S, T](v: T):
    def inner(xs: ParserInput[S]):
        return Ok(ParserValue(v, xs))

    return Parser(inner, "succeed_with")


def fail_with[S, T](msg: ParserErrorMsg):
    def inner(xs: ParserInput[S]):
        return Err(ParserError("fail", msg, xs.get_position()))

    return Parser(inner, "fail_with")


def between[
    S, a, b, c
](open_: Parser[S, a], close: Parser[S, c], p: Parser[S, b]) -> Parser[S, b]:
    return open_ > p < close


def fix[S, T](f: F[Parser[S, T], Parser[S, T]]):
    """Given a function f of type (Parser->Parser), `fix` returns a parser that is the fixed point of f."""
    return defer(lambda: f(fix(f)))


## --------------------------
## String Parsers
## --------------------------


def space():
    """Matches a single whitespace character."""
    return satisfy(str.isspace, "whitespace")


def spaces():
    """Matches zero or more whitespace characters."""
    return many(space())


def letter():
    """Matches a single letter character."""
    return satisfy(str.isalpha, "letter")


def digit():
    """Matches a single digit character."""
    return satisfy(str.isdigit, "digit")


def string(itm: str):
    """Matches a multi-character string literal."""
    pchars = list(map(literal, itm))
    return map_(utils.partial(str.join, ""), seq(pchars)).named(
        f"string literal: {itm}"
    )


# TODO: regexp


def newline():
    """Matches a newline character."""
    return literal("\n", "newline")


def crlf():
    """Matches a carriage return followed by a newline."""
    return literal("\r") > newline()


def end_of_line():
    return (newline() | crlf()).named("end of line")


## --------------------------
## Number Parsers
## --------------------------


def _number(base, digit):
    return many1(digit) @ (
        lambda ds: utils.reduce(lambda acc, d: acc * base + int(d, base), ds, 0)
    )


b_digit = one_of("01").named("binary digit")
b_number = _number(2, b_digit).named("binary number")
binary = (one_of("bB") > b_number).named("binary")

o_digit = one_of("01234567").named("octal digit")
o_number = _number(8, o_digit).named("octal number")
octal = (one_of("oO") > o_number).named("octal")

h_digit = one_of("0123456789abcdefABCDEF").named("hex digit")
h_number = _number(16, h_digit).named("hex number")
hexadecimal = (one_of("xX") > h_number).named("hexadecimal")

d_number = _number(10, digit()).named("decimal number")
decimal = d_number.named("decimal")

zero_pfx = literal("0") > (hexadecimal | octal | binary | decimal | succeed_with(0))
natural = zero_pfx | decimal
