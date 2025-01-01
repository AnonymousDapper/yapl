# MIT License
#
# Copyright (c) 2025 AnonymousDapper

from __future__ import annotations

from typing import Callable, Concatenate

type F[*P, R] = Callable[[*P], R]

def partial[**Ps,T,R](f: Callable[Concatenate[T,Ps], R], v: T) -> Callable[Ps,R]:
    def inner(*a: Ps.args, **k: Ps.kwargs):
        return f(v, *a, **k)

    return inner

def curry1[a,R](f: F[a,R]) -> F[a, R]:
    return f

def curry2[a,b,R](f: F[a,b,R]) -> F[a, F[b, R]]:
    def inner(a):
        return partial(f, a)

    return inner

def curry3[a,b,c,R](f: F[a,b,c,R]) -> F[a, F[b, F[c, R]]]:
    def outer(a: a):
        def inner(b: b):
            return partial(partial(f, a), b)

        return inner

    return outer

def curry4[a,b,c,d,R](f: F[a,b,c,d,R]) -> F[a, F[b, F[c, F[d, R]]]]:
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

def zp[a,b](ls: list[a], rs: list[b]) -> list[tuple[a, b]]:
    return list(zip(ls, rs))

def first[a,b](t: tuple[a,b]) -> a:
    (a, b) = t
    return a

def second[a,b](t: tuple[a,b]) -> b:
    (a, b) = t
    return b

def cons[a](v: a, ls: list[a]) -> list[a]:
    return [v] + ls

def compose[a,b,c](l: F[b,c], r: F[a,b]) -> F[a,c]:
    return lambda *a: l(r(*a))

def reduce[a](f: F[a,a,a], arr: list[a]):
    [initial, *rst] = arr
    for x in rst:
        initial = f(initial, x)

    return initial

def take_while[a](f: F[a,bool], lst: list[a]) -> list[a]:
    i = 1
    while f(lst[0:i][-1]):
        i += 1

    return lst[0:i-1]

def drop_while[a](f: F[a,bool], lst: list[a]) -> list[a]:
    i = 0
    l = len(lst)
    while f(lst[i:][0]):
        i += 1
        if i == l: break

    return lst[min(i,l):]



class Result[T,E]:
    _t: T
    _e: E
    __OK: bool
    __match_args__: tuple[str]

    def is_ok(self):
        return self.__OK

    def is_ok_and(self, f: F[T,bool]):
        return self.__OK and f(self._t)

    def is_err(self):
        return not self.__OK

    def is_err_and(self, f: F[E,bool]):
        return (not self.__OK) and f(self._e)

    def ok(self) -> Option[T]:
        return self.__OK and Some(self._t) or Nothing

    def err(self) -> Option[E]:
        return (not self.__OK) and Some(self._e) or Nothing

    def map[U](self, f: F[T,U]) -> Result[U,E]:
        return self.__OK and Ok(f(self._t)) or Err(self._e)

    def map_or[U](self, d: U, f: F[T,U]) -> U:
        return self.__OK and f(self._t) or d

    def map_or_else[U](self, d: F[E,U], f: F[T,U]) -> U:
        return self.__OK and f(self._t) or d(self._e)

    def map_err[U](self, f: F[E,U]) -> Result[T,U]:
        return (not self.__OK) and Err(f(self._e)) or Ok(self._t)

    def inspect(self, f: Callable[[T], None]) -> Result[T,E]:
        if self.__OK: f(self._t)
        return self

    def inspect_err(self, f: Callable[[E], None]) -> Result[T,E]:
        if not self.__OK: f(self._e)
        return self

    def expect(self, msg: str):
        if self.__OK:
            return self._t
        else:
            raise Exception(msg)

    def unwrap(self):
        if self.__OK:
            return self._t
        else:
            raise Exception(self._e)

    def expect_err(self, msg: str):
        if not self.__OK:
            return self._e

        else:
            raise Exception(msg)

    def unwrap_err(self):
        if not self.__OK:
            return self._e
        else:
            raise Exception(self._t)

    def and_[U](self, res: Result[U,E]) -> Result[U,E]:
        if self.__OK:
            return res

        return Err(self._e)

    def and_then[U](self, f: F[T, Result[U,E]]) -> Result[U,E]:
        if self.__OK:
            return f(self._t)

        return Err(self._e)

    def or_[U](self, res: Result[T,U]) -> Result[T,U]:
        if not self.__OK:
            return res

        return Ok(self._t)

    def or_else[U](self, f: F[E, Result[T,U]]) -> Result[T,U]:
        if not self.__OK:
            return f(self._e)

        return Ok(self._t)

    def unwrap_or(self, d: T) -> T:
        return self.__OK and self._t or d

    def unwrap_or_else(self, f: F[E,T]) -> T:
        return self.__OK and self._t or f(self._e)


