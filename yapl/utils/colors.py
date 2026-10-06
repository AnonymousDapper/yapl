# MIT License
#
# Copyright (c) 2025 AnonymousDapper
#

from __future__ import annotations

from typing import Any, SupportsIndex

__all__ = "Colorize", "Style", "Styles", "Color"

from collections import namedtuple
from enum import Enum
from functools import wraps
from re import finditer

TrueColor = namedtuple("TrueColor", "r g b")

StyleFlagData = namedtuple("StyleFlagData", "mask value")


class Styles(Enum):
    """
    VT seqences for styling
    """

    Clear = StyleFlagData(0, "")
    Bold = StyleFlagData(1, "1")
    Dimmed = StyleFlagData(64, "2")
    Italic = StyleFlagData(8, "3")
    Underline = StyleFlagData(2, "4")
    Blink = StyleFlagData(16, "5")
    Reversed = StyleFlagData(4, "7")
    Hidden = StyleFlagData(32, "8")
    Strikethrough = StyleFlagData(128, "7")

    @classmethod
    def from_int(cls, value):
        if value != 0:
            styles = tuple(filter(lambda s: value & s.value.mask, Styles))

            if styles:
                return styles

        return None

    def to_int(self) -> int:
        return self.value.mask

    def to_str(self) -> str:
        return self.value.value


class Style:
    style: int

    def __init__(self, style: Styles):
        self.style = style.to_int()

    def contains(self, style: Styles) -> bool:
        return style in self

    def add(self, other: Styles):
        self += other

    def __contains__(self, item: Styles) -> bool:
        if isinstance(item, Styles):
            val = item.to_int()

            return self.style & val == val

        return NotImplemented

    def __iadd__(self, other: Styles):
        if isinstance(other, Styles):
            self.style |= other.value.mask
            return self

        return NotImplemented

    def __eq__(self, other) -> bool:
        if isinstance(other, Styles):
            return self.style == other.to_int()

        return NotImplemented

    def __str__(self):
        styles = Styles.from_int(self.style)

        if styles:
            return ";".join(map(Styles.to_str, styles))

        return Styles.Clear.to_str()


class Color(Enum):
    """
    VT sequences for coloring
    """

    Black = 0
    Red = 1
    Green = 2
    Yellow = 3
    Blue = 4
    Magenta = 5
    Cyan = 6
    White = 7

    BrightBlack = 60
    BrightRed = 61
    BrightGreen = 62
    BrightYellow = 63
    BrightBlue = 64
    BrightMagenta = 65
    BrightCyan = 66
    BrightWhite = 67

    TrueColor = TrueColor

    @classmethod
    def true_color(cls, color) -> Color:
        self = cls.TrueColor

        setattr(self, "color", color)

        return self

    def fg(self):
        if self != Color.TrueColor:
            return str(self.value + 30)
        else:
            return f"38;2;{self.color.r};{self.color.g};{self.color.b}"  # type: ignore

    def bg(self):
        if self != Color.TrueColor:
            return str(self.value + 40)
        else:
            return f"48;2;{self.color.r};{self.color.g};{self.color.b}"  # type: ignore


