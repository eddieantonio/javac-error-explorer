import sqlite3
from collections import Counter

from rich import print

from constants import *
from data_layer import verify_sha


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


if __name__ == "__main__":
    conn = sqlite3.connect(DATABASE_PATH)
    # init_db(conn)
    verify_sha(conn)
