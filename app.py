from flask import Flask, redirect, render_template, url_for
from rich import print

import constants
from data_layer import message_list, messages
from javac_compiler_properties_parser import Placeholder

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", messages=messages().values())


@app.route("/message/<message_id>")
def message_detail(message_id: str):

    # Get the message
    message = messages().get(message_id)
    if message is None:
        return render_template("message-not-found.html", message_id=message_id), 404

    # TODO: figure out how to represent these tags
    tags = {
        "soup": "Token Soup",
        "suggestion": "Implicit Suggestion",
        "cascade": "Cascading Error",
        "compilerspeak": "Compiler-speak",
        "conflict": "One-sided conflict",
        "illegal": "Illegal Vocabulary",
    }

    # prepare components
    components = []
    for item in message.components:
        if isinstance(item, Placeholder):
            components.append(
                {
                    "is_placeholder": True,
                    "index": item.index,
                    "type": item.type_,
                    "comment": item.comment,
                }
            )
        else:
            components.append(
                {
                    "is_text": True,
                    "text": item,
                }
            )

    # This is an attrocious way to do it 🙈
    query = "+".join(
        " ".join(item for item in message.components if isinstance(item, str)).split()
    )
    stack_overflow_search = f"https://stackoverflow.com/search?q=%5Bjava%5D+{query}"

    return render_template(
        "message-detail.html",
        message=message,
        tags=tags,
        components=components,
        stack_overflow_search=stack_overflow_search,
    )


@app.route("/next-message/<message_id>")
def next_message(message_id: str):
    return seek_message(message_id, diff=+1, default_index=0)


@app.route("/previous-message/<message_id>")
def previous_message(message_id: str):
    return seek_message(message_id, diff=-1, default_index=-1)


def seek_message(message_id: str, *, diff: int, default_index: int):
    """
    Get a message offset from the given message ID.
    """
    current = messages().get(message_id)
    if current is None:
        return render_template("message-not-found.html", message_id=message_id), 404

    # Uh... ignore the fact that this code is awful.
    all_messages = message_list()
    current_index = all_messages.index(current)
    next_index = current_index + diff
    try:
        next_message = all_messages[next_index]
    except IndexError:
        # Wrap around
        next_message = all_messages[default_index]

    return redirect(url_for("message_detail", message_id=next_message.name))


# Place all globals in the Jinja environment
for name in dir(constants):
    if not name[:1].isupper():
        continue
    app.jinja_env.globals[name] = getattr(constants, name)
