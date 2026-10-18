"""Redeem code operations for the web admin UI."""

from core.sql import Connect

from ._common import random_str


def add_one_redeem(code, redeem_type, item_id, item_type, item_amount):
    message = None
    with Connect() as c:
        c.execute("""select exists(select * from redeem where code=:a)""", {"a": code})
        if c.fetchone() == (0,):
            c.execute(
                """select exists(select * from item where item_id=? and type=?)""",
                (item_id, item_type),
            )
            if c.fetchone() == (1,):
                c.execute(
                    """insert into redeem values(:a,:c)""",
                    {"a": code, "c": redeem_type},
                )
                c.execute(
                    """insert into redeem_item values(?,?,?,?)""",
                    (code, item_id, item_type, item_amount),
                )
                message = "Successfully add it."
            else:
                message = "The item does not exist."
        else:
            message = "The redeem code exists."

    return message


def add_some_random_redeem(amount, redeem_type, item_id, item_type, item_amount):
    message = None
    with Connect() as c:
        c.execute(
            """select exists(select * from item where item_id=? and type=?)""",
            (item_id, item_type),
        )
        if c.fetchone() == (0,):
            return "The item does not exist."
        i = 1
        while i <= amount:
            code = random_str()
            c.execute(
                """select exists(select * from redeem where code=:a)""", {"a": code}
            )
            if c.fetchone() == (0,):
                c.execute(
                    """insert into redeem values(:a,:c)""",
                    {"a": code, "c": redeem_type},
                )
                c.execute(
                    """insert into redeem_item values(?,?,?,?)""",
                    (code, item_id, item_type, item_amount),
                )
                i += 1

        message = "Successfully add it."

    return message


def delete_one_redeem(code):
    message = None
    with Connect() as c:
        c.execute("""select exists(select * from redeem where code=:a)""", {"a": code})
        if c.fetchone() == (1,):
            c.execute("""delete from redeem where code = :a""", {"a": code})
            c.execute("""delete from user_redeem where code =:a""", {"a": code})
            c.execute("""delete from redeem_item where code =:a""", {"a": code})
            message = "Successfully delete it."
        else:
            message = "The redeem code does not exist."

    return message
