# MIT License
#
# Copyright (c) 2025 AnonymousDapper

from __future__ import annotations

__all__ = (
    "F",
    "partial",
    "compose",
    "curry1",
    "curry2",
    "curry3",
    "curry4",
    "head",
    "tail",
    "zp",
    "first",
    "second",
    "cons",
    "reduce",
    "take_while",
    "drop_while",
    "Result",
    "Ok",
    "Err",
    "Option",
    "Some",
    "Nothing",
)

from typing import Callable, Concatenate, TypeGuard

type F[*P, R] = Callable[[*P], R]


def partial[**P, T, R](f: Callable[Concatenate[T, P], R], v: T) -> Callable[P, R]:
    def inner(*a: P.args, **k: P.kwargs):
        return f(v, *a, **k)

    return inner


def compose[**P, T, R](l: F[T, R], r: Callable[P, T]) -> Callable[P, R]:
    def inner(*a: P.args, **k: P.kwargs):
        return l(r(*a, **k))

    return inner


def curry1[a, R](f: F[a, R]) -> F[a, R]:
    return f


def curry2[a, b, R](f: F[a, b, R]) -> F[a, F[b, R]]:
    def inner(a):
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


def head[a](xs: list[a]) -> a:
    return xs[0]


def tail[a](xs: list[a]) -> list[a]:
    return xs[1::]


def zp[a, b](ls: list[a], rs: list[b]) -> list[tuple[a, b]]:
    return list(zip(ls, rs))


def first[a, b](t: tuple[a, b]) -> a:
    (a, b) = t
    return a


def second[a, b](t: tuple[a, b]) -> b:
    (a, b) = t
    return b


def cons[a](v: a, ls: list[a]) -> list[a]:
    return [v] + ls


def reduce[a, b](f: F[b, a, b], arr: list[a], initial: b):
    for x in arr:
        initial = f(initial, x)

    return initial


def take_while[a](f: F[a, bool], lst: list[a]) -> list[a]:
    i = 1
    while f(lst[0:i][-1]):
        i += 1

    return lst[0 : i - 1]


def drop_while[a](f: F[a, bool], lst: list[a]) -> list[a]:
    i = 0
    l = len(lst)
    while f(lst[i:][0]):
        i += 1
        if i == l:
            break

    return lst[min(i, l) :]


def _tg_is_ok[T, E](r: Ok[T, E]) -> TypeGuard[Ok[T, E]]:
    return True


def _tg_is_err[T, E](r: Err[T, E]) -> TypeGuard[Err[T, E]]:
    return True


def _tg_is_not_ok[T, E](r: Err[T, E]) -> TypeGuard[Ok[T, E]]:
    return False


def _tg_is_not_err[T, E](r: Ok[T, E]) -> TypeGuard[Err[T, E]]:
    return False


class _Result[T, E]:
    _t: T
    _e: E
    _OK: bool
    __match_args__: tuple[str]

    __slots__ = "_t", "_e"

    def is_ok(self):
        return self._OK

    def is_ok_and(self, f: F[T, bool]):
        return self._OK and f(self._t)

    def is_err(self):
        return not self._OK

    def is_err_and(self, f: F[E, bool]):
        return (not self._OK) and f(self._e)

    def ok(self) -> Option[T]:
        return self._OK and Some(self._t) or Nothing

    def err(self) -> Option[E]:
        return (not self._OK) and Some(self._e) or Nothing

    def map[U](self, f: F[T, U]) -> Result[U, E]:
        return self._OK and Ok(f(self._t)) or Err(self._e)

    def map_or[U](self, d: U, f: F[T, U]) -> U:
        return self._OK and f(self._t) or d

    def map_or_else[U](self, d: F[E, U], f: F[T, U]) -> U:
        return self._OK and f(self._t) or d(self._e)

    def map_err[U](self, f: F[E, U]) -> Result[T, U]:
        return (not self._OK) and Err(f(self._e)) or Ok(self._t)

    def inspect(self, f: Callable[[T], None]) -> Result[T, E]:
        if self._OK:
            f(self._t)
            return Ok(self._t)
        return Err(self._e)

    def inspect_err(self, f: Callable[[E], None]) -> Result[T, E]:
        if not self._OK:
            f(self._e)
            return Err(self._e)
        return Ok(self._t)

    def expect(self, msg: str):
        if self._OK:
            return self._t
        else:
            raise Exception(msg)

    def unwrap(self):
        if self._OK:
            return self._t
        else:
            raise Exception(self._e)

    def expect_err(self, msg: str):
        if not self._OK:
            return self._e

        else:
            raise Exception(msg)

    def unwrap_err(self):
        if not self._OK:
            return self._e
        else:
            raise Exception(self._t)

    def and_[U](self, res: Result[U, E]) -> Result[U, E]:
        if self._OK:
            return res

        return Err(self._e)

    def and_then[U](self, f: F[T, Result[U, E]]) -> Result[U, E]:
        if self._OK:
            return f(self._t)

        return Err(self._e)

    def or_[U](self, res: Result[T, U]) -> Result[T, U]:
        if not self._OK:
            return res

        return Ok(self._t)

    def or_else[U](self, f: F[E, Result[T, U]]) -> Result[T, U]:
        if not self._OK:
            return f(self._e)

        return Ok(self._t)

    def unwrap_or(self, d: T) -> T:
        return self._OK and self._t or d

    def unwrap_or_else(self, f: F[E, T]) -> T:
        return self._OK and self._t or f(self._e)


