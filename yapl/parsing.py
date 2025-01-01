# MIT License
#
# Copyright (c) 2025 AnonymousDapper

from __future__ import annotations
from typing import Self

from dataclasses import dataclass, field

from .utils import F, Result, Ok, Err, Option, Some, Nothing

from . import utils


def foo():
    f: Option[int] = Some(5)

    match f:
        case Some(v): print(v)
        case Nothing(d): print(d)

@dataclass
class ParserPosition[S]:
    current_item: S
    offset: int

@dataclass
class StringParserPosition(ParserPosition[str]):
    line: int
    column: int

class ParserInput[S]:
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

class StringParserInput(ParserInput[str]):
    def __init__(self, src: str):
        self.source = src
        self.source_len = len(src)
        self.index = 0

        self.line = 1
        self.column = 1

    def get_position(self):
        return StringParserPosition(self.source.split("\n")[self.line-1], self.index, self.line, self.column)

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

type ParseReturn[T,S] = tuple[T, ParserInput[S]]

type ParserLabel = str
type ParserErrorMsg = str
@dataclass
class AbstractParser[S,T,E]:
    fn: F[ParserInput[S], Result[ParseReturn[T,S], E]]
    label: Option[ParserLabel] = field(init=False)

    def named(self: Self, label: ParserLabel):
        self.label = Some(label)
        return self

    def get_label(self) -> ParserLabel:
        return self.label.unwrap_or("")

    def run(self,_:ParserInput[S]):
        return self.fn(_)

    def parse(self, s: list[S]):
        return self.run(ParserInput(s))

type ParserError[S] = tuple[ParserLabel, ParserErrorMsg, ParserPosition[S]]
type ParseResult[S,T] = Result[ParseReturn[T,S], ParserError[S]]


class Parser[S,T](AbstractParser[S,T,ParserError[S]]):
    def __pos__(self: Self):
        return many(self)

    def __neg__(self: Self):
        return some(self)

    def __invert__(self: Self):
        return opt(self)

    def __or__(self: Self, other: Parser[S,T]):
        return or_(self, other)

    def __and__[a](self: Self, other: Parser[S,a]):
        return then(self, other)

    def __rshift__[a](self: Self, other: Parser[S,a]):
        return right(self, other)

    def __lshift__[a](self: Self, other: Parser[S,a]):
        return left(self, other)

    def __call__[a](self: Self, f: F[T,a]):
        return map_(f, self)

    def __rmatmul__[a](self, f: F[T,a]):
        return map_(f, self)

    def __pow__[b](self: Self, other: Parser[S, F[T,b]]):
        return apply(other, self)

    def __ge__[a](self: Self, f: F[T, Parser[S,a]]):
        return bind(f, self)

    def __truediv__[a](self: Self, other: Parser[S,a]):
        return sep_by(self, other)

    def __floordiv__[a](self, Self, other: Parser[S,a]):
        return sep_by_strict(self, other)


def print_result[S,T](r: ParseResult[S,T]):
    match r:
        case Ok((v,_)): print(repr(v))

        case Err((label,err,pos)):
            match pos:
                case StringParserPosition(i,o,l,c):
                    print(f"Error at parser {label}, Line {l} Column {c}:\n\t| {i}\n\t  {'^':>{c-1}} {err}")

                case ParserPosition(i,o):
                    print(f"Error at parser {label}, token #{o+1} {i!r} : {err}")

def parse_string[a](p: Parser[str, a]):
    def inner(s: str):
        r = p.run(StringParserInput(s))
        print_result(r)

    return inner


def named[S,T,E](p: AbstractParser[S,T,E], label: ParserLabel):
    p.label = Some(label)
    return p

def match_[S](pred: F[S,bool], label: ParserLabel):
    def inner(xs: ParserInput[S]) -> ParseResult[S,S]:
        match xs.peek():
            case Some(v):
                if pred(v): xs.next(); return Ok((v,xs))
                else: return Err((label, f"Unexpected {v!r}", xs.get_position()))
            case _: return Err((label, "no more input", xs.get_position()))

    return Parser(inner).named(label)

def lit[S](t: S):
    pred = lambda c: c == t
    return match_(pred, str(t))

def any_of[S](s: list[S]):
    return choice(list(map(lit, s)))

def then[S,a,b](p1: Parser[S,a], p2: Parser[S,b]):
    def inner(xs: ParserInput[S]) -> ParseResult[S, tuple[a,b]]:
        match p1.run(xs):
            case Err(_) as err: return err
            case Ok((v, rst)):
                match p2.run(rst):
                    case Err(_) as err: return err
                    case Ok((v2,rst2)):
                        return Ok(((v,v2),rst2))

    return Parser(inner)

