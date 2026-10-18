from flask import flash, redirect, render_template, request, url_for

from core.sql import Connect
from web.blueprint import bp
from web.login import login_required

import time

import web.system
from web.helpers import resolve_user_id


@bp.route("/allpresent", methods=["GET"])
@login_required
def all_present():

    error = None
    with Connect() as c:
        c.execute("""select * from present""")
        x = c.fetchall()

        # Fetch all present items at once instead of one query per present.
        c.execute("""select present_id, item_id, type, amount from present_item""")
        items_by_present = {}
        for j in c.fetchall():
            items_by_present.setdefault(j[0], []).append(
                {"item_id": j[1], "type": j[2], "amount": j[3]}
            )

        if x:
            posts = []
            for i in x:
                posts.append(
                    {
                        "present_id": i[0],
                        "expire_ts": time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime(int(i[1]) // 1000)
                        ),
                        "items": items_by_present.get(i[0], []),
                        "description": i[2],
                    }
                )
        else:
            error = "No present data."

    if error:
        flash(error)
        return render_template("web/allpresent.html")
    else:
        return render_template("web/allpresent.html", posts=posts)


@bp.route("/changepresent", methods=["GET"])
@login_required
def change_present():
    return render_template("web/changepresent.html")


@bp.route("/changepresent/addpresent", methods=["POST"])
@login_required
def add_present():
    present_id = request.form["present_id"]
    expire_ts = request.form["expire_ts"]
    description = request.form["description"]
    item_id = request.form["item_id"]
    item_type = request.form["type"]
    item_amount = request.form["amount"]

    try:
        if item_amount:
            item_amount = int(item_amount)
        else:
            item_amount = 1
        expire_ts = int(time.mktime(time.strptime(expire_ts, "%Y-%m-%dT%H:%M"))) * 1000
    except:
        flash("Wrong data.")
        return redirect(url_for("index.change_present"))

    if len(present_id) >= 256:
        present_id = present_id[:200]
    if len(description) >= 256:
        description = description[:200]

    message = web.system.add_one_present(
        present_id, expire_ts, description, item_id, item_type, item_amount
    )

    if message:
        flash(message)

    return redirect(url_for("index.change_present"))


@bp.route("/changepresent/deletepresent", methods=["POST"])
@login_required
def delete_present():
    present_id = request.form["present_id"]
    message = web.system.delete_one_present(present_id)

    if message:
        flash(message)

    return redirect(url_for("index.change_present"))


@bp.route("/deliverpresent", methods=["GET", "POST"])
@login_required
def deliver_present():

    if request.method == "GET":
        return render_template("web/deliverpresent.html")

    error = None
    flag = True
    name = None
    user_code = None
    present_id = request.form["present_id"]

    with Connect() as c:
        if not web.system.is_present_available(c, present_id):
            flash("The present does not exist.")
            return render_template("web/deliverpresent.html")

        if "name" not in request.form and "user_code" not in request.form:
            flag = False
            web.system.deliver_all_user_present(c, present_id)
            flash("Successfully deliver the present to all users.")
        else:
            name = request.form["name"]
            user_code = request.form["user_code"]

        if name or user_code:
            user_id = resolve_user_id(c, name, user_code)
            if user_id:
                web.system.deliver_one_user_present(c, present_id, user_id)
                flash("Successfully deliver the present to the user.")

            else:
                error = "The player does not exist."

        else:
            if flag:
                error = "Null Input."

    if error:
        flash(error)

    return render_template("web/deliverpresent.html")


@bp.route("/allredeem", methods=["GET"])
@login_required
def all_redeem():

    error = None
    with Connect() as c:
        c.execute("""select * from redeem""")
        x = c.fetchall()

        # Fetch all redeem items at once instead of one query per code.
        c.execute("""select code, item_id, type, amount from redeem_item""")
        items_by_code = {}
        for j in c.fetchall():
            items_by_code.setdefault(j[0], []).append(
                {"item_id": j[1], "type": j[2], "amount": j[3]}
            )

        if x:
            posts = []
            for i in x:
                posts.append(
                    {"code": i[0], "items": items_by_code.get(i[0], []), "type": i[1]}
                )
        else:
            error = "No redeem code data."

    if error:
        flash(error)
        return render_template("web/allredeem.html")
    else:
        return render_template("web/allredeem.html", posts=posts)


@bp.route("/changeredeem", methods=["GET"])
@login_required
def change_redeem():
    return render_template("web/changeredeem.html")


@bp.route("/changeredeem/addredeem", methods=["POST"])
@login_required
def add_redeem():
    code = request.form["code"]
    redeem_amount = request.form["redeem_amount"]
    redeem_type = request.form["redeem_type"]
    item_id = request.form["item_id"]
    item_type = request.form["type"]
    item_amount = request.form["amount"]

    try:
        if item_amount:
            item_amount = int(item_amount)
        else:
            item_amount = 1
        if redeem_amount:
            redeem_amount = int(redeem_amount)
    except:
        flash("Wrong data.")
        return redirect(url_for("index.change_redeem"))

    if code and not redeem_amount:
        if len(code) > 20 or len(code) < 10:
            flash("Inappropriate length of redeem code.")
            return redirect(url_for("index.change_redeem"))

        message = web.system.add_one_redeem(
            code, redeem_type, item_id, item_type, item_amount
        )
    elif redeem_amount and not code:
        if redeem_amount <= 0 or redeem_amount > 1000:
            flash("Wrong amount.")
            return redirect(url_for("index.change_redeem"))

        message = web.system.add_some_random_redeem(
            redeem_amount, redeem_type, item_id, item_type, item_amount
        )
    elif redeem_amount and code:
        flash("Only one add method can be used.")
        return redirect(url_for("index.change_redeem"))
    else:
        flash("Null input.")
        return redirect(url_for("index.change_redeem"))

    if message:
        flash(message)

    return redirect(url_for("index.change_redeem"))


@bp.route("/changeredeem/deleteredeem", methods=["POST"])
@login_required
def delete_redeem():
    code = request.form["code"]
    message = web.system.delete_one_redeem(code)

    if message:
        flash(message)

    return redirect(url_for("index.change_redeem"))


@bp.route("/redeem/<code>", methods=["GET"])
@login_required
def one_redeem(code):

    error = None
    with Connect() as c:
        c.execute(
            """select user_id, name, user_code from user where user_id in (select user_id from user_redeem where code=:a)""",
            {"a": code},
        )
        x = c.fetchall()
        if x:
            posts = []
            for i in x:
                posts.append({"user_id": i[0], "name": i[1], "user_code": i[2]})
        else:
            error = "No data."

    if error:
        flash(error)
        return render_template("web/redeem.html", code=code)
    else:
        return render_template("web/redeem.html", posts=posts, code=code)
