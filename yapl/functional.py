# MIT License
#
# Copyright (c) 2025 AnonymousDapper

# pyright: reportImplicitOverride=false

from __future__ import annotations

__all__ = (
    "compose",
    "cons",
    "curry1",
    "curry2",
    "curry3",
    "curry4",
    "drop_while",
    "Err",
    "F",
    "first",
    "flatten",
    "head",
    "is_err",
    "is_none",
    "is_ok",
    "is_some",
    "Nothing",
    "Ok",
    "Option",
    "partial",
    "reduce",
    "Result",
    "second",
    "Some",
    "tail",
    "take_while",
)

from collections.abc import Callable, Generator, Iterable, Iterator, Sequence
from functools import reduce
from itertools import dropwhile as drop_while
from itertools import takewhile as take_while
from typing import Any, Concatenate, TypeIs, cast

type F[*P, R] = Callable[[*P], R]

type Result[T, E] = Ok[T] | Err[E]

type Option[T] = Some[T] | NothingType


# TODO: on recursive type alias release:
# replace with Union[*T]
type Nested = Any | Iterable["Nested[Any]"]


def is_ok[T, E](v: Result[T, E]) -> TypeIs[Ok[T]]:
    return isinstance(v, Ok)


def is_err[T, E](v: Result[T, E]) -> TypeIs[Err[E]]:
    return isinstance(v, Err)


def is_some[T](v: Option[T]) -> TypeIs[Some[T]]:
    return isinstance(v, Some)


def is_none[T](v: Option[T]) -> TypeIs[NothingType]:
    return isinstance(v, NothingType)


def partial[**P, T, R](f: Callable[Concatenate[T, P], R], v: T) -> Callable[P, R]:
    def inner(*a: P.args, **k: P.kwargs):
        return f(v, *a, **k)

    return inner


def compose[**P, T, R](r: Callable[P, T], l: F[T, R]) -> Callable[P, R]:
    """Equivalent to `r >> l`"""

    def inner(*a: P.args, **k: P.kwargs):
        return l(r(*a, **k))

    return inner


# TODO:
#      also waiting on recursive variadics


def curry1[a, R](f: F[a, R]) -> F[a, R]:
    return f


def curry2[a, b, R](f: F[a, b, R]) -> F[a, F[b, R]]:
    def inner(a: a):
        return partial(f, a)

    return inner


def curry3[a, b, c, R](f: F[a, b, c, R]) -> F[a, F[b, F[c, R]]]:
    def outer(a: a):
        def inner(b: b):
            return partial(partial(f, a), b)

        return inner

    return outer


def curry4[a, b, c, d, R](f: F[a, b, c, d, R]) -> F[a, F[b, F[c, F[d, R]]]]:
    def outer(a: a):
        def inner(b: b):
            def third(c: c):
                return partial(partial(partial(f, a), b), c)

            return third

        return inner

    return outer


def head[a](xs: Sequence[a]) -> a:
    return xs[0]


def tail[a](xs: Sequence[a]) -> Sequence[a]:
    return xs[1::]


def first[a, b](t: tuple[a, b]) -> a:
    (a, _) = t
    return a


def second[a, b](t: tuple[a, b]) -> b:
    (a, b) = t
    return b


def cons[a](v: a, ls: list[a]) -> list[a]:
    return [v] + ls


def flatten[T](xs: Iterable[Nested]) -> Generator[Any, None, None]:
    for x in xs:
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
            yield from flatten(x)

        else:
            yield x


class _Result[T, E]:
    __slots__ = ("v", "e")
    v: T  # pyright: ignore[reportUninitializedInstanceVariable]
    e: E  # pyright: ignore[reportUninitializedInstanceVariable]

    def is_ok_and(self, f: F[T, bool]):
        obj = cast(Result[T, E], self)

        if is_ok(obj):
            return f(obj.v)

        return False

    def is_err_and(self, f: F[E, bool]):
        obj = cast(Result[T, E], self)
        if is_err(obj):
            return f(obj.e)

        return False

    def ok(self) -> Option[T]:
        obj = cast(Result[T, E], self)

        if is_ok(obj):
            return Some(obj.v)

        return Nothing

    def err(self) -> Option[E]:
        obj = cast(Result[T, E], self)

        if is_err(obj):
            return Some(obj.e)

        return Nothing

    def map[V](self, f: F[T, V]) -> Result[V, E]:
        obj = cast(Result[T, E], self)

        if is_ok(obj):
            return Ok(f(obj.v))

        return obj

    def map_or[V](self, default: V, f: F[T, V]) -> V:
        obj = cast(Result[T, E], self)

        if is_ok(obj):
            return f(obj.v)

        return default

    def map_or_else[V](self, default: F[E, V], f: F[T, V]) -> V:
        obj = cast(Result[T, E], self)

        if is_ok(obj):
            return f(obj.v)

        return default(obj.e)

    def and_[V](self, r: Result[V, E]) -> Result[V, E]:
        obj = cast(Result[T, E], self)

        if is_ok(obj):
            return r

        return obj

    def and_then[V](self, f: F[T, Result[V, E]]) -> Result[V, E]:
        obj = cast(Result[T, E], self)

        if is_ok(obj):
            return f(obj.v)

        return obj

    def or_[R](self, r: Result[T, R]) -> Result[T, R]:
        obj = cast(Result[T, E], self)

        if is_err(obj):
            return r

        return obj

    def or_else[R](self, f: F[E, Result[T, R]]) -> Result[T, R]:
        obj = cast(Result[T, E], self)

        if is_err(obj):
            return f(obj.e)

        return obj

    def inspect(self, f: F[T, None]) -> Result[T, E]:
        obj = cast(Result[T, E], self)

        if is_ok(obj):
            f(obj.v)
            return obj

        return obj

    def inspect_err(self, f: F[E, None]) -> Result[T, E]:
        obj = cast(Result[T, E], self)

        if is_err(obj):
            f(obj.e)
            return obj

        return obj

    def iter(self) -> Iterator[T]:
        obj = cast(Result[T, E], self)

        if is_ok(obj):
            item = [obj.v]
        else:
            item = []

        return iter(item)

    def expect(self, msg: str) -> T:
        obj = cast(Result[T, E], self)

        if is_ok(obj):
            return obj.v

        raise Exception(msg)

    def unwrap(self) -> T:
        obj = cast(Result[T, E], self)

        if is_ok(obj):
            return obj.v

        raise Exception(f"called `Result.unwrap()` on an `Err` value: {obj.e!r}")

    def expect_err(self, msg: str) -> E:
        obj = cast(Result[T, E], self)

        if is_err(obj):
            return obj.e

        raise Exception(msg)

    def unwrap_err(self) -> E:
        obj = cast(Result[T, E], self)

        if is_err(obj):
            return obj.e

        raise Exception(f"called `Result.unwrap_err()` on an `Ok` value: {obj.v!r}")

    def unwrap_or(self, default: T) -> T:
        obj = cast(Result[T, E], self)

        if is_ok(obj):
            return obj.v

        return default

    def unwrap_or_else(self, f: F[E, T]) -> T:
        obj = cast(Result[T, E], self)

        if is_ok(obj):
            return obj.v

        return f(obj.e)


