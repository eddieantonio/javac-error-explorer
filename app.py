from flask import Flask, render_template
from rich import print

import constants
from data_layer import messages

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", messages=messages().values())


@app.route("/rate/<message_id>")
def message_detail(message_id: str):
    message = messages().get(message_id)
    if message is None:
        return "<p>Message not found. <a href='/'>Go back home</a>", 404

    tags = {
        "soup": "Token Soup",
        "suggestion": "Implicit Suggestion",
        "cascade": "Cascading Error",
        "compilerspeak": "Compiler-speak",
        "conflict": "One-sided conflict",
        "illegal": "Illegal Vocabulary",
    }

    return render_template("message-detail.html", message=message, tags=tags)


# Place all globals in the Jinja environment
for name in dir(constants):
    if not name[:1].isupper():
        continue
    app.jinja_env.globals[name] = getattr(constants, name)
