from base64 import b64encode
from os import urandom
from random import randint
from time import time

from flask import Blueprint, request

from core.constant import Constant
from core.course import CoursePlay
from core.error import InputError
from core.rank import RankList
from core.score import UserPlay
from core.sql import Connect
from core.user import UserOnline

from .auth import auth_required
from .func import arc_try, success_return

bp = Blueprint('score', __name__, url_prefix='/score')


@bp.route('/token', methods=['GET'])  # Token required for score upload
def score_token():
    # A random, single-use-shaped token. It is not persisted, so `get_play_state`
    # falls back to normal (non-world) mode, matching the previous behaviour
    # without relying on a hardcoded constant.
    return success_return({'token': b64encode(urandom(64)).decode()})


@bp.route('/token/world', methods=['GET'])  # Token required for world mode score upload
@auth_required(request)
@arc_try
def score_token_world(user_id):

    d = request.args.get

    stamina_multiply = max(1, d('stamina_multiply', 1, type=int))
    fragment_multiply = max(100, d('fragment_multiply', 100, type=int))
    prog_boost_multiply = max(0, d('prog_boost_multiply', 0, type=int))
    beyond_boost_gauge_use = max(0, d('beyond_boost_gauge_use', 0, type=int))
    skill_cytusii_flag = None
    skill_chinatsu_flag = None
    skill_id = d('skill_id')

    # check value

    if (skill_id == 'skill_ilith_ivy' or skill_id == 'skill_hikari_vanessa') and d('is_skill_sealed') == 'false':
        # Handle the ivy skill or the vanessa skill
        # TODO: The entire user_play needs refactoring for world mode / course mode, so this is a temporary workaround for now
        skill_cytusii_flag = ''.join([str(randint(0, 2)) for _ in range(5)])

    if skill_id == 'skill_chinatsu' and d('is_skill_sealed') == 'false':
        skill_chinatsu_flag = ''.join([str(randint(0, 2)) for _ in range(7)])
    skill_flag = skill_cytusii_flag or skill_chinatsu_flag

    with Connect() as c:
        x = UserPlay(c, UserOnline(c, user_id))
        x.song.set_chart(d('song_id'), d('difficulty', type=int))
        x.set_play_state_for_world(
            stamina_multiply, fragment_multiply, prog_boost_multiply, beyond_boost_gauge_use, skill_cytusii_flag, skill_chinatsu_flag)

        r = {
            "stamina": x.user.stamina.stamina,
            "max_stamina_ts": x.user.stamina.max_stamina_ts,
            "token": x.song_token,
            "play_parameters": {},
            "beyond_boost_gauge": x.user.beyond_boost_gauge
        }
        if skill_flag and skill_id:
            r['play_parameters'] = {
                skill_id: list(
                    map(lambda x: Constant.WORLD_VALUE_NAME_ENUM[int(x)], skill_flag)),
            }
        if x.invasion_flag == 1:
            r['play_parameters']['invasion_start'] = True
        elif x.invasion_flag == 2:
            r['play_parameters']['invasion_hard'] = True
        
        return success_return(r)


@bp.route('/token/course', methods=['GET'])  # Token required for course mode score upload
@auth_required(request)
@arc_try
def score_token_course(user_id):
    with Connect() as c:
        use_course_skip_purchase = request.args.get(
            'use_course_skip_purchase', 'false') == 'true'

        user = UserOnline(c, user_id)
        user_play = UserPlay(c, user)
        user_play.song_token = request.args.get('previous_token', None)
        user_play.get_play_state()

        status = 'created'
        if user_play.course_play_state == -1:
            # No token, course mode has just started
            course_play = CoursePlay(c, user, user_play)
            course_play.course_id = request.args['course_id']
            user_play.course_play = course_play
            user_play.set_play_state_for_course(
                use_course_skip_purchase)
        elif 0 <= user_play.course_play_state <= 3:
            # Validate token
            user_play.update_token_for_course()
        else:
            # Course mode has ended
            user_play.clear_play_state()
            user.select_user_about_stamina()
            status = 'cleared' if user_play.course_play_state == 4 else 'failed'

        return success_return({
            "stamina": user.stamina.stamina,
            "max_stamina_ts": user.stamina.max_stamina_ts,
            "token": user_play.song_token,
            'status': status
        })


@bp.route('/song', methods=['POST'])  # Score upload
@auth_required(request)
@arc_try
def song_score_post(user_id):
    # nell_toggle ?
    # gauge_level ? find with char 97
    with Connect() as c:
        x = UserPlay(c, UserOnline(c, user_id))
        f = request.form
        x.nell_toggle = request.args.get("nell_toggle",type=bool)
        
        x.song_token = f['song_token']
        x.song_hash = f['song_hash']
        x.song.set_chart(f['song_id'], f['difficulty'])
        x.set_score(f['score'], f['shiny_perfect_count'], f['perfect_count'], f['near_count'],
                    f['miss_count'], f['health'], f['modifier'], int(time() * 1000), f['clear_type'])
        x.beyond_gauge = int(f['beyond_gauge'])
        x.submission_hash = f['submission_hash']
        x.combo_interval_bonus = f.get('combo_interval_bonus', type=int)
        x.hp_interval_bonus = f.get('hp_interval_bonus', type=int)
        
        # visible_map_count
        x.fever_bonus = f.get('fever_bonus', type=int)
        x.rank_bonus = f.get('rank_bonus', type=int)
        x.maya_gauge = f.get('maya_gauge', type=int)
        x.nextstage_bonus = f.get('nextstage_bonus', type=int)
        x.highest_health = f.get("highest_health", type=int)
        x.lowest_health = f.get("lowest_health", type=int)
        x.room_code = f.get('room_code')
        x.room_total_score = f.get('room_total_score', type=int)
        x.room_total_players = f.get('room_total_players', type=int)
        
        if not x.is_valid:
            raise InputError('Invalid score.', 107)
        x.upload_score()
        # room_code???
        return success_return(x.to_dict())


@bp.route('/song', methods=['GET'])  # TOP20
@auth_required(request)
@arc_try
def song_score_top(user_id):
    with Connect() as c:
        rank_list = RankList(c)
        rank_list.song.set_chart(request.args.get(
            'song_id'), request.args.get('difficulty'))
        rank_list.select_top()
        return success_return(rank_list.to_dict_list())


@bp.route('/song/me', methods=['GET'])  # My rank, at most 20 by default
@auth_required(request)
@arc_try
def song_score_me(user_id):
    with Connect() as c:
        rank_list = RankList(c)
        rank_list.song.set_chart(request.args.get(
            'song_id'), request.args.get('difficulty'))
        rank_list.select_me(UserOnline(c, user_id))
        return success_return(rank_list.to_dict_list())


@bp.route('/song/friend', methods=['GET'])  # Friend rank, at most 50 by default
@auth_required(request)
@arc_try
def song_score_friend(user_id):
    with Connect() as c:
        rank_list = RankList(c)
        rank_list.song.set_chart(request.args.get(
            'song_id'), request.args.get('difficulty'))
        rank_list.select_friend(UserOnline(c, user_id))
        return success_return(rank_list.to_dict_list())
