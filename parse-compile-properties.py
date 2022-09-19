import inspect
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

HERE = Path(__file__).resolve().parent
properties_file = HERE / "compiler.properties"
assert properties_file.exists()

properties_text = properties_file.read_text(encoding="UTF-8")


@dataclass(frozen=True)
class Placeholder:
    index: int
    type_: str
    comment: str

    def __str__(self):
        # Didn't use f-string because the {{{_}}} gets confusing.
        return "{" + int(self.index) + "}"


@dataclass
class Message:
    name: str
    components: Sequence[Placeholder | str]

    def __str__(self):
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
        return self.raw_line.rstrip()

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
        Parsing a property value, i.e., the part after equals

            conatiner {0} is not applicable to element {1}
        """

        value_chunks = []

        has_continuation = True
        while has_continuation:
            chunk = self.line.lstrip().removesuffix("\\")
            value_chunks.append(chunk)
            has_continuation = self.line.endswith("\\")
            try:
                self.next_line()
            except StopIteration:
                break
        return "".join(value_chunks)

    def make_components(self, message_text: str) -> Sequence[str | Placeholder]:
        """
        Uh.... hard to explain
        """

        types = parse_annotation(self.current_comment_lines)
        # TODO: this entire function
        return [message_text]

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
    Parse annotations. Annotations might have comments.
    """

    if len(lines) == 0:
        # No placeholder type annotations to be found!
        return {}

    # Only the last line has annotations
    annotation_line = lines[-1]

    if ":" not in annotation_line:
        print("Warning: not interpreting this as an annotation:", lines)
        return {}

    # TODO: do the actual parsing
    print(annotation_line)

    return {}


p = Parser(properties_text.splitlines())
p.parse()
for message in p.messages:
    print(message.name, message)
