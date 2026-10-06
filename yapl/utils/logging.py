# MIT License
#
# Copyright (c) 2025 AnonymousDapper

# pyright: reportImplicitOverride=false

import inspect
import os
from enum import IntEnum
from typing import Protocol


class IntoStr(Protocol):
    def __str__(self) -> str: ...


DEBUG: bool = os.environ.get("YAPL_DEBUG") == "1"


class Color(IntEnum):
    Black = 30
    Red = 31
    Green = 32
    Yellow = 33
    Blue = 34
    Magenta = 35
    Cyan = 36
    White = 37

    AltBlack = 90
    AltRed = 91
    AltGreen = 92
    AltYellow = 93
    AltBlue = 94
    AltMagenta = 95
    AltCyan = 96
    AltWhite = 97


class Logger:
    __slots__ = ("module_name", "text_color", "background_color")
    module_name: str
    text_color: Color
    background_color: Color

    def __init__(self, module_name: str, text_color: Color, background_color: Color):
        self.module_name = module_name
        self.text_color = text_color
        self.background_color = background_color

    def log(self, *args: IntoStr):
        if DEBUG:
            framei = inspect.stack()[1]
            f_name = framei.function
            lineno = framei.lineno

            f_context = framei.frame.f_locals.get(  # pyright: ignore[reportAny]
                "_log_context_", f"<{f_name}>"
            )
            f_text = framei.frame.f_locals.get(
                "_log_color_", self.text_color
            )  # pyright: ignore[reportAny]

            f_bg = framei.frame.f_locals.get(
                "_log_background_", self.background_color
            )  # pyright: ignore[reportAny]

            assert isinstance(f_context, str)

            assert isinstance(f_text, Color)
            assert isinstance(f_bg, Color)

            del framei

            print(
                f"\033[{f_bg + 10};{f_text}m[ {f_context}:{lineno} ]\033[0m {'\t'.join(str(a) for a in args)}"
            )


def get_logger(*, text: Color = Color.AltWhite, background: Color = Color.Black):
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame.frame)

    module_name = module and module.__name__ or "<unknown>"

    del frame
    del module

    return Logger(module_name, text, background)
