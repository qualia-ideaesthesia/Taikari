"""User account operations for the web admin UI."""

import hashlib


def update_user_char(c):
    c.execute("""select character_id, max_level, is_uncapped from character""")
    x = c.fetchall()
    c.execute("""select user_id from user""")
    y = c.fetchall()
    if x and y:
        for j in y:
            for i in x:
                c.execute(
                    """delete from user_char_full where user_id=:a and character_id=:b""",
                    {"a": j[0], "b": i[0]},
                )
                exp = 25000 if i[1] == 30 else 10000
                c.execute(
                    """insert into user_char_full values(?,?,?,?,?,?,?)""",
                    (j[0], i[0], i[1], exp, i[2], 0, 0),
                )


def change_userpwd(c, user_id, password):
    hash_pwd = hashlib.sha256(password.encode("utf8")).hexdigest()
    c.execute(
        """update user set password =:a where user_id=:b""",
        {"a": hash_pwd, "b": user_id},
    )


def ban_one_user(c, user_id):
    c.execute("""update user set password = '' where user_id=:a""", {"a": user_id})
    c.execute("""delete from login where user_id=:a""", {"a": user_id})
