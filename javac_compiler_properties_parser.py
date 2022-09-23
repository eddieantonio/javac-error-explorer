"""
Parses messages from javac's `compiler.properties` file.
"""

import inspect
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from random import sample
from typing import Iterable, Sequence

logger = logging.getLogger(__name__)


####################################### Classes ########################################


@dataclass(frozen=True)
class Placeholder:
    """
    A placeholder within a message.

    Within the message value, it looks like this:

        {0}

    Within the comment that declares types, it might look like this:

        0: symbol kind
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
    A message declared in the compiler.properties file. It may have zero or more
    placeholders, each of which can may be annotated with a type and comment.
    """

    name: str
    components: Sequence[Placeholder | str]

    @property
    def text(self) -> str:
        "A plain representation of the message template"
        return str(self)

    @property
    def level(self) -> str:
        "The 'message level' of the error"
        namespace, level, *rest = self.name.split(".")
        assert namespace == "compiler"
        return level

    @property
    def resource_name(self) -> str | None:
        "The name within the enum in com.sun.tools.javac.resources.CompilerProperties"
        namespace, level, *words = self.name.split(".")
        assert namespace == "compiler"

        class_name = {
            "err": "Errors",
            "warn": "Warnings",
            "misc": "Fragments",
            "note": "Notes",
        }.get(level)
        assert class_name is not None

        member_name = "".join(w.title() for w in words)

        return f"{class_name}.{member_name}"

    @property
    def placeholders(self) -> Sequence[Placeholder]:
        "A sequence of all of the unique placeholders in the message, in index order."
        unique_placeholders = {
            item.index: item
            for item in self.components
            if isinstance(item, Placeholder)
        }
        # Placeholders are stored by their position in the message, but we want
        # the placeholders to be accessible by their logical index.
        return sorted(unique_placeholders.values(), key=lambda p: p.index)

    @property
    def n_placeholders(self) -> int:
        "The number of unique placeholders in the message."
        return len(self.placeholders)

    @property
    def is_error_message(self) -> bool:
        "True if this is a compiler error message."
        return self.name.startswith("compiler.err.")

    def __str__(self) -> str:
        # Returns a string that looks like the original value in the file.
        return "".join(str(item) for item in self.components)


class ParseError(Exception):
    def __init__(
        self, *, filename: str, line_no: int, line: str, production: str, message: str
    ):
        self.filename = filename
        self.line_no = line_no
        self.message = message
        self.production = production
        self.message = message
        self.line = line

    def __str__(self):
        return (
            f"{self.filename}:{self.line_no}: {self.message}\n"
            "\n"
            f"  {self.line_no} | {self.line}\n"
            "\n"
            f"(while parsing {self.production})"
        )


