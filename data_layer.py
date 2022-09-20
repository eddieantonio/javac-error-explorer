"""
Access to any and all data.
"""

import hashlib
from functools import cache
from typing import Mapping, Sequence

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


def init_db(conn) -> None:
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
            for message in message_list():
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


def verify_sha(conn) -> None:
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


@cache
def message_list() -> list[Message]:
    "Return all the parsed messages as one long list"
    return list(messages().values())


@cache
def messages() -> Mapping[str, Message]:
    "Return all the messages as a mapping from its id -> message"
    return {m.name: m for m in parse_messages_from_path(PROPERTIES_FILE)}
