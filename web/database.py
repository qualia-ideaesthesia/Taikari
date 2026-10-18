from flask import flash, redirect, render_template, request, url_for

from core.sql import Connect
from web.blueprint import bp
from web.login import login_required

import os

UPLOAD_FOLDER = "database"

from werkzeug.utils import secure_filename

from core.init import FileChecker
from core.operation import (
    RefreshAllScoreRating,
    RefreshBundleCache,
    RefreshSongFileCache,
    RefreshWorldMapCache,
)
from web.helpers import allowed_file, is_number


@bp.route("/updatedatabase", methods=["GET", "POST"])
@login_required
def update_database():
    error = None
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part.")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("No selected file.")
            return redirect(request.url)

        if (
            file
            and allowed_file(file.filename)
            and file.filename in ["arcaea_database.db"]
        ):
            filename = "old_" + secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            flash("Success upload.")
            try:
                FileChecker.update_database(os.path.join(UPLOAD_FOLDER, filename))
                flash("Success update data.")
            except:
                flash("Cannot update data.")
        else:
            error = "Upload error."

        if error:
            flash(error)

    return render_template("web/updatedatabase.html")


@bp.route("/updatedatabase/refreshsonghash", methods=["POST"])
@login_required
def update_song_hash():
    try:
        RefreshSongFileCache().run()
        flash("Success refresh data.")
    except:
        flash("Something error!")
    return render_template("web/updatedatabase.html")


@bp.route("/updatedatabase/refreshsbundle", methods=["POST"])
@login_required
def update_content_bundle():
    try:
        RefreshBundleCache().run()
        flash("Success refresh data.")
    except:
        flash("Something error!")
    return render_template("web/updatedatabase.html")


@bp.route("/updatedatabase/refreshworldmap", methods=["POST"])
@login_required
def update_world_map():
    try:
        RefreshWorldMapCache().run()
        flash("Success refresh data.")
    except:
        flash("Something error!")
    return render_template("web/updatedatabase.html")


@bp.route("/updatedatabase/refreshsongrating", methods=["POST"])
@login_required
def update_song_rating():
    RefreshAllScoreRating().run()
    flash("Success refresh data.")
    return render_template("web/updatedatabase.html")


@bp.route("/changesong", methods=["GET"])
@login_required
def change_song():
    return render_template("web/changesong.html")


@bp.route("/changesong/addsong", methods=["POST"])
@login_required
def add_song():
    def get_rating(x):
        if is_number(x):
            x = float(x)
            if x >= 0:
                return int(x * 10)
            else:
                return -1
        else:
            return -1

    error = None
    song_id = request.form["sid"]
    name_en = request.form["name_en"]
    rating_pst = get_rating(request.form["rating_pst"])
    rating_prs = get_rating(request.form["rating_prs"])
    rating_ftr = get_rating(request.form["rating_ftr"])
    rating_byd = get_rating(request.form["rating_byd"])
    rating_etr = get_rating(request.form["rating_etr"])
    if len(song_id) >= 256:
        song_id = song_id[:200]
    if len(name_en) >= 256:
        name_en = name_en[:200]

    with Connect() as c:
        c.execute(
            """select exists(select * from chart where song_id=:a)""", {"a": song_id}
        )
        if c.fetchone() == (0,):
            c.execute(
                """insert into chart values(:a,:b,:c,:d,:e,:f,:g)""",
                {
                    "a": song_id,
                    "b": name_en,
                    "c": rating_pst,
                    "d": rating_prs,
                    "e": rating_ftr,
                    "f": rating_byd,
                    "g": rating_etr,
                },
            )
            flash("Successfully add the song.")
        else:
            error = "The song exists."

    if error:
        flash(error)

    return redirect(url_for("index.change_song"))


@bp.route("/changesong/deletesong", methods=["POST"])
@login_required
def delete_song():

    error = None
    song_id = request.form["sid"]
    with Connect() as c:
        c.execute(
            """select exists(select * from chart where song_id=:a)""", {"a": song_id}
        )
        if c.fetchone() == (1,):
            c.execute("""delete from chart where song_id=:a""", {"a": song_id})
            flash("Successfully delete the song.")
        else:
            error = "The song doesn't exist."

    if error:
        flash(error)

    return redirect(url_for("index.change_song"))