class Ok[T,E](Result[T,E]):
    __OK = True
    __match_args__ = ("_t",)

    def __init__(self, val: T):
        self._t = val

class Err[T,E](Result[T,E]):
    __OK = False
    __match_args__ = ("_e",)

    def __init__(self, val: E):
        self._e = val


class Option[T]:
    _t : T
    __OK: bool
    __match_args__: tuple[str] | None

    def is_some(self):
        return self.__OK

    def is_some_and(self, f: F[T,bool]):
        return self.__OK and f(self._t)

    def is_none(self):
        return not self.__OK

    def is_none_or(self, f: F[T,bool]):
        return (not self.__OK) or f(self._t)

    def expect(self, msg: str):
        if self.__OK:
            return self._t

        raise Exception(msg)

    def unwrap(self):
        if self.__OK:
            return self._t

        raise Exception("unwrap called on Nothing")

    def unwrap_or(self, d: T) -> T:
        return self.__OK and self._t or d

    def unwrap_or_else(self, f: F[T]) -> T:
        return self.__OK and self._t or f()

    def map[U](self, f: F[T,U]) -> Option[U]:
        if self.__OK:
            return Some(f(self._t))

        return Nothing

    def inspect(self, f: Callable[[T], None]) -> Option[T]:
        if self.__OK: f(self._t)
        return self

    def map_or[U](self, d: U, f: F[T,U]) -> U:
        if self.__OK:
            return f(self._t)

        return d

    def map_or_else[U](self, d: F[U], f: F[T,U]) -> U:
        if self.__OK:
            return f(self._t)

        return d()

    def ok_or[E](self, err: E) -> Result[T,E]:
        if self.__OK:
            return Ok(self._t)
        return Err(err)

    def ok_or_else[E](self, err: F[E]) -> Result[T,E]:
        if self.__OK:
            return Ok(self._t)

        return Err(err())

    def and_[U](self, o: Option[U]) -> Option[U]:
        if self.__OK:
            return o

        return Nothing

    def and_then[U](self, f: F[T,Option[U]]) -> Option[U]:
        if self.__OK:
            return f(self._t)

        return Nothing

    def filter(self, pred: F[T,bool]) -> Option[T]:
        if self.__OK:
            return pred(self._t) and Some(self._t) or Nothing

        return Nothing

    def or_(self, o: Option[T]) -> Option[T]:
        if self.__OK:
            return self

        return o

    def or_else(self, f: F[Option[T]]) -> Option[T]:
        if self.__OK:
            return self

        return f()

    def xor(self, o: Option[T]) -> Option[T]:
        if self.is_some() and o.is_none():
            return self

        if self.is_none() and o.is_some():
            return o

        return Nothing

    def insert(self, v: T) -> T:
        self._t = v
        self.__OK = True
        return v

    def get_or_insert(self, v: T) -> T:
        if self.__OK:
            return self._t

        return self.insert(v)

    def get_or_insert_with(self, f: F[T]) -> T:
        if self.__OK:
            return self._t

        self._t = f()
        self.__OK = True
        return self._t

    def take(self) -> Option[T]:
        if self.__OK:
            self._t = None # type: ignore
            self.__OK = False

        return self

    def take_if(self, pred: F[T,bool]) -> Option[T]:
        if self.__OK and pred(self._t):
            self._t = None # type: ignore
            self.__OK = False

        return self

    def zip[U](self, o: Option[U]) -> Option[tuple[T,U]]:
        if self.is_some() and o.is_some():
            return Some((self.unwrap(), o.unwrap()))

        return Nothing


class Some[T](Option[T]):
    __OK = True
    __match_args__ = ("_t",)

    def __init__(self, val: T):
        self._t = val

@type.__call__
class Nothing[T](Option[T]):
    __OK = False
    __match_args__ = None