class Colorize:
    def __init__(
        self,
        text,
        *,
        fg_color: Color | None = None,
        bg_color: Color | None = None,
        style: Style | None = None,
    ):
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.style = style or Style(Styles.Clear)
        self.inner: str = str(text)

    def is_plain(self) -> bool:
        return (
            self.fg_color is None
            and self.bg_color is None
            and self.style == Styles.Clear
        )

    def _from(self, text: str) -> Colorize:
        return Colorize(
            text, fg_color=self.fg_color, bg_color=self.bg_color, style=self.style
        )

    def compute_style(self) -> str:
        if self.is_plain():
            return ""

        buf = ["\x1B["]
        wrote = False

        if self.style != Styles.Clear:
            buf.append(str(self.style))
            wrote = True

        if self.bg_color is not None:
            if wrote:
                buf.append(";")

            buf.append(self.bg_color.bg())
            wrote = True

        if self.fg_color is not None:
            if wrote:
                buf.append(";")

            buf.append(self.fg_color.fg())

        buf.append("m")
        return "".join(buf)

    def escape_inner_resets(self) -> str:
        if self.is_plain():
            return self.inner

        reset = "\x1B\\[0m"
        r_len = 4

        style = self.compute_style()

        matches = tuple(m.start() for m in finditer(reset, self.inner))

        if not matches:
            return self.inner

        tmp = list(self.inner)

        for idx, offset in enumerate(matches):
            offset = offset + r_len + idx * len(style)

            for c in style:
                tmp.insert(offset, c)
                offset += 1

        return "".join(tmp)

    def __repr__(self):
        return repr(str(self))

    def __str__(self):
        if self.is_plain():
            return self.inner

        return f"{self.compute_style()}{self.escape_inner_resets()}\x1B[0m"

    def capitalize(self):
        self.inner = self.inner.capitalize()
        return self

    def casefold(self):
        self.inner = self.inner.casefold()
        return self

    def center(self, *args):
        self.inner = self.inner.center(*args)
        return self

    def count(self, *args):
        return self.inner.count(*args)

    def endswith(self, *args):
        return self.inner.endswith(*args)

    def expandtabs(self, *args, **kwargs):
        self.inner = self.inner.expandtabs(*args, **kwargs)
        return self

    def find(self, *args):
        return self.inner.find(*args)

    def format(self, *args, **kwargs):
        self.inner = self.inner.format(*args, **kwargs)
        return self

    def format_map(self, mapping):
        self.inner = self.inner.format_map(mapping)
        return self

    def index(self, *args):
        return self.inner.index(*args)

    def isalnum(self):
        return self.inner.isalnum()

    def isalpha(self):
        return self.inner.isalpha()

    def isascii(self):
        return self.inner.isascii()

    def isdecimal(self):
        return self.inner.isdecimal()

    def isdigit(self):
        return self.inner.isdigit()

    def isidentifier(self):
        return self.inner.isidentifier()

    def islower(self):
        return self.inner.islower()

    def isnumeric(self):
        return self.inner.isnumeric()

    def isprintable(self):
        return self.inner.isprintable()

    def isspace(self):
        return self.inner.isspace()

    def istitle(self):
        return self.inner.istitle()

    def isupper(self):
        return self.inner.isupper()

    def join(self, _iter):
        self.inner = self.inner.join(_iter)
        return self

    def ljust(self, *args):
        self.inner = self.inner.ljust(*args)
        return self

    def lower(self):
        self.inner = self.inner.lower()
        return self

    def lstrip(self, *args):
        self.inner = self.inner.lstrip(*args)
        return self

    def partition(self, *args):
        res = self.inner.partition(*args)
        return list(map(self._from, res))

    def removeprefix(self, *args):
        self.inner = self.inner.removeprefix(*args)
        return self

    def removesuffix(self, *args):
        self.inner = self.inner.removesuffix(*args)
        return self

    def replace(self, *args):
        self.inner = self.inner.replace(*args)
        return self

    def rfind(self, *args):
        return self.inner.rfind(*args)

    def rindex(self, *args):
        return self.inner.rindex(*args)

    def rjust(self, *args):
        self.inner = self.inner.rjust(*args)
        return self

    def rpartition(self, *args):
        res = self.inner.rpartition(*args)
        return list(map(self._from, res))

    def rsplit(self, *args, **kwargs):
        return self.inner.rsplit(*args, **kwargs)

    def rstrip(self, *args):
        self.inner = self.inner.rstrip(*args)
        return self

    def split(self, *args, **kwargs):
        return self.inner.split(*args, **kwargs)

    def splitlines(self, *args, **kwargs):
        return self.inner.splitlines(*args, **kwargs)

    def startswith(self, *args):
        return self.inner.startswith(*args)

    def strip(self, *args):
        self.inner = self.inner.strip(*args)
        return self

    def swapcase(self):
        self.inner = self.inner.swapcase()
        return self

    def title(self):
        self.inner = self.inner.title()
        return self

    def translate(self, *args):
        self.inner = self.inner.translate(*args)
        return self

    def upper(self):
        self.inner = self.inner.upper()
        return self

    def zfill(self, *args):
        self.inner = self.inner.zfill(*args)
        return self

    def __format__(self, spec: str):
        new = self._from(self.inner.__format__(spec))
        return str(new)

    def __add__(self, other: str):
        return str(self).__add__(other)

    def __contains__(self, other: str):
        return self.inner.__contains__(other)

    def __eq__(self, other: object):
        return self.inner.__eq__(other)

    def __ge__(self, other: str):
        return self.inner.__ge__(other)

    def __getitem__(self, other: SupportsIndex | slice[Any, Any, Any]):
        return self._from(self.inner.__getitem__(other))

    def __gt__(self, other: str):
        return self.inner.__gt__(other)

    def __hash__(self):
        return self.inner.__hash__()

    def __iter__(self):
        return iter(self._from(char) for char in self.inner.__iter__())

    def __le__(self, other: str):
        return self.inner.__le__(other)

    def __len__(self):
        return self.inner.__len__()

    def __lt__(self, other: str):
        return self.inner.__lt__(other)

    def __mod__(self, other: Any):
        return self._from(self.inner.__mod__(other))

    def __mul__(self, other: SupportsIndex):
        return self._from(self.inner.__mul__(other))

    def __ne__(self, other: object):
        return self.inner.__ne__(other)

    def color(self, color: Color) -> Colorize:
        self.fg_color = color
        return self

    def on_color(self, color: Color) -> Colorize:
        self.bg_color = color
        return self

    def clear(self) -> Colorize:
        return Colorize(self.inner)

    def bold(self) -> Colorize:
        self.style += Styles.Bold
        return self

    def dimmed(self) -> Colorize:
        self.style += Styles.Dimmed
        return self

    def italic(self) -> Colorize:
        self.style += Styles.Italic
        return self

    def underline(self) -> Colorize:
        self.style += Styles.Underline
        return self

    def blink(self) -> Colorize:
        self.style += Styles.Blink
        return self

    def reversed(self) -> Colorize:
        self.style += Styles.Reversed
        return self

    def hidden(self) -> Colorize:
        self.style += Styles.Hidden
        return self

    def strikethrough(self) -> Colorize:
        self.style += Styles.Strikethrough
        return self

    def black(self) -> Colorize:
        return self.color(Color.Black)

    def red(self) -> Colorize:
        return self.color(Color.Red)

    def green(self) -> Colorize:
        return self.color(Color.Green)

    def yellow(self) -> Colorize:
        return self.color(Color.Yellow)

    def blue(self) -> Colorize:
        return self.color(Color.Blue)

    def magenta(self) -> Colorize:
        return self.color(Color.Magenta)

    def cyan(self) -> Colorize:
        return self.color(Color.Cyan)

    def white(self) -> Colorize:
        return self.color(Color.White)

    def bright_black(self) -> Colorize:
        return self.color(Color.BrightBlack)

    def bright_red(self) -> Colorize:
        return self.color(Color.BrightRed)

    def bright_green(self) -> Colorize:
        return self.color(Color.BrightGreen)

    def bright_yellow(self) -> Colorize:
        return self.color(Color.BrightYellow)

    def bright_blue(self) -> Colorize:
        return self.color(Color.BrightBlue)

    def bright_magenta(self) -> Colorize:
        return self.color(Color.BrightMagenta)

    def bright_cyan(self) -> Colorize:
        return self.color(Color.BrightCyan)

    def bright_white(self) -> Colorize:
        return self.color(Color.BrightWhite)

    def truecolor(self, r: int, b: int, g: int) -> Colorize:
        return self.color(Color.true_color(TrueColor(r, g, b)))

    def on_black(self) -> Colorize:
        return self.on_color(Color.Black)

    def on_red(self) -> Colorize:
        return self.on_color(Color.Red)

    def on_green(self) -> Colorize:
        return self.on_color(Color.Green)

    def on_yellow(self) -> Colorize:
        return self.on_color(Color.Yellow)

    def on_blue(self) -> Colorize:
        return self.on_color(Color.Blue)

    def on_magenta(self) -> Colorize:
        return self.on_color(Color.Magenta)

    def on_cyan(self) -> Colorize:
        return self.on_color(Color.Cyan)

    def on_white(self) -> Colorize:
        return self.on_color(Color.White)

    def on_bright_black(self) -> Colorize:
        return self.on_color(Color.BrightBlack)

    def on_bright_red(self) -> Colorize:
        return self.on_color(Color.BrightRed)

    def on_bright_green(self) -> Colorize:
        return self.on_color(Color.BrightGreen)

    def on_bright_yellow(self) -> Colorize:
        return self.on_color(Color.BrightYellow)

    def on_bright_blue(self) -> Colorize:
        return self.on_color(Color.BrightBlue)

    def on_bright_magenta(self) -> Colorize:
        return self.on_color(Color.BrightMagenta)

    def on_bright_cyan(self) -> Colorize:
        return self.on_color(Color.BrightCyan)

    def on_bright_white(self) -> Colorize:
        return self.on_color(Color.BrightWhite)

    def on_truecolor(self, r: int, b: int, g: int) -> Colorize:
        return self.on_color(Color.true_color(TrueColor(r, g, b)))
