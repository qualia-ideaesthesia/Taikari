from flask import flash, render_template, request

from core.sql import Connect
from web.blueprint import bp
from web.login import login_required

import time

from core.rank import RankList
from core.score import Potential
from core.user import User
from web.helpers import format_user_row, get_user, get_user_score, resolve_user_id


@bp.route("/index")
@bp.route("/")
@login_required
def index():
    return render_template("web/index.html")


@bp.route("/singleplayer", methods=["POST", "GET"])
@login_required
def single_player_score():
    if request.method == "POST":
        name = request.form["name"]
        user_code = request.form["user_code"]
        error = None
        if name or user_code:
            with Connect() as c:
                user_id = resolve_user_id(c, name, user_code)
                posts = []
                if user_id:
                    posts = get_user_score(c, user_id)
                    if not posts:
                        error = "No score."
                else:
                    error = "The player does not exist."

        else:
            error = "Null Input."

        if error:
            flash(error)
        else:
            return render_template("web/singleplayer.html", posts=posts)

    return render_template("web/singleplayer.html")


@bp.route("/singleplayerptt", methods=["POST", "GET"])
@login_required
def single_player_ptt():
    if request.method == "POST":
        name = request.form["name"]
        user_code = request.form["user_code"]
        error = None
        if name or user_code:
            with Connect() as c:
                user_id = resolve_user_id(c, name, user_code)
                posts = []
                if user_id:
                    user = get_user(c, user_id)
                    posts = get_user_score(c, user_id, 30)
                    u = User()
                    u.user_id = user_id
                    p = Potential(c, u)
                    recentptt = p.recent_10 / 10
                    recent = p.recent_30_to_dict_list()
                    if not posts:
                        error = "No score."
                    else:
                        bestptt = 0
                        for i in posts:
                            if i["rating"]:
                                bestptt += i["rating"]
                        bestptt = bestptt / 30
                else:
                    error = "The player does not exist."

        else:
            error = "Null Input."

        if error:
            flash(error)
        else:
            return render_template(
                "web/singleplayerptt.html",
                posts=posts,
                user=user,
                recent=recent,
                recentptt=recentptt,
                bestptt=bestptt,
            )

    return render_template("web/singleplayerptt.html")


@bp.route("/allplayer", methods=["GET"])
@login_required
def all_player():
    error = None
    with Connect() as c:
        c.execute("""select * from user order by rating_ptt DESC""")
        x = c.fetchall()
        if x:
            posts = [format_user_row(i) for i in x]
        else:
            error = "No player data."

    if error:
        flash(error)
        return render_template("web/allplayer.html")
    else:
        return render_template("web/allplayer.html", posts=posts)


@bp.route("/allsong", methods=["GET"])
@login_required
def all_song():
    def defnum(x):
        if x >= 0:
            return x / 10
        else:
            return None

    error = None
    with Connect() as c:
        c.execute("""select * from chart""")
        x = c.fetchall()
        if x:
            posts = []
            for i in x:
                posts.append(
                    {
                        "song_id": i[0],
                        "name_en": i[1],
                        "rating_pst": defnum(i[2]),
                        "rating_prs": defnum(i[3]),
                        "rating_ftr": defnum(i[4]),
                        "rating_byn": defnum(i[5]),
                        "rating_etr": defnum(i[6]),
                    }
                )
        else:
            error = "No song data."

    if error:
        flash(error)
        return render_template("web/allsong.html")
    else:
        return render_template("web/allsong.html", posts=posts)


@bp.route("/singlecharttop", methods=["GET", "POST"])
@login_required
def single_chart_top():
    if request.method == "POST":
        song_name = request.form["sid"]
        difficulty = request.form["difficulty"]
        if difficulty.isdigit():
            difficulty = int(difficulty)
        else:
            difficulty = 0
        error = None
        x = None
        with Connect() as c:
            song_name = "%" + song_name + "%"
            c.execute(
                """select song_id, name from chart where song_id like :a limit 1""",
                {"a": song_name},
            )
            x = c.fetchone()

            if x:
                y = RankList(c)
                y.song.set_chart(x[0], difficulty)
                y.limit = -1
                y.select_top()
                posts = y.to_dict_list()
                for i in posts:
                    i["time_played"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(i["time_played"])
                    )
            else:
                error = "No song."

        if not error:
            return render_template(
                "web/singlecharttop.html",
                posts=posts,
                song_name_en=x[1],
                song_id=x[0],
                difficulty=difficulty,
            )
        else:
            flash(error)

    return render_template("web/singlecharttop.html")
