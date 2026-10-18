from flask import Blueprint, current_app, request

from core.error import DataExist, InputError, NoData
from core.rank import RankList
from core.song import Song
from core.sql import Connect, Query, Sql

from .api_auth import api_try, request_json_handle, role_required
from .api_code import success_return
from .constant import Constant
from os import path
import json

bp = Blueprint("songs", __name__, url_prefix="/songs")


@bp.route("/<string:song_id>", methods=["GET"])
@role_required(request, ["select", "select_song_info"])
@api_try
def songs_song_get(user, song_id):
    """Query song info"""
    with Connect() as c:
        s = Song(c, song_id).select()
        return success_return(s.to_dict())


@bp.route("/<string:song_id>", methods=["PUT"])
@role_required(request, ["change"])
@request_json_handle(request, optional_keys=["name", "charts"], must_change=True)
@api_try
def songs_song_put(data, user, song_id):
    """Modify song info"""
    with Connect() as c:
        s = Song(c, song_id).select()
        if "name" in data:
            s.name = str(data["name"])
        if "charts" in data:
            for i in data["charts"]:
                if "difficulty" in i and "chart_const" in i:
                    s.charts[i["difficulty"]].defnum = round(i["chart_const"] * 10)

        s.update()
        return success_return(s.to_dict())


@bp.route("/<string:song_id>", methods=["DELETE"])
@role_required(request, ["change"])
@api_try
def songs_song_delete(user, song_id):
    """Delete song info"""
    with Connect() as c:
        s = Song(c, song_id)
        if not s.select_exists():
            raise NoData(f"No such song: `{song_id}`")
        s.delete()
        return success_return()


_songlist_cache = None
_songlist_loaded = False


def _get_songlist():
    """Lazily load the song metadata file used to enrich song responses.

    Loading at import time made the whole application fail to start when the
    file was missing, so it is read on first use instead. When the file is
    absent the enrichment is skipped instead of failing the request.
    """
    global _songlist_cache, _songlist_loaded
    if not _songlist_loaded:
        _songlist_loaded = True
        songlist_path = path.join(
            path.dirname(__file__), "..", "database", "songs", "songlist"
        )
        if path.isfile(songlist_path):
            with open(songlist_path) as file:
                _songlist_cache = json.load(file)["songs"]
        else:
            _songlist_cache = []
            current_app.logger.warning(
                "Song list file not found at %s; "
                "song responses will omit set/version.",
                path.abspath(songlist_path),
            )
    return _songlist_cache


@bp.route("", methods=["GET"])
@role_required(request, ["select", "select_song_info"])
@request_json_handle(request, optional_keys=Constant.QUERY_KEYS)
@api_try
def songs_get(data, user):
    """Query all song info"""
    A = ["song_id", "name"]
    B = [
        "song_id",
        "name",
        "rating_pst",
        "rating_prs",
        "rating_ftr",
        "rating_byn",
        "rating_etr",
    ]
    with Connect() as c:
        query = Query(A, A, B).from_dict(data)
        if data.get("count_only", False):
            return success_return({"count": Sql(c).select_count("chart", query)})
        x = Sql(c).select("chart", query=query)
        r = []
        for i in x:
            r.append(Song(c).from_list(i))

        if not r:
            raise NoData(api_error_code=-2)

        songs = [x.to_dict() for x in r]
        songlist = _get_songlist()
        for song in songs:
            songlist_song = next(
                (item for item in songlist if item["id"] == song["song_id"]),
                None,
            )
            if songlist_song is not None:
                song["set"] = songlist_song["set"]
                song["version"] = songlist_song["version"]

        return success_return(songs)


@bp.route("", methods=["POST"])
@role_required(request, ["change"])
@request_json_handle(request, ["song_id", "charts"], ["name"])
@api_try
def songs_post(data, user):
    """Add song info"""
    with Connect() as c:
        s = Song(c).from_dict(data)
        if s.select_exists():
            raise DataExist(f"Song `{s.song_id}` already exists")
        s.insert()
        return success_return(s.to_dict())


@bp.route("/<string:song_id>/<int:difficulty>/rank", methods=["GET"])
@role_required(request, ["select", "select_song_rank", "select_song_rank_top"])
@request_json_handle(request, optional_keys=["limit"])
@api_try
def songs_song_difficulty_rank_get(data, user, song_id, difficulty):
    """Query the score rank list for a song difficulty, similar to the in-game API, only limit is allowed"""
    if difficulty not in [0, 1, 2, 3, 4]:
        raise InputError("Difficulty must be 0, 1, 2, 3 or 4")
    limit = data.get("limit", 20)
    if not isinstance(limit, int):
        raise InputError("Limit must be int")
    if user.role.only_has_powers(
        ["select_song_rank_top"], ["select", "select_song_rank"]
    ):
        # Restrict low-permission users to querying only the top 20
        if limit > 20 or limit < 0:
            limit = 20
    with Connect() as c:
        rank_list = RankList(c)
        rank_list.song.set_chart(song_id, difficulty)
        rank_list.limit = limit
        # Does not check whether the song exists; if it does not, an empty list is returned
        rank_list.select_top()
        return success_return(rank_list.to_dict_list())
