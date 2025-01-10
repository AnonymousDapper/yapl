# MIT License
#
# Copyright (c) 2025 AnonymousDapper

from __future__ import annotations

__all__ = (
    "parse_string",
    "Parser",
    "StringParserInput",
    "ParseResult",
    "print_result",
    "defer",
    "many",
    "defer",
    "pure",
    "seq",
    "literal",
    "any_",
    "one_of",
    "none_of",
    "eof",
    "between",
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
    "Result",
    "Ok",
    "Err",
    "Option",
    "Some",
    "Nothing",
)

from .parsing import *
from .utils import *


def parse_string[a](p: Parser[str, a]):
    def inner(s: str):
        r = p.run(StringParserInput(s))
        return print_result(r)

    return inner
