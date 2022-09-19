from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Sequence

HERE = Path(__file__).resolve().parent
properties_file = HERE / "compiler.properties"
assert properties_file.exists()

properties_text = properties_file.read_text(encoding="UTF-8")


@dataclass(frozen=True)
class Placeholder:
    index: int

    def __str__(self):
        return "{" + int(self.index) + "}"


@dataclass
class Message:
    raw_text: str
    _components: Sequence[Placeholder | str]

    def __str__(self):
        return "".join(str(item) for item in self.components)


class ParseError(Exception):
    def __init__(self, line_no: int, message: str):
        self.line_no = line_no
        self.message = message

    def __str__(self):
        return f"line {self.line_no}: {self.message}"


# Parse some messages!

messages: list[Message] = []
comment_buffer: list[str] = []
current_value = []

parsing = True


class State:
    LOOKING_FOR_ITEM = "looking for any item"
    PARSING_VALUE = "parsing a value"
    PARSING_COMMENT = "parsing a comment"


state = State.LOOKING_FOR_ITEM

for line_no, line in enumerate(properties_text.splitlines(), start=1):
    line = line.rstrip()

    match state:
        case State.LOOKING_FOR_ITEM | State.PARSING_COMMENT:
            if line.startswith("#"):
                comment_buffer.append(line)
                state = State.PARSING_COMMENT
            elif line == "":
                comment_buffer = []
            elif line[0].isalpha():
                # Found a property, like:
                #
                #  compiler.error.syntax=syntax error
                name, sep, rest = line.partition("=")

                if name.strip() != name:
                    raise ParseError(
                        line_no, f"found spaces around property name: {line}"
                    )
                if sep != "=":
                    raise ParseError(
                        line_no, f"Expected property= but instead got: {line}"
                    )

                if rest.endswith("\\"):
                    state = State.PARSING_VALUE
                else:
                    state = State.LOOKING_FOR_ITEM
                    raise NotImplementedError("one line message")
            else:
                raise ParseError(line_no, f"Unexpected line: {line!r}")
        case State.PARSING_VALUE:
            if line == "":
                state = State.LOOKING_FOR_ITEM
            elif line[0].isspace():
                assert not line[-1].isspace()
                current_value.append(line)
            else:
                current_value.append(line)
        case _:
            raise ParseError(line_no, f"Unhandled state: {state}")

print("done")
