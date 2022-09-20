import hashlib
import sqlite3
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Sequence

from rich import print

from constants import *
from javac_compiler_properties_parser import Message, parse_messages_from_path

SCHEMA = """
CREATE TABLE rater(
    name TEXT PRIMARY KEY
);

CREATE TABLE source(
    jdk_version TEXT PRIMARY KEY,
    file_sha256 TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    permalink TEXT NOT NULL
);

CREATE TABLE message(
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    level TEXT NOT NULL,
    text TEXT NOT NULL,

    FOREIGN KEY (source) REFERENCES source(jdk_version)
);

CREATE TABLE rating(
    rater TEXT NOT NULL,
    message TEXT NOT NULL,
    tags TEXT NOT NULL,
    date DATETIME NOT NULL,

    PRIMARY KEY (rater, message)
);
"""


def init_db(conn):
    with conn:
        conn.executescript(SCHEMA)
        conn.execute(
            """
            INSERT INTO source(jdk_version, file_sha256, commit_sha, permalink)
            VALUES (?, ?, ?, ?)
            """,
            (
                PROPERTIES_JDK_VERSION,
                PROPERTIES_SHA_256,
                PROPERTIES_COMMIT_SHA,
                PROPERTIES_PERMALINK,
            ),
        )
        conn.executemany("INSERT INTO rater(name) VALUES (?)", [("eddie",), ("brett",)])

        def generate_message_data():
            for message in messages():
                message_id = message.name
                level = message_id.split(".")[1]
                text = str(message)
                yield (message_id, PROPERTIES_JDK_VERSION, level, text)

        conn.executemany(
            """
            INSERT INTO message(id, source, level, text)
            VALUES (?, ?, ?, ?)
            """,
            generate_message_data(),
        )


@cache
def messages() -> Sequence[Message]:
    return parse_messages_from_path(PROPERTIES_FILE)


def print_all_placeholder_types():
    placeholder_types: Counter[str] = Counter()

    for message in messages():
        if not message.is_error_message:
            continue

        for placeholder in message.placeholders:
            if placeholder.type_ is None:
                continue
            placeholder_types[placeholder.type_] += 1

    print(placeholder_types.most_common())


def verify_sha(conn):
    cur = conn.execute(
        "SELECT file_sha256 FROM source WHERE jdk_version = ?",
        (PROPERTIES_JDK_VERSION,),
    )
    stored_hash = cur.fetchone()[0].lower()

    with PROPERTIES_FILE.open("rb") as binary_file:
        calculated_hash = hashlib.sha256(binary_file.read()).hexdigest().lower()

    if stored_hash != calculated_hash:
        raise ValueError(
            f"hashes differ: expected {stored_hash}; got {calculated_hash}"
        )


if __name__ == "__main__":
    conn = sqlite3.connect(DATABASE_PATH)
    # init_db(conn)
    verify_sha(conn)
