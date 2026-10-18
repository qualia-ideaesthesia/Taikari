"""Item catalog operations for the web admin UI."""

from core.sql import Connect

from ._common import int2b


def get_all_item():
    with Connect() as c:
        c.execute("""select * from item""")
        x = c.fetchall()

    return [
        {"item_id": i[0], "type": i[1], "is_available": int2b(i[2])} for i in x or []
    ]
