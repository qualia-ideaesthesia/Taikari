from flask import flash, redirect, render_template, request, url_for

from core.sql import Connect
from web.blueprint import bp
from web.login import login_required

import web.system


@bp.route("/allchar", methods=["GET"])
@login_required
def all_character():
    error = None
    with Connect() as c:
        c.execute("""select * from character""")
        x = c.fetchall()
        if x:
            posts = []
            for i in x:
                posts.append(
                    {
                        "character_id": i[0],
                        "name": i[1],
                        "max_level": i[2],
                        "frag1": i[3],
                        "prog1": i[4],
                        "overdrive1": i[5],
                        "frag20": i[6],
                        "prog20": i[7],
                        "overdrive20": i[8],
                        "frag30": i[9],
                        "prog30": i[10],
                        "overdrive30": i[11],
                        "skill_id": i[12],
                        "skill_unlock_level": i[13],
                        "skill_id_uncap": i[15],
                        "char_type": i[16],
                        "is_uncapped": i[17] == 1,
                    }
                )
        else:
            error = "No character data."

    if error:
        flash(error)
        return render_template("web/allchar.html")
    else:
        return render_template("web/allchar.html", posts=posts)


@bp.route("/changechar", methods=["GET"])
@login_required
def change_character():
    skill_ids = [
        "No_skill",
        "gauge_easy",
        "note_mirror",
        "gauge_hard",
        "frag_plus_10_pack_stellights",
        "gauge_easy|frag_plus_15_pst&prs",
        "gauge_hard|fail_frag_minus_100",
        "frag_plus_5_side_light",
        "visual_hide_hp",
        "frag_plus_5_side_conflict",
        "challenge_fullcombo_0gauge",
        "gauge_overflow",
        "gauge_easy|note_mirror",
        "note_mirror",
        "visual_tomato_pack_tonesphere",
        "frag_rng_ayu",
        "gaugestart_30|gaugegain_70",
        "combo_100-frag_1",
        "audio_gcemptyhit_pack_groovecoaster",
        "gauge_saya",
        "gauge_chuni",
        "kantandeshou",
        "gauge_haruna",
        "frags_nono",
        "gauge_pandora",
        "gauge_regulus",
        "omatsuri_daynight",
        "sometimes(note_mirror|frag_plus_5)",
        "scoreclear_aa|visual_scoregauge",
        "gauge_tempest",
        "gauge_hard",
        "gauge_ilith_summer",
        "frags_kou",
        "visual_ink",
        "shirabe_entry_fee",
        "frags_yume",
        "note_mirror|visual_hide_far",
        "frags_ongeki",
        "gauge_areus",
        "gauge_seele",
        "gauge_isabelle",
        "gauge_exhaustion",
        "skill_lagrange",
        "gauge_safe_10",
        "frags_nami",
        "skill_elizabeth",
        "skill_lily",
        "skill_kanae_midsummer",
        "eto_uncap",
        "luna_uncap",
        "frags_preferred_song",
        "visual_ghost_skynotes",
        "ayu_uncap",
        "skill_vita",
        "skill_fatalis",
        "skill_reunion",
        "frags_ongeki_slash",
        "frags_ongeki_hard",
        "skill_amane",
        "skill_kou_winter",
        "gauge_hard|note_mirror",
        "skill_shama",
        "skill_milk",
        "skill_shikoku",
        "skill_mika",
        "ilith_awakened_skill",
        "skill_mithra",
        "skill_toa",
        "skill_nami_twilight",
        "skill_ilith_ivy",
        "skill_hikari_vanessa",
        "skill_maya",
        "skill_luin",
        "skill_luin_uncap",
        "skill_kanae_uncap",
        "skill_doroc_uncap",
        "skill_saya_uncap",
        "skill_luna_ilot",
        "skill_eto_hoppe",
        "skill_aichan",
        "skill_nell",
        "skill_chinatsu",
        "skill_tsumugi",
        "skill_nai",
        "skill_selene",
        "skill_salt",
        "skill_acid",
        "skill_hikari_selene",
        "skill_hikari_clear",
        "skill_tairitsu_fail",
        "skill_nami_sui",
        "skill_nonoka",
        "skill_nonoka_uncap",
        "skill_vita_arc",
        "skill_maya_uncap",
        "skill_hikari_tairitsu_debut",
        "skill_hp_slow_drain",
        "skill_lost_to_85",
        "skill_hprate_based_on_hp",
        "skill_frag_doubled_after_earning_X",
        "skill_insight_konzetsu",
        "skill_saya_konzetsu",
    ]
    return render_template("web/changechar.html", skill_ids=skill_ids)


@bp.route("/changesong/editchar", methods=["POST"])
@login_required
def edit_char():

    error = None

    try:
        character_id = int(request.form["id"])
        level = request.form["level"]
        skill_id = request.form["skill_id"]
        skill_id_uncap = request.form["skill_id_uncap"]
        if level:
            level = int(level)
        else:
            level = None
    except:
        error = "Wrong data."
        flash(error)
        return redirect(url_for("index.change_character"))

    with Connect() as c:
        c.execute(
            """select exists(select * from character where character_id=:a)""",
            {"a": character_id},
        )
        if c.fetchone() == (1,):
            if level is None and skill_id is None and skill_id_uncap is None:
                error = "No change."
            else:
                sql = """update character set """
                sql_dict = {"character_id": character_id}
                if level is not None:
                    sql += "max_level = :level, "
                    sql_dict["level"] = level
                if skill_id is not None:
                    sql += "skill_id = :skill_id, "
                    if skill_id == "No_skill":
                        sql_dict["skill_id"] = ""
                    else:
                        sql_dict["skill_id"] = skill_id
                if skill_id_uncap is not None:
                    sql += "skill_id_uncap = :skill_id_uncap, "
                    if skill_id_uncap == "No_skill":
                        sql_dict["skill_id_uncap"] = ""
                    else:
                        sql_dict["skill_id_uncap"] = skill_id_uncap

                sql = sql[:-2]
                sql += " where character_id = :character_id"
                c.execute(sql, sql_dict)
                flash("Successfully edit the character.")
        else:
            error = "The character does not exist."

    if error:
        flash(error)

    return redirect(url_for("index.change_character"))


@bp.route("/changesong/updatechar", methods=["POST"])
@login_required
def update_character():
    with Connect() as c:
        web.system.update_user_char(c)

    flash("Success update data.")
    return redirect(url_for("index.change_character"))
