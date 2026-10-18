from flask import flash, redirect, render_template, request, url_for

from core.sql import Connect
from web.blueprint import bp
from web.login import login_required

from core.operation import SaveUpdateScore, UnlockUserItem
from core.user import User
from web.helpers import resolve_user_id


@bp.route("/changeuser", methods=["GET"])
@login_required
def change_user():

    return render_template("web/changeuser.html")


@bp.route("/changeuser/edituser", methods=["POST"])
@login_required
def edit_user():

    error = None
    flag = True
    name = None
    user_code = None
    try:
        ticket_raw = request.form.get("ticket")
        if ticket_raw is None or ticket_raw == "":
            ticket = None
        else:
            ticket = int(ticket_raw)
    except (TypeError, ValueError):
        error = "Wrong data."
        flash(error)
        return redirect(url_for("index.change_user"))

    with Connect() as c:

        if "name" not in request.form and "user_code" not in request.form:
            flag = False
            if ticket is None:
                error = "No change."
            else:
                sql = """update user set ticket = :ticket"""
                sql_dict = {"ticket": ticket}
                c.execute(sql, sql_dict)
                flash(
                    "Successfully edit all the users' information."
                )

        else:
            name = request.form.get("name")
            user_code = request.form.get("user_code")

        if name or user_code:

            user_id = resolve_user_id(c, name, user_code)
            if user_id:

                if ticket is None:
                    error = "No change."
                else:
                    sql = (
                        """update user set ticket = :ticket where user_id = :user_id"""
                    )
                    sql_dict = {"ticket": ticket, "user_id": user_id}
                    c.execute(sql, sql_dict)
                    flash("Successfully edit the user information.")

            else:
                error = "The player does not exist."

        else:
            if flag:
                error = "Null Input."

    if error:
        flash(error)

    return redirect(url_for("index.change_user"))


@bp.route("/changeuserpurchase", methods=["GET"])
@login_required
def change_user_purchase():

    return render_template("web/changeuserpurchase.html")


@bp.route("/changeuserpurchase/edituser", methods=["POST"])
@login_required
def edit_user_purchase():

    error = None
    flag = True
    name = None
    user_code = None
    try:
        method = request.form.get("method")
    except (TypeError, ValueError):
        flash("Null Input.")
        return redirect(url_for("index.change_user_purchase"))

    with Connect() as c:

        if "name" not in request.form and "user_code" not in request.form:
            flag = False
            if method == "0":
                UnlockUserItem().run()
            else:
                c.execute("""delete from user_item where type in ('pack', 'single')""")

            flash(
                "Successfully edit all the users' purchase information."
            )

        else:
            name = request.form.get("name")
            user_code = request.form.get("user_code")

        if name or user_code:

            user_id = resolve_user_id(c, name, user_code)
            if user_id:

                if method == "0":
                    x = UnlockUserItem()
                    x.set_params(user_id=user_id)
                    x.run()
                else:
                    c.execute(
                        """delete from user_item where type in ('pack', 'single') and user_id = :user_id""",
                        {"user_id": user_id},
                    )
                flash(
                    "Successfully edit the user purchase information."
                )

            else:
                error = "The player does not exist."

        else:
            if flag:
                error = "Null Input."

    if error:
        flash(error)

    return redirect(url_for("index.change_user_purchase"))


@bp.route("/updateusersave", methods=["POST", "GET"])
@login_required
def update_user_save():

    if request.method == "GET":
        return render_template("web/updateusersave.html")

    error = None
    flag = True
    name = None
    user_code = None

    with Connect() as c:

        if "name" not in request.form and "user_code" not in request.form:
            flag = False
            SaveUpdateScore().run()
            flash("Successfully update all users' saves.")

        else:
            name = request.form["name"]
            user_code = request.form["user_code"]

        if name or user_code:

            user_id = resolve_user_id(c, name, user_code)
            if user_id:
                user = User()
                user.user_id = user_id
                SaveUpdateScore(user).run()
                flash("Successfully update the user's saves.")

            else:
                error = "The player does not exist."

        else:
            if flag:
                error = "Null Input."

    if error:
        flash(error)

    return render_template("web/updateusersave.html")
