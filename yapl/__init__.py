# MIT License
#
# Copyright (c) 2025 AnonymousDapper

# pyright: reportImplicitOverride=false

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
    "Err",
    "fail_with",
    "is_err",
    "is_none",
    "is_ok",
    "is_some",
    "left",
    "lift2",
    "literal",
    "many",
    "many1",
    "map_",
    "newline",
    "none_of",
    "Nothing",
    "Ok",
    "one_of",
    "opt",
    "Option",
    "or_",
    "parse_string",
    "Parser",
    "ParserError",
    "ParseResult",
    "ParserInput",
    "ParserValue",
    "pure",
    "regex",
    "regex_captures",
    "Result",
    "right",
    "sep_by",
    "sep_by1",
    "seq",
    "Some",
    "space",
    "spaces",
    "string_",
    "StringParserInput",
    "succeed_with",
    "times",
)


from yapl import parser

from .functional import *
from .parser import *


def parse_string[a](p: Parser[str, a]):
    def inner(s: str):
        parser._COUNT = iter(parser.itertools.count())
        r = p.run(StringParserInput(s))
        match r:
            case Ok(v):
                print(f"Success: {v.item!r}")
                print(f"{next(parser._COUNT)-1} cycles")

            case Err(e):
                e.print_err()

    return inner