curry_then = lambda p1: lambda p2: then(p1,p2)

def or_[S,a](p1: Parser[S,a], p2: Parser[S,a]):
    def inner(xs: ParserInput[S]):
        match p1.run(xs):
            case Ok(_) as r: return r
            case Err(_): return p2.run(xs)

    return Parser(inner)

curry_or = curry2(or_)

def choice[S,a](ps: list[Parser[S,a]]):
    return reduce(or_, ps)

def map_[S,a,b](f: F[a,b], p: Parser[S,a]):
    def inner(xs: ParserInput[S]):
        match p.run(xs):
            case Ok((v, rst)):
                try:
                    new_v = f(v)
                except Exception as e:
                    return Err((p.get_label(), f"map failed: {e}", xs.get_position()))
                else:
                    return Ok((new_v, rst))
            case Err(_) as r: return r

    return Parser(inner)

curry_map = curry2(map_)

def return_[S,a](x: a):
    def inner(xs: ParserInput[S]):
        return Ok((x, xs))

    return Parser(inner)

def apply[S,a,b](fp: Parser[S, F[a, b]], xp: Parser[S,a]):
    return map_(lambda t: first(t)(second(t)), then(fp, xp))

def lift2[S,a,b,c](f: F[a,b,c], xp: Parser[S,a], yp: Parser[S,b]):
    return apply(apply(return_(curry2(f)), xp), yp)

def lift3[S,a,b,c,d](f: F[a,b,c,d], xp: Parser[S,a], yp: Parser[S,b], zp: Parser[S,c]):
    return apply(apply(apply(return_(curry3(f)), xp), yp), zp)

def seq[S,a](l: list[Parser[S,a]]) -> Parser[S, list[a]]:
    consP = curry3(lift2)(curry2(cons))

    match l:
        case [h, *t]: return consP(h)(seq(t))
        case _      : return return_([])

def string(itm: str):
    pchars = list(map(lit, list(itm)))
    return map_(partial(str.join, ""), seq(pchars))

def integer() -> Parser[str,int]:
    pred = lambda s: s in "0123456789"
    ls = map_("".join, many(match_(pred, "number")))
    return map_(int, ls)

def _zero_or_more[S,a](p: Parser[S,a], inp: ParserInput[S]) -> tuple[list[a], ParserInput[S]]:
    match p.run(inp):
        case Err(_): return ([], inp)
        case Ok((val, first_rem)):
            (sub_vals, rem) = _zero_or_more(p, first_rem)
            return (cons(val, sub_vals), rem)

def some[S,a](p: Parser[S,a]) :
    def inner(xs: ParserInput[S]):
        return Ok(_zero_or_more(p, xs))

    return Parser(inner)

def many[S,a](p: Parser[S,a]) :
    def inner(xs: ParserInput[S]):
        match p.run(xs):
            case Err(_) as e: return e
            case Ok((val, first_rem)):
                (sub_vals, rem) = _zero_or_more(p, first_rem)
                return Ok((cons(val, sub_vals), rem))

    return Parser(inner)

def opt[S,a](p: Parser[S,a]):
    some: Parser[S, Option[a]] = map_(Some, p)
    none: Parser[S, Option[a]] = return_(Nothing)

    return or_(some, none)

def between[S,a,b,c](l: Parser[S,a], p: Parser[S,b], r: Parser[S,c]):
    return right(l, left(p, r))

def left[S,a,b](p1: Parser[S,a], p2: Parser[S,b]):
    return map_(lambda v: first(v), then(p1, p2))

def right[S,a,b](p1: Parser[S,a], p2: Parser[S,b]):
    return map_(lambda v: second(v), then(p1, p2))

def sep_by_strict[S,a,b](p: Parser[S,a], sep: Parser[S,b]):
    pair = right(sep, p)
    return map_(lambda v: cons(*v), then(p, some(pair)))

def sep_by[S,a,b](p: Parser[S,a], sep: Parser[S,b]):
    return or_(sep_by_strict(p, sep), return_([]))

def bind[S,a,b](f: F[a, Parser[S,b]], p: Parser[S,a]):
    def inner(xs: ParserInput[S]):
        match p.run(xs):
            case Err(_) as err: return err
            case Ok((v, rem)): 
                p2 = f(v)
                return p2.run(rem)

    return Parser(inner)
