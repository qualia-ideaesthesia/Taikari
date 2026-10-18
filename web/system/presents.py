"""Present operations for the web admin UI."""

from core.sql import Connect


def add_one_present(
    present_id, expire_ts, description, item_id, item_type, item_amount
):
    message = None
    with Connect() as c:
        c.execute(
            """select exists(select * from present where present_id=:a)""",
            {"a": present_id},
        )
        if c.fetchone() == (0,):
            c.execute(
                """select exists(select * from item where item_id=? and type=?)""",
                (item_id, item_type),
            )
            if c.fetchone() == (1,):
                c.execute(
                    """insert into present values(:a,:b,:c)""",
                    {"a": present_id, "b": expire_ts, "c": description},
                )
                c.execute(
                    """insert into present_item values(?,?,?,?)""",
                    (present_id, item_id, item_type, item_amount),
                )
                message = "Successfully add it."
            else:
                message = "The item does not exist."
        else:
            message = "The present exists."

    return message


def delete_one_present(present_id):
    message = None
    with Connect() as c:
        c.execute(
            """select exists(select * from present where present_id=:a)""",
            {"a": present_id},
        )
        if c.fetchone() == (1,):
            c.execute(
                """delete from present where present_id = :a""", {"a": present_id}
            )
            c.execute(
                """delete from user_present where present_id =:a""", {"a": present_id}
            )
            c.execute(
                """delete from present_item where present_id =:a""", {"a": present_id}
            )
            message = "Successfully delete it."
        else:
            message = "The present does not exist."

    return message


def is_present_available(c, present_id):
    c.execute(
        """select exists(select * from present where present_id = :a)""",
        {"a": present_id},
    )
    return c.fetchone() == (1,)


def deliver_one_user_present(c, present_id, user_id):
    c.execute(
        """select exists(select * from user_present where user_id=:a and present_id=:b)""",
        {"a": user_id, "b": present_id},
    )
    if c.fetchone() == (0,):
        c.execute(
            """insert into user_present values(:a,:b)""",
            {"a": user_id, "b": present_id},
        )


def deliver_all_user_present(c, present_id):
    c.execute("""select user_id from user""")
    x = c.fetchall()
    if x:
        c.execute("""delete from user_present where present_id=:b""", {"b": present_id})
        for i in x:
            c.execute(
                """insert into user_present values(:a,:b)""",
                {"a": i[0], "b": present_id},
            )