class Parser:
    r"""
    A very ad hoc parsing algorithm for a very ad hoc file format.

    This vaguely implements a recursive descent parser, which operates on a line-by-line
    basis. Within each line, parsing is done via a mixture of splitting the line, using
    regular expressions, and basic Python string methods.

    Since comments are *sometimes* meaningful, we maintain the block of comments, in the
    even that the key=value pair uses it to annotate placeholder types.

    Parse errors are always raised by `raise self.parse_error()`, which are messages
    designed exclusively for my eyes (Eddie) to ensure I handle all cases properly. Note
    that a malformed comment is NEVER a parser error --- instead, a message is logged to
    whoever will listen, and we ignore the offending comment.

    For details about the compiler.properties file, consult its own comments:

     - https://github.com/openjdk/jdk/blob/master/src/jdk.compiler/share/classes/com/sun/tools/javac/resources/compiler.properties

    For details about .properties files in general, see:
     - https://docs.oracle.com/javase/10/docs/api/java/util/Properties.html#load(java.io.Reader)
     - https://en.wikipedia.org/wiki/.properties

    Note: according to the docs of `Properties.load(Reader)`, this code is DEFINITELY
    wrong! But it works well enough for now ¯\_(ツ)_/¯

    ...however, the (sometimes) meaningful comments means it's better to parse it as its
    own special format.
    """

    def __init__(self, lines: Iterable[str], *, filename=None):
        self.filename = filename or "<input>"
        self.lines = enumerate(lines, start=1)
        self.line_no, self.raw_line = next(self.lines)
        self.parsing = True
        self.messages: list[Message] = []
        self.current_comment_lines: list[str] = []
        self.parsing = True

    @property
    def line(self) -> str:
        r"""
        Return the current logical line from the file. A logical line:
            - always has trailing (authored) whitespace removed
            - always has \uXXXX escaped interpreted (after whitespace removal)
        """
        line = self.raw_line.rstrip()

        def unescape_unicode(m):
            # TODO: there might be some surrogate pair shenanigans...
            return chr(int(m[1], 16))

        return re.sub(r"\\u([0-9a-zA-Z]{4})", unescape_unicode, line)

    def parse(self) -> list[Message]:
        """
        Parse the file, returning all parsed messages.

        Raises a ParseError if this algorithm can't understand something in the file.
        """
        while self.parsing:
            self.item()

        return self.messages

    def next_line(self) -> None:
        try:
            self.line_no, self.raw_line = next(self.lines)
        except StopIteration:
            self.parsing = False

    ################################ "Productions" #####################################

    def item(self) -> None:
        """
        Parse an "item", which can either be:
         - a comment line
         - an empty line
         - a message (key=value pair)
        """
        if self.line.startswith("#"):
            self.comment()
        elif self.line == "":
            # Empty line. Clear the current comment.
            self.current_comment_lines = []
            self.next_line()
        elif self.line[0].isalpha():
            # A message without an annotation
            self.message()
        else:
            raise self.parse_error()

    def comment(self) -> None:
        """
        Parsing either an "annotation":

        # 0: type

        or a regular comment like

        # hello
        """
        self.current_comment_lines.append(self.line)
        self.next_line()

    def message(self) -> None:
        r"""
        Parse a property (key=value pair) like:

            compiler.err.syntax=\
                    syntax error
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
            value = rest.rstrip()
            self.next_line()

        self.messages.append(Message(name=name, components=self.make_components(value)))
        self.current_comment_lines = []
        # Note: Do not advance to the next line; the next line might be the
        # start of another message.

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
                        # According to the spec, this is actually not an error:
                        raise self.parse_error(f"Unknown escape: {full_escape}")

            chunk = re.sub(r"\\(.)", replace_escape, chunk)

            value_chunks.append(chunk)
            has_continuation = self.line.endswith("\\")
            try:
                self.next_line()
            except StopIteration:
                break

        return "".join(value_chunks).replace("''", "'")

    def make_components(self, message_text: str) -> Sequence[str | Placeholder]:
        """
        Parses out message components, which can be either:
            - literal text; or
            - a numbered placeholder

        Placeholders may have types, which are declared in a comment above the message.
        """

        types = parse_annotation(self.current_comment_lines)
        components: list[Placeholder | str] = []

        placeholder_pattern = re.compile(r"{(\d+)}")

        # This algorithm works by finding all placeholders that look like this:
        #   {0}
        # and appends a text component for the text before the placeholder, and then
        # appending the placeholder, proper -- each iteration appends a text component
        # and a placeholder.
        #
        # For example, on the first iteration of the message: expected {0}, actual: {1}
        #
        #     last_fencepost
        #     |
        #     |         match.start()
        #     |         |
        #     |         |  match.end()
        #     |         |  |
        #     expected: {0}, actual: {1}
        #
        # Then, at the end of the first iteration, the following will be true
        #   components == ["expected: ", Placeholder(0, ...)]
        #
        # The second iteration will continue:
        #
        #                  last_fencepost
        #                  |
        #                  |         match.start()
        #                  |         |
        #                  |         |  match.end()
        #                  |         |  |
        #     expected: {0}, actual: {1}
        #
        # Then, after this iteration, the following will be true:
        #   components == ["expected: ", Placeholder(0), ", actual: ", Placeholder(1)]
        #
        last_fencepost = 0
        for match in placeholder_pattern.finditer(message_text):
            index = int(match[1])

            try:
                placeholder = types[index]
            except KeyError:
                logger.info(
                    "could not find placeholder {%d} in message: %s",
                    index,
                    message_text,
                )
                placeholder = Placeholder(index, None, None)

            before_placeholder = message_text[last_fencepost : match.start()]
            components.append(before_placeholder)
            components.append(placeholder)
            last_fencepost = match.end()

        # Append the text leftover after the last placeholder (if it exists):
        last_bit = message_text[last_fencepost:]
        if last_bit != "":
            components.append(last_bit)

        return components

    def parse_error(self, message=None):
        """
        Helper to create a nice parse error, with plenty of source context.
        """
        name = inspect.stack()[1].function
        return ParseError(
            filename=self.filename,
            line_no=self.line_no,
            line=self.line,
            production=name,
            message=message or "Parse error",
        )


###################################### Public API ######################################


def parse_messages_from_path(filename: Path) -> Sequence[Message]:
    """
    Given a file path, parse the messages from the file.
    """
    with filename.open("r", encoding="UTF-8") as properties_file:
        return parse_messages_from_lines(properties_file, filename=filename.name)


def parse_messages_from_lines(lines: Iterable[str], filename=None) -> Sequence[Message]:
    """
    Given a sequence of lines from a file like `compiler.properties`, parses the file
    including "stylized comments" that provide types for the placeholders.
    """
    p = Parser(lines, filename=filename)
    return p.parse()


################################### Helper functions ###################################


def parse_annotation(lines: Sequence[str]) -> dict[int, Placeholder]:
    """
    Parse annotation comments. These are things that look like this:

        # 0: option name, 1: symbol

    Sometimes they look like this:

        # {0} - current module
        # {1} - package in which the invisible class is declared
        # {2} - module in which {1} is declared
        # 0: symbol, 1: symbol, 2: symbol

    Sometimes they're not even annotations:

        # TODO 308: make a better error message

    Regardless, this function will always a dictionary that maps the index to a Placeholder.
    If at any point the comment looks malformed, this will return an empty dictionary
    and emit a logging message.
    """

    if len(lines) == 0:
        # No placeholder type annotations to be found!
        return {}

    # Only the last line has annotations
    annotation_line = lines[-1].removeprefix("#").lstrip()

    if ":" not in annotation_line:
        logger.info("not interpreting this as an annotation: %s", lines)
        return {}

    # Parse long placeholder comments:
    # e.g., # {0} - message
    long_placeholder_comments = {}
    for line in lines[:-1]:
        if m := re.match(r"#\s+{(\d+)}\s+-\s+(.+)$", line):
            str_index, comment = m.groups()
            index = int(str_index)
            long_placeholder_comments[index] = comment

    # Parse the actual placeholder types themselves,
    # e.g.,
    #     0: symbol, 1: string (expected version)
    types = {}
    for declaration in annotation_line.split(","):
        declaration = declaration.strip()

        str_index, separator, description = declaration.partition(":")
        if separator != ":":
            logger.info("ignoring malformed annotation line: %s", annotation_line)
            return {}

        try:
            index = int(str_index)
        except ValueError:
            logger.info("does not look like an annotation: %s", annotation_line)
            return {}

        # Extract the type and comment from the description
        # e.g., string (found version) -> "string", "found version"
        type_str, paren, comment_str = description.partition("(")
        type_str = type_str.strip()
        if paren == "(":
            comment = comment_str.rstrip().removesuffix(")")
        else:
            comment = long_placeholder_comments.get(index)

        if index in types:
            # Placeholder declared more than once;
            # Log it, but override the previous declaration:
            logger.info(
                "duplicate index %d in annotation line: %s", index, annotation_line
            )

        types[index] = Placeholder(index, type_str, comment)

    return types


if __name__ == "__main__":
    from rich import print
    from rich.logging import RichHandler

    # Configure the logger so we can see logger.info() messages:
    logging.basicConfig(level=logging.INFO, handlers=[RichHandler()])

    # Pares the `compiler.properties` file that is in the same directory as this source
    # file.
    HERE = Path(__file__).resolve().parent
    properties_path = HERE / "compiler.properties"
    assert properties_path.exists()

    messages = parse_messages_from_path(properties_path)
    print()

    for message in messages:
        if not message.is_error_message:
            # Only print error messages.
            continue
        print(f"[bold]{message.name}[/bold]:")
        for line in str(message).splitlines():
            print(f"\t{line}")

    n_errors = sum(m.is_error_message for m in messages)
    total = len(messages)
    print(f"[bold]{n_errors}[/bold] error messages ({total} total)")
