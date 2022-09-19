import inspect
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from random import sample
from typing import Sequence

from rich import print  # type: ignore

HERE = Path(__file__).resolve().parent
properties_file = HERE / "compiler.properties"
assert properties_file.exists()

properties_text = properties_file.read_text(encoding="UTF-8")


@dataclass(frozen=True)
class Placeholder:
    """
    A placeholder within a message.
    """

    index: int
    type_: str | None
    comment: str | None

    def __str__(self) -> str:
        # Didn't use f-string because the {{{_}}} gets confusing.
        return "{" + str(self.index) + "}"


@dataclass
class Message:
    """
    A possible message declared in javac's compiler.properties file.
    """

    name: str
    components: Sequence[Placeholder | str]

    @property
    def level(self) -> str:
        return self.name.split(".")[1]

    @property
    def is_error_message(self) -> bool:
        return self.name.startswith("compiler.err.")

    def __str__(self) -> str:
        return "".join(str(item) for item in self.components)


class ParseError(Exception):
    def __init__(self, *, line_no: int, line: str, production: str, message: str):
        self.line_no = line_no
        self.message = message
        self.production = production
        self.message = message
        self.line = line

    def __str__(self):
        filename = properties_file.name
        return (
            f"{filename}:{self.line_no}: {self.message}\n"
            "\n"
            f"  {self.line_no} | {self.line}"
            "\n"
            f"(while in {self.production})"
        )


# Parse some messages!
class Parser:
    def __init__(self, lines: Sequence[str]):
        self.lines = enumerate(lines, start=1)
        self.line_no, self.raw_line = next(self.lines)
        self.parsing = True
        self.messages: list[Message] = []
        self.current_comment_lines: list[str] = []

    @property
    def line(self) -> str:
        line = self.raw_line.rstrip()

        def unescape_unicode(m):
            # TODO: there might be some surrogate pair shenanigans...
            return chr(int(m[1], 16))

        return re.sub(r"\\u([0-9a-zA-Z]{4})", unescape_unicode, line)

    def parse(self):
        while True:
            self.item()
            try:
                self.next_line()
            except StopIteration:
                break

    def next_line(self):
        self.line_no, self.raw_line = next(self.lines)

    def item(self):
        if self.line.startswith("#"):
            self.comment()
        elif self.line == "":
            # Empty line. Clear the current comment.
            self.current_comment_lines = []
        elif self.line[0].isalpha():
            # A message without an annotation
            self.message()
        else:
            self.parse_error()

    def comment(self):
        """
        Parsing either an "annotation":

        # 0: type

        or a regular comment like

        # hello
        """
        self.current_comment_lines.append(self.line)

    def message(self):
        """
        Parse a property like:

            compiler.error.syntax=syntax error
        """
        name, sep, rest = self.line.partition("=")

        if sep != "=":
            raise self.parse_error("expected `property=` here")

        # A few names have spaces around the property name.
        name = name.strip()

        if rest.endswith("\\"):
            self.next_line()
            value = self.value()
        else:
            value = [rest]

        self.messages.append(Message(name=name, components=self.make_components(value)))
        self.current_comment_lines = []

    def value(self) -> str:
        """
        Parsing a property value, i.e., the part after equals.

        Example:

            container {0} is not applicable to element {1}

        Note: this only extracts the text. It does not process the placeholders.
        """

        value_chunks = []

        has_continuation = True
        while has_continuation:
            chunk = self.line.lstrip().removesuffix("\\")

            def replace_escape(match_):
                match match_[1]:
                    case "n":
                        return "\n"
                    case "t":
                        return "\t"
                    case "'":
                        return "'"
                    case '"':
                        return '"'
                    case _:
                        full_escape = match_[0]
                        raise self.parse_error(f"Unknown escape: {full_escape}")

            chunk = re.sub(r"\\(.)", replace_escape, chunk)

            value_chunks.append(chunk)
            has_continuation = self.line.endswith("\\")
            try:
                self.next_line()
            except StopIteration:
                break
        return "".join(value_chunks)

    def make_components(self, message_text: str) -> Sequence[str | Placeholder]:
        """
        Parses out message components:
            - either literal text; or
            - a numbered placeholder

        Placeholders may have types, which are declared in a comment above the message.
        """

        types = parse_annotation(self.current_comment_lines)
        components: list[Placeholder | str] = []

        placeholder_pattern = re.compile(r"{(\d+)}")

        last_fencepost = 0
        for match in placeholder_pattern.finditer(message_text):
            index = int(match[1])

            try:
                placeholder = types[index]
            except KeyError:
                warning(
                    f"could not find placeholder {{{index}}} in [dim italic]{message_text}[/dim italic]"
                )
                placeholder = Placeholder(index, None, None)

            before_placeholder = message_text[last_fencepost : match.start()]
            components.append(before_placeholder)
            components.append(placeholder)
            last_fencepost = match.end()

        last_bit = message_text[last_fencepost:]
        if last_bit != "":
            components.append(last_bit)

        return components

    def parse_error(self, message=None):
        """
        Helper to create a nice parse error.
        """
        name = inspect.stack()[1].function
        return ParseError(
            line_no=self.line_no,
            line=self.line,
            production=name,
            message=message or "Parse error",
        )


def parse_annotation(lines: Sequence[str]) -> dict[int, Placeholder]:
    """
    Parse annotation comments. These are things that look like this:

        # 0: option name, 1: symbol

    Sometimes they look like this:

        # {0} - current module
        # {1} - package in which the invisible class is declared
        # {2} - module in which {1} is declared
        # 0: symbol, 1: symbol, 2: symbol

    Sometimes they're not even annonations:

        # TODO 308: make a better error message

    Regardless, this function will always a dictionary that maps the index to a Placeholder.
    If at any point the comment looks malformed, this will return an empty dictionary
    and emit a warning.
    """

    if len(lines) == 0:
        # No placeholder type annotations to be found!
        return {}

    # TODO: add support for annotation comments

    # Only the last line has annotations
    annotation_line = lines[-1].removeprefix("#").lstrip()

    if ":" not in annotation_line:
        warning("not interpreting this as an annotation:", lines)
        return {}

    types = {}
    for declaration in annotation_line.split(","):
        declaration = declaration.strip()
        str_index, separator, description = declaration.partition(":")
        if separator != ":":
            warning("ignorning malformed annotation line:", annotation_line)
            return {}

        try:
            index = int(str_index)
        except ValueError:
            warning("does not look like an annotation:", annotation_line)
            return {}

        if index in types:
            warning("duplicate index {index} in annotation line:", annotation_line)

        types[index] = Placeholder(index, description.strip(), None)

    return types


def warning(*args, **kwargs):
    print("[bold yellow]Warning[/bold yellow]:", *args, **kwargs, file=sys.stderr)


if __name__ == "__main__":
    p = Parser(properties_text.splitlines())
    p.parse()
    print("[bold]Showing 10 random messages[/bold]:")
    for message in sample(p.messages, k=10):
        print(message.name, message, str(message))

    n_errors = sum(m.is_error_message for m in p.messages)
    total = len(p.messages)
    print(f"[bold]{n_errors}[/bold] error messages ({total} total)")
