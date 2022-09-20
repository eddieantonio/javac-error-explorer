from flask import Flask, render_template
from rich import print

import constants
from data_layer import messages
from javac_compiler_properties_parser import Placeholder

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", messages=messages().values())


@app.route("/rate/<message_id>")
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

    return render_template(
        "message-detail.html", message=message, tags=tags, components=components
    )


# Place all globals in the Jinja environment
for name in dir(constants):
    if not name[:1].isupper():
        continue
    app.jinja_env.globals[name] = getattr(constants, name)
