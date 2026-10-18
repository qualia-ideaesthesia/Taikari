from flask import flash, redirect, render_template, request, url_for

from core.sql import Connect
from web.blueprint import bp
from web.login import login_required

import web.system
from web.helpers import resolve_user_id

from core.operation import DeleteUserScore


@bp.route("/changeuserpwd", methods=["GET", "POST"])
@login_required
def edit_userpwd():
    if request.method == "GET":
        return render_template("web/changeuserpwd.html")

    error = None

    name = request.form.get("name")
    user_code = request.form.get("user_code")
    pwd = request.form.get("pwd")
    pwd2 = request.form.get("pwd2")
    if pwd != pwd2:
        flash("Entered passwords differ!")
        return render_template("web/changeuserpwd.html")
    else:
        if len(pwd) < 8 or len(pwd) > 20:
            flash("Password is too long or too short!")
            return render_template("web/changeuserpwd.html")

    with Connect() as c:
        if name or user_code:

            user_id = resolve_user_id(c, name, user_code)
            if user_id:
                web.system.change_userpwd(c, user_id, pwd)
                flash("Successfully edit the user information.")

            else:
                error = "The player does not exist."

        else:
            error = "Null Input."

    if error:
        flash(error)

    return redirect(url_for("index.edit_userpwd"))


@bp.route("/banuser", methods=["POST", "GET"])
@login_required
def ban_user():
    if request.method == "GET":
        return render_template("web/banuser.html")

    error = None

    name = request.form.get("name")
    user_code = request.form.get("user_code")

    with Connect() as c:
        if name or user_code:
            user_id = resolve_user_id(c, name, user_code)
            if user_id:
                web.system.ban_one_user(c, user_id)
                flash("Successfully ban the user.")

            else:
                error = "The player does not exist."

        else:
            error = "Null Input."

    if error:
        flash(error)

    return redirect(url_for("index.ban_user"))


@bp.route("/banuser/deleteuserscore", methods=["POST"])
@login_required
def delete_user_score():
    error = None

    name = request.form.get("name")
    user_code = request.form.get("user_code")

    with Connect() as c:
        if name or user_code:
            user_id = resolve_user_id(c, name, user_code)
            if user_id:
                c.execute(
                    """update user set rating_ptt=0, song_id='', difficulty=0, score=0, shiny_perfect_count=0, perfect_count=0, near_count=0, miss_count=0, health=0, time_played=0, rating=0, world_rank_score=0 where user_id=:a""",
                    {"a": user_id},
                )
                c.connection.commit()
                DeleteUserScore().set_params(user_id=user_id).run()
                flash("Successfully delete the user's scores.")

            else:
                error = "The player does not exist."

        else:
            error = "Null Input."

    if error:
        flash(error)

    return redirect(url_for("index.ban_user"))


@bp.route("/changescore", methods=["GET"])
@login_required
def change_score():
    return render_template("web/changescore.html")


@bp.route("/changescore/delete", methods=["POST"])
@login_required
def delete_score():

    song_id = request.form.get("sid", "")
    difficulty_raw = request.form.get("difficulty", "")
    name = request.form.get("name")
    user_code = request.form.get("user_code")

    error = "Unknown error."
    flag = [False, False, False]
    if song_id:
        flag[0] = True

    # "-1" (or blank) means "all difficulties"; otherwise it must be a
    # non-negative integer. `flag[1]` should only be set for a real filter.
    difficulty = -1
    if difficulty_raw not in ("", "-1", None):
        if not difficulty_raw.isdigit():
            flash("Invalid difficulty.")
            return redirect(url_for("index.change_score"))
        difficulty = int(difficulty_raw)
        flag[1] = True

    with Connect() as c:
        if name or user_code:
            user_id = resolve_user_id(c, name, user_code)
            if user_id:
                flag[2] = True
            else:
                error = "The player does not exist."

        if flag[0] or flag[1] or flag[2]:
            sql = """delete from best_score where """
            sql_dict = {}
            if flag[0]:
                sql += "song_id=:song_id and "
                sql_dict["song_id"] = song_id
            if flag[1]:
                sql += "difficulty=:difficulty and "
                sql_dict["difficulty"] = difficulty
            if flag[2]:
                sql += "user_id=:user_id "
                sql_dict["user_id"] = user_id
            if sql[-4:-1] == "and":
                sql = sql[:-4]

            c.execute(sql, sql_dict)
            flash("Successfully delete the scores.")
            error = None
        else:
            error = "Null Input."

    if error:
        flash(error)

    return redirect(url_for("index.change_score"))
