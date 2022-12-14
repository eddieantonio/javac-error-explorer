"""
Test javac compiler.properties parser.
"""

from javac_compiler_properties_parser import parse_messages_from_lines

# Various parsing cases, including:
# - multiple, complex placeholder descriptions
# - a message with an erroneous line extender (`\` at the end of the line)
# - a message with no placeholders
# - a message with a comment, but no placeholder declarations
# - a message with placeholders, but no placeholder declarations
# - a message with a UTF-16 escape
# - placeholders with comments (in parentheses)
EXAMPLE = r"""
# 0: symbol kind, 1: name, 2: list of type or message segment, 3: list of type or message segment, 4: symbol kind, 5: type, 6: message segment
compiler.misc.cant.apply.symbol=\
    {0} {1} in {4} {5} cannot be applied to given types\n\
    required: {2}\n\
    found:    {3}\n\
    reason: {6}

# 0: fragment
compiler.err.local.classes.cant.extend.sealed=\
    {0} classes must not extend sealed classes\

compiler.misc.anonymous=\
    anonymous

# TODO 308: make a better error message
compiler.err.this.as.identifier=\
    as of release 8, ''this'' is allowed as the parameter name for the receiver type only\n\
    which has to be the first parameter, and cannot be a lambda parameter

compile.misc.fake.message=syntax error

compiler.misc.bad.const.pool.tag=\
    bad constant pool tag: {0}

## All errors which do not refer to a particular line in the source code are
## preceded by this string.
compiler.err.error=\
    error:\u0020

# 0: message segment (feature), 1: string (found version), 2: string (expected version)
compiler.err.feature.not.supported.in.source=\
   {0} is not supported in -source {1}\n\
    (use -source {2} or higher to enable {0})

# {0} - package in which the invisible class is declared
# {1} - module in which {0} is declared
# 0: symbol, 1: symbol
compiler.misc.not.def.access.does.not.read.from.unnamed=\
    package {0} is declared in module {1}, which is not in the module graph

compiler.err.else.without.if=\
    ''else'' without ''if''

# 0: symbol
compiler.err.icls.cant.have.static.decl.fake=\
    modifier \''static\'' is only allowed in constant variable declarations
"""
N_EXAMPLES = 11


def test_kitchen_sink() -> None:
    messages = parse_messages_from_lines(EXAMPLE.splitlines(), "<example>")
    assert len(messages) == N_EXAMPLES
    name_to_message = {m.name: m for m in messages}
    assert len(name_to_message) == N_EXAMPLES

    # Test the simple message can be converted to a string:
    m = name_to_message["compiler.misc.anonymous"]
    assert str(m) == "anonymous"

    # Test a message with a single placeholder
    m = name_to_message["compiler.err.local.classes.cant.extend.sealed"]
    assert str(m) == "{0} classes must not extend sealed classes"
    assert m.n_placeholders == 1
    assert m.placeholders[0].type_ == "fragment"

    # Test a message with multiple placeholders
    m = name_to_message["compiler.misc.cant.apply.symbol"]
    assert m.n_placeholders == 7
    assert m.placeholders[0].type_ == "symbol kind"
    assert m.placeholders[1].type_ == "name"
    assert m.placeholders[4].type_ == "symbol kind"
    assert m.placeholders[5].type_ == "type"
    assert m.placeholders[6].type_ == "message segment"

    # Test a message with a UTF-16 escape
    m = name_to_message["compiler.err.error"]
    assert str(m) == "error: "

    # Test a message with a comment, but no placeholders
    m = name_to_message["compiler.err.this.as.identifier"]
    assert m.n_placeholders == 0

    # Test a message with placeholders, but no placeholder declarations
    m = name_to_message["compiler.misc.bad.const.pool.tag"]
    assert m.n_placeholders == 1
    assert m.placeholders[0].type_ is None

    # Test a message that does not spill on to the next line (fake)
    m = name_to_message["compile.misc.fake.message"]
    assert str(m) == "syntax error"

    # Test that comments are parsed in the message.
    m = name_to_message["compiler.err.feature.not.supported.in.source"]
    assert m.placeholders[0].type_ == "message segment"
    assert m.placeholders[0].comment == "feature"
    assert m.placeholders[1].type_ == "string"
    assert m.placeholders[1].comment == "found version"
    assert m.placeholders[2].type_ == "string"
    assert m.placeholders[2].comment == "expected version"

    # Test that comments are parsed from above the annotation.
    m = name_to_message["compiler.misc.not.def.access.does.not.read.from.unnamed"]
    assert m.placeholders[0].type_ == "symbol"
    assert (
        m.placeholders[0].comment == "package in which the invisible class is declared"
    )
    assert m.placeholders[1].type_ == "symbol"
    assert m.placeholders[1].comment == "module in which {0} is declared"

    # Test that single quotes are interpreted correctly
    m = name_to_message["compiler.err.else.without.if"]
    assert str(m) == "'else' without 'if'"
    m = name_to_message["compiler.err.icls.cant.have.static.decl.fake"]
    assert (
        str(m) == "modifier 'static' is only allowed in constant variable declarations"
    )
