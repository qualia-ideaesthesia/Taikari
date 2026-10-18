from flask import flash, redirect, render_template, request, url_for

from core.sql import Connect
from web.blueprint import bp
from web.login import login_required

import time

import web.system


@bp.route("/allitem", methods=["GET"])
@login_required
def all_item():

    error = None
    posts = web.system.get_all_item()
    if not posts:
        error = "No item data."

    if error:
        flash(error)
        return render_template("web/allitem.html")
    else:
        return render_template("web/allitem.html", posts=posts)


@bp.route("/changeitem", methods=["GET", "POST"])
@login_required
def change_item():

    error = None
    if request.method == "POST":
        try:
            item_id = request.form["item_id"]
            item_type = request.form["type"]
            try:
                is_available = request.form["is_available"]
                if is_available:
                    is_available = int(is_available)
                else:
                    is_available = 0
            except:
                is_available = 0

        except:
            error = "Wrong data."
            flash(error)
            return redirect(url_for("index.change_item"))

        with Connect() as c:
            c.execute(
                """select exists(select * from item where item_id=:a and type=:b)""",
                {"a": item_id, "b": item_type},
            )
            if c.fetchone() == (0,):
                c.execute(
                    """insert into item values(?,?,?)""",
                    (item_id, item_type, is_available),
                )
                flash("Successfully add the item.")
            else:
                error = "The item exists."

        if error:
            flash(error)

    return render_template("web/changeitem.html")


@bp.route("/changeitem/delete", methods=["POST"])
@login_required
def change_item_delete():

    error = None
    try:
        item_id = request.form["item_id"]
        item_type = request.form["type"]
    except:
        error = "Wrong data."
        flash(error)
        return redirect(url_for("index.change_item"))

    with Connect() as c:
        c.execute(
            """select exists(select * from item where item_id=:a and type=:b)""",
            {"a": item_id, "b": item_type},
        )
        if c.fetchone() == (1,):
            c.execute(
                """delete from item where item_id=? and type=?""", (item_id, item_type)
            )
            flash("Successfully delete the item.")
        else:
            error = "The item does not exist."

    if error:
        flash(error)

    return render_template("web/changeitem.html")


@bp.route("/allpurchase", methods=["GET"])
@login_required
def all_purchase():

    error = None
    posts = web.system.get_all_purchase()
    if not posts:
        error = "No purchase data."

    if error:
        flash(error)
        return render_template("web/allpurchase.html")
    else:
        return render_template("web/allpurchase.html", posts=posts)


@bp.route("/changepurchase", methods=["GET", "POST"])
@login_required
def change_purchase():

    error = None
    if request.method == "POST":
        try:
            purchase_name = request.form["purchase_name"]
            price = request.form["price"]
            orig_price = request.form["orig_price"]
            discount_from = request.form["discount_from"]
            discount_to = request.form["discount_to"]
            discount_reason = request.form["discount_reason"]

            if price:
                price = int(price)
            else:
                price = None
            if orig_price:
                orig_price = int(orig_price)
            else:
                orig_price = None
            if discount_from:
                discount_from = (
                    int(time.mktime(time.strptime(discount_from, "%Y-%m-%dT%H:%M")))
                    * 1000
                )
            else:
                discount_from = -1
            if discount_to:
                discount_to = (
                    int(time.mktime(time.strptime(discount_to, "%Y-%m-%dT%H:%M")))
                    * 1000
                )
            else:
                discount_to = -1

            if not discount_reason:
                discount_reason = ""

        except:
            error = "Wrong data."
            flash(error)
            return redirect(url_for("index.change_purchase"))

        with Connect() as c:
            c.execute(
                """select exists(select * from purchase where purchase_name=:a)""",
                {"a": purchase_name},
            )
            if c.fetchone() == (0,):
                c.execute(
                    """insert into purchase values(?,?,?,?,?,?)""",
                    (
                        purchase_name,
                        price,
                        orig_price,
                        discount_from,
                        discount_to,
                        discount_reason,
                    ),
                )

                flash("Successfully add the purchase.")
            else:
                error = "The purchase exists."

        if error:
            flash(error)

    return render_template("web/changepurchase.html")


@bp.route("/changepurchase/delete", methods=["POST"])
@login_required
def change_purchase_delete():

    error = None
    try:
        purchase_name = request.form["purchase_name"]
    except:
        error = "Wrong data."
        flash(error)
        return redirect(url_for("index.change_purchase"))

    with Connect() as c:
        c.execute(
            """select exists(select * from purchase where purchase_name=:a)""",
            {"a": purchase_name},
        )
        if c.fetchone() == (1,):
            c.execute(
                """delete from purchase where purchase_name=?""", (purchase_name,)
            )
            c.execute(
                """delete from purchase_item where purchase_name=?""", (purchase_name,)
            )
            flash("Successfully delete the purchase.")
        else:
            error = "The purchase does not exist."

    if error:
        flash(error)

    return render_template("web/changepurchase.html")


@bp.route("/changepurchaseitem", methods=["GET", "POST"])
@login_required
def change_purchase_item():

    error = None
    if request.method == "POST":
        try:
            purchase_name = request.form["purchase_name"]
            item_id = request.form["item_id"]
            item_type = request.form["type"]
            amount = int(request.form["amount"])
        except:
            error = "Wrong data."
            flash(error)
            return redirect(url_for("index.change_purchase_item"))

        with Connect() as c:
            c.execute(
                """select exists(select * from purchase_item where purchase_name=? and item_id=? and type=?)""",
                (purchase_name, item_id, item_type),
            )
            if c.fetchone() == (0,):
                c.execute(
                    """select exists(select * from purchase where purchase_name=?)""",
                    (purchase_name,),
                )
                if c.fetchone() == (1,):
                    c.execute(
                        """select exists(select * from item where item_id=? and type=?)""",
                        (item_id, item_type),
                    )
                    if c.fetchone() == (1,):
                        c.execute(
                            """insert into purchase_item values(?,?,?,?)""",
                            (purchase_name, item_id, item_type, amount),
                        )
                        flash(
                            """Successfully add the purchase's item."""
                        )
                    else:
                        error = """The item does not exist."""
                else:
                    error = """The purchase does not exist."""
            else:
                error = """The purchase's item exists."""

        if error:
            flash(error)

    return render_template("web/changepurchaseitem.html")


@bp.route("/changepurchaseitem/delete", methods=["POST"])
@login_required
def change_purchase_item_delete():

    error = None
    try:
        purchase_name = request.form["purchase_name"]
        item_id = request.form["item_id"]
        item_type = request.form["type"]
    except:
        error = "Wrong data."
        flash(error)
        return redirect(url_for("index.change_purchase_item"))

    with Connect() as c:
        c.execute(
            """select exists(select * from purchase_item where purchase_name=? and item_id=? and type=?)""",
            (purchase_name, item_id, item_type),
        )
        if c.fetchone() == (1,):
            c.execute(
                """delete from purchase_item where purchase_name=? and item_id=? and type=?""",
                (purchase_name, item_id, item_type),
            )

            flash("""Successfully delete the purchase's item.""")
        else:
            error = """The purchase's item does not exist."""

    if error:
        flash(error)

    return render_template("web/changepurchaseitem.html")
