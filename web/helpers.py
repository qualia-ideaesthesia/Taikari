import time

ALLOWED_EXTENSIONS = {"db"}


def is_number(value):
    """Return whether the value can be parsed as a float."""
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def allowed_file(filename):
    """Return whether a database upload has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_score(c, user_id, limit=-1, offset=0):
    """Return a user's best scores ordered by rating."""
    if limit >= 0:
        c.execute(
            "SELECT * FROM best_score WHERE user_id = :a ORDER BY rating DESC LIMIT :b OFFSET :c",
            {"a": user_id, "b": limit, "c": offset},
        )
    else:
        c.execute(
            "SELECT * FROM best_score WHERE user_id = :a ORDER BY rating DESC",
            {"a": user_id},
        )

    rows = c.fetchall()
    result = []
    for rank, row in enumerate(rows, 1):
        result.append(
            {
                "song_id": row[1],
                "difficulty": row[2],
                "score": row[3],
                "shiny_perfect_count": row[4],
                "perfect_count": row[5],
                "near_count": row[6],
                "miss_count": row[7],
                "health": row[8],
                "modifier": row[9],
                "time_played": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(row[10])
                ),
                "best_clear_type": row[11],
                "clear_type": row[12],
                "rating": row[13],
                "rank": rank,
            }
        )
    return result


def format_user_row(row):
    """Format a raw ``user`` table row into the web-facing dict."""
    if not row:
        return None

    join_date = None
    time_played = None
    if row[3]:
        join_date = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(int(row[3]) // 1000)
        )
    if row[20]:
        time_played = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(int(row[20]) // 1000)
        )

    return {
        "name": row[1],
        "user_id": row[0],
        "join_date": join_date,
        "user_code": row[4],
        "rating_ptt": row[5],
        "song_id": row[11],
        "difficulty": row[12],
        "score": row[13],
        "shiny_perfect_count": row[14],
        "perfect_count": row[15],
        "near_count": row[16],
        "miss_count": row[17],
        "time_played": time_played,
        "clear_type": row[21],
        "rating": row[22],
        "ticket": row[26],
        # A user is banned when an automatic multi-device ban is recorded in
        # `ban_flag` (col 30) or when the account ban emptied the password
        # (col 2) — both are enforced in core/user.py UserLogin.
        "ban_flag": bool(row[2] == "" or (row[30] not in (None, ""))),
    }


def get_user(c, user_id):
    """Return the web-facing subset of a user's data."""
    c.execute("SELECT * FROM user WHERE user_id = :a", {"a": user_id})
    return format_user_row(c.fetchone())


def resolve_user_id(c, name=None, user_code=None):
    """Look up a ``user_id`` by ``user_code`` (preferred) or user name.

    Returns ``None`` when no matching user exists. This is shared by the web
    routes that accept either a name or a user code from a form.
    """
    if user_code:
        c.execute("SELECT user_id FROM user WHERE user_code = :a", {"a": user_code})
    else:
        c.execute("SELECT user_id FROM user WHERE name = :a", {"a": name})

    row = c.fetchone()
    return row[0] if row else None