class Ok[T, E](_Result[T, E]):
    _OK = True
    __match_args__ = ("_t",)

    def __init__(self, val: T):
        self._t = val

    # def is_ok(self):
    #     return _tg_is_ok(self)

    # def is_err(self):
    #     return _tg_is_not_err(self)

    def __repr__(self):
        return f"Ok({self._t})"


class Err[T, E](_Result[T, E]):
    _OK = False
    __match_args__ = ("_e",)

    def __init__(self, val: E):
        self._e = val

    # def is_ok(self):
    #     return _tg_is_not_ok(self)

    # def is_err(self):
    #     return _tg_is_err(self)

    def __repr__(self):
        return f"Err({self._e})"


type Result[T, E] = Ok[T, E] | Err[T, E]


class _Option[T]:
    _t: T
    _OK: bool
    __match_args__: tuple[str] | None

    __slots__ = tuple("_t")

    def is_some(self):
        return self._OK

    def is_some_and(self, f: F[T, bool]):
        return self._OK and f(self._t)

    def is_none(self):
        return not self._OK

    def is_none_or(self, f: F[T, bool]):
        return (not self._OK) or f(self._t)

    def expect(self, msg: str):
        if self._OK:
            return self._t

        raise Exception(msg)

    def unwrap(self):
        if self._OK:
            return self._t

        raise Exception("unwrap called on Nothing")

    def unwrap_or(self, d: T) -> T:
        return self._OK and self._t or d

    def unwrap_or_else(self, f: F[T]) -> T:
        return self._OK and self._t or f()

    def map[U](self, f: F[T, U]) -> Option[U]:
        if self._OK:
            return Some(f(self._t))

        return Nothing

    def inspect(self, f: Callable[[T], None]) -> Option[T]:
        if self._OK:
            f(self._t)
        return self

    def map_or[U](self, d: U, f: F[T, U]) -> U:
        if self._OK:
            return f(self._t)

        return d

    def map_or_else[U](self, d: F[U], f: F[T, U]) -> U:
        if self._OK:
            return f(self._t)

        return d()

    def ok_or[E](self, err: E) -> Result[T, E]:
        if self._OK:
            return Ok(self._t)
        return Err(err)

    def ok_or_else[E](self, err: F[E]) -> Result[T, E]:
        if self._OK:
            return Ok(self._t)

        return Err(err())

    def and_[U](self, o: Option[U]) -> Option[U]:
        if self._OK:
            return o

        return Nothing

    def and_then[U](self, f: F[T, Option[U]]) -> Option[U]:
        if self._OK:
            return f(self._t)

        return Nothing

    def filter(self, pred: F[T, bool]) -> Option[T]:
        if self._OK:
            return pred(self._t) and Some(self._t) or Nothing

        return Nothing

    def or_(self, o: Option[T]) -> Option[T]:
        if self._OK:
            return self

        return o

    def or_else(self, f: F[Option[T]]) -> Option[T]:
        if self._OK:
            return self

        return f()

    def xor(self, o: Option[T]) -> Option[T]:
        if self.is_some() and o.is_none():
            return self

        if self.is_none() and o.is_some():
            return o

        return Nothing

    def zip[U](self, o: Option[U]) -> Option[tuple[T, U]]:
        if self.is_some() and o.is_some():
            return Some((self.unwrap(), o.unwrap()))

        return Nothing


class Some[T](_Option[T]):
    _OK = True
    __match_args__ = ("_t",)

    def __init__(self, val: T):
        self._t = val

    def __repr__(self):
        return f"Some({self._t})"


@type.__call__
class Nothing(_Option[None]):
    _OK = False
    __match_args__ = None

    def __repr__(self):
        return "Nothing"


type Option[T] = Some[T] | Nothing