class Ok[T](_Result[T, object]):
    __slots__ = ("v",)
    __match_args__ = ("v",)

    v: T

    def __init__(self, item: T):
        self.v = item

    def __repr__(self):
        return f"Ok({self.v!r})"


class Err[E](_Result[object, E]):
    __slots__ = ("e",)
    __match_args__ = ("e",)

    e: E

    def __init__(self, item: E):
        self.e = item

    def __repr__(self):
        return f"Err({self.e!r})"


class _Option[T]:
    __slots__ = ("v",)
    v: T  # pyright: ignore[reportUninitializedInstanceVariable]

    def is_some_and(self, f: F[T, bool]) -> bool:
        obj = cast(Option[T], self)

        if is_some(obj):
            return f(obj.v)

        return False

    def is_none_or(self, f: F[T, bool]):
        obj = cast(Option[T], self)

        if is_none(obj):
            return False

        return f(obj.v)

    def map[V](self, f: F[T, V]) -> Option[V]:
        obj = cast(Option[T], self)

        if is_some(obj):
            return Some(f(obj.v))

        return Nothing

    def map_or[V](self, default: V, f: F[T, V]) -> V:
        obj = cast(Option[T], self)

        if is_some(obj):
            return f(obj.v)

        return default

    def map_or_else[V](self, default: F[V], f: F[T, V]) -> V:
        obj = cast(Option[T], self)

        if is_some(obj):
            return f(obj.v)

        return default()

    def and_[V](self, o: Option[V]) -> Option[V]:
        obj = cast(Option[T], self)

        if is_some(obj):
            return o

        return Nothing

    def and_then[V](self, f: F[T, Option[V]]) -> Option[V]:
        obj = cast(Option[T], self)

        if is_some(obj):
            return f(obj.v)

        return Nothing

    def or_(self, o: Option[T]) -> Option[T]:
        obj = cast(Option[T], self)

        if is_some(obj):
            return obj

        return o

    def or_else(self, f: F[Option[T]]) -> Option[T]:
        obj = cast(Option[T], self)

        if is_some(obj):
            return obj

        return f()

    def xor(self, o: Option[T]) -> Option[T]:
        obj = cast(Option[T], self)

        if is_some(obj):
            if is_none(o):
                return obj

        if is_none(obj):
            if is_some(o):
                return o

        return Nothing

    def zip[V](self, o: Option[V]) -> Option[tuple[T, V]]:
        obj = cast(Option[T], self)

        if is_some(obj):
            if is_some(o):

                return Some((obj.unwrap(), o.unwrap()))

        return Nothing

    def filter(self, f: F[T, bool]) -> Option[T]:
        obj = cast(Option[T], self)

        if is_some(obj):
            return f(obj.v) and obj or Nothing

        return Nothing

    def iter(self) -> Iterator[T]:
        obj = cast(Option[T], self)

        if is_some(obj):
            item = [obj.v]
        else:
            item = []

        return iter(item)

    def ok_or[E](self, err: E) -> Result[T, E]:
        obj = cast(Option[T], self)

        if is_some(obj):
            return Ok(obj.v)

        return Err(err)

    def ok_or_else[E](self, err: F[E]) -> Result[T, E]:
        obj = cast(Option[T], self)

        if is_some(obj):
            return Ok(obj.v)

        return Err(err())

    def unwrap(self) -> T:
        obj = cast(Option[T], self)

        if is_some(obj):
            return obj.v

        raise Exception(f"called `Option.unwrap` on a {obj!r} value")

    def unwrap_or(self, default: T) -> T:
        obj = cast(Option[T], self)

        if is_some(obj):
            return obj.v

        return default

    def unwrap_or_else(self, f: F[T]) -> T:
        obj = cast(Option[T], self)

        if is_some(obj):
            return obj.v

        return f()


class Some[T](_Option[T]):
    __slots__ = ("v",)
    __match_args__ = ("v",)

    v: T

    def __init__(self, item: T):
        self.v = item

    def __repr__(self):
        return f"Some({self.v!r})"


class NothingType(_Option[None]):
    __slots__ = tuple()

    def __repr__(self):
        return f"Nothing"


Nothing = NothingType()
