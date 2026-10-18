import logging
from base64 import b64decode, b64encode
from os import urandom
from secrets import choice
from threading import RLock
from time import time

from .config import Config
from .udp_class import Player, Room, bi
from .udp_sender import CommandSender


class Store:
    # token: {'key': key, 'room': Room, 'player_index': player_index, 'player_id': player_id}
    link_play_data = {}
    room_id_dict: "dict[int, Room]" = {}  # 'room_id': Room
    room_code_dict = {}  # 'room_code': Room
    player_dict = {}  # 'player_id' : Player

    share_token_dict = {}  # 'share_token': Room

    lock = RLock()


ROOM_CODE_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ROOM_CODE_DIGITS = "0123456789"
SHARE_TOKEN_CHARSET = "abcdefghijklmnopqrstuvwxyz0123456789"


def random_room_code():
    # A room code is 4 uppercase letters followed by 2 digits.
    return "".join(choice(ROOM_CODE_LETTERS) for _ in range(4)) + "".join(
        choice(ROOM_CODE_DIGITS) for _ in range(2)
    )


def random_share_token():
    return "".join(choice(SHARE_TOKEN_CHARSET) for _ in range(10))


def unique_random(dataset, length=8, random_func=None):
    """Unique random, defaults to non-zero; does not handle possible infinite loops"""
    if random_func is None:
        x = bi(urandom(length))
        while x in dataset or x == 0:
            x = bi(urandom(length))
    else:
        x = random_func()
        while x in dataset:
            x = random_func()
    return x


def clear_player(token):
    # Clear player info and token
    with Store.lock:
        data = Store.link_play_data.get(token)
        if data is None:
            return
        player_id = data["player_id"]
        player = Store.player_dict.get(player_id)
        if player is not None:
            logging.info(f"Clean player `{player.name}`")
            del Store.player_dict[player_id]
        Store.link_play_data.pop(token, None)


def clear_room(room):
    # Clear room info
    room_id = room.room_id
    room_code = room.room_code
    share_token = room.share_token
    logging.info(f"Clean room `{room_code}`")
    with Store.lock:
        if room_id in Store.room_id_dict:
            del Store.room_id_dict[room_id]
        if room_code in Store.room_code_dict:
            del Store.room_code_dict[room_code]
        if share_token in Store.share_token_dict:
            del Store.share_token_dict[share_token]


def memory_clean(now):
    # Memory cleanup, handles players exiting abnormally
    #
    # Snapshot the dictionaries under the store lock, then inspect rooms
    # without holding it. Holding Store.lock while walking every room (and
    # taking each room lock) stalled the UDP hot path, which needs Store.lock
    # just to resolve a token.
    with Store.lock:
        data_snapshot = list(Store.link_play_data.items())
        room_snapshot = list(Store.room_id_dict.items())

    clean_room_list = set()
    clean_player_list = set()

    for token, v in data_snapshot:
        room = v["room"]
        with room.lock:
            if now - room.timestamp >= Config.TIME_LIMIT_US:
                clean_room_list.add(room.room_id)

            player = room.players[v["player_index"]]
            if (
                player.last_timestamp
                and now - player.last_timestamp >= Config.TIME_LIMIT_US
            ):
                clean_player_list.add(token)

    for room_id, room in room_snapshot:
        with room.lock:
            if now - room.timestamp >= Config.TIME_LIMIT_US:
                clean_room_list.add(room_id)

    for room_id in clean_room_list:
        room = Store.room_id_dict.get(room_id)
        if room is not None:
            clear_room(room)

    for token in clean_player_list:
        clear_player(token)


class TCPRouter:
    clean_timer = 0
    router = {
        "debug",
        "create_room",
        "join_room",
        "update_room",
        "get_rooms",
        "select_room",
        "get_match_rooms",
    }

    def __init__(self, raw_data: "dict | list"):
        self.raw_data = raw_data  # data: dict {endpoint: str, data: dict}
        self.data = raw_data["data"]
        self.endpoint = raw_data["endpoint"]

    def debug(self) -> dict:
        # Kept as a simple liveness probe. The previous implementation ran
        # `eval()` on a client-supplied string, which is a remote code
        # execution risk even behind the DEBUG flag.
        return {"hello_world": "ok"}

    @staticmethod
    def clean_check():
        now = round(time() * 1000000)
        if now - TCPRouter.clean_timer >= Config.TIME_LIMIT_US:
            logging.info("Start cleaning memory...")
            TCPRouter.clean_timer = now
            memory_clean(now)

    def handle(self) -> dict:
        self.clean_check()
        if self.endpoint not in self.router:
            return {"code": 999}
        try:
            r = getattr(self, self.endpoint)()
        except Exception as e:
            logging.error(e)
            return {"code": 999}
        if isinstance(r, int):
            return {"code": r}
        return {"code": 0, "data": r}

    @staticmethod
    def generate_player(name: str) -> Player:
        player_id = unique_random(Store.player_dict, 3)
        player = Player()
        player.player_id = player_id
        player.set_player_name(name)

        Store.player_dict[player_id] = player

        return player

    @staticmethod
    def generate_room() -> Room:
        room_id = unique_random(Store.room_id_dict)
        room = Room()
        room.room_id = room_id
        room.timestamp = round(time() * 1000000)
        Store.room_id_dict[room_id] = room

        room_code = unique_random(Store.room_code_dict, random_func=random_room_code)
        room.room_code = room_code
        Store.room_code_dict[room_code] = room

        share_token = unique_random(
            Store.share_token_dict, random_func=random_share_token
        )
        room.share_token = share_token
        Store.share_token_dict[share_token] = room

        return room

    def create_room(self) -> dict:
        # Create room
        # data = ['1', name, song_unlock, ]
        # song_unlock: base64 str
        name = self.data["name"]
        song_unlock = b64decode(self.data["song_unlock"])
        rating_ptt = self.data.get("rating_ptt", 0)
        is_hide_rating = self.data.get("is_hide_rating", False)
        match_times = self.data.get("match_times", None)

        key = urandom(16)
        with Store.lock:
            room = self.generate_room()
            player = self.generate_player(name)

            player.song_unlock = song_unlock
            player.rating_ptt = rating_ptt
            player.is_hide_rating = is_hide_rating
            player.player_index = 0
            room.song_unlock = song_unlock
            room.host_id = player.player_id
            room.players[0] = player

            token = room.room_id
            player.token = token

            # Match mode append
            if match_times is not None:
                room.is_public = 1
                room.round_mode = 3
                room.timed_mode = 1

            Store.link_play_data[token] = {
                "key": key,
                "room": room,
                "player_index": 0,
                "player_id": player.player_id,
            }

        logging.info(f"TCP-Create room `{room.room_code}` by player `{name}`")
        return {
            "room_code": room.room_code,
            "room_id": room.room_id,
            "token": token,
            "key": b64encode(key).decode("utf-8"),
            "player_id": player.player_id,
        }

    def join_room(self) -> "dict | int":
        # Join room
        # data = ['2', name, song_unlock, room_code]
        # song_unlock: base64 str
        room_code = self.data["room_code"].upper()
        key = urandom(16)
        name = self.data["name"]
        song_unlock = b64decode(self.data["song_unlock"])
        rating_ptt = self.data.get("rating_ptt", 0)
        is_hide_rating = self.data.get("is_hide_rating", False)
        match_times = self.data.get("match_times", None)

        with Store.lock:
            if room_code not in Store.room_code_dict:
                # Wrong room code / room does not exist
                return 1202
            room: Room = Store.room_code_dict[room_code]

            player_num = room.player_num
            if player_num == 4:
                # Room full
                return 1201
            if player_num == 0:
                # Room does not exist
                return 1202
            if room.state not in (0, 1, 2) or (room.is_public and match_times is None):
                # Cannot join
                return 1205

            token = unique_random(Store.link_play_data)

            player = self.generate_player(name)
            player.token = token
            player.song_unlock = song_unlock
            player.rating_ptt = rating_ptt
            player.is_hide_rating = is_hide_rating
            room.update_song_unlock()
            for i in range(4):
                if room.players[i].player_id == 0:
                    room.players[i] = player
                    player.player_index = i
                    break
            Store.link_play_data[token] = {
                "key": key,
                "room": room,
                "player_index": player.player_index,
                "player_id": player.player_id,
            }

        logging.info(f"TCP-Player `{name}` joins room `{room_code}`")
        return {
            "room_code": room_code,
            "room_id": room.room_id,
            "token": token,
            "key": b64encode(key).decode("utf-8"),
            "player_id": player.player_id,
            "song_unlock": b64encode(room.song_unlock).decode("utf-8"),
        }

    def update_room(self) -> dict:
        # Room info update
        # data = ['3', token]
        token = int(self.data["token"])
        rating_ptt = self.data.get("rating_ptt", 0)
        is_hide_rating = self.data.get("is_hide_rating", False)

        # Resolve the room under the store lock, then release it before taking
        # the room lock so a busy room cannot block other token lookups.
        with Store.lock:
            if token not in Store.link_play_data:
                return 108
            r = Store.link_play_data[token]

        room = r["room"]
        with room.lock:
            # Update player info
            player_index = r["player_index"]
            player = room.players[player_index]
            changed = (
                player.rating_ptt != rating_ptt
                or player.is_hide_rating != is_hide_rating
            )
            player.rating_ptt = rating_ptt
            player.is_hide_rating = is_hide_rating
            cs = CommandSender(room)
            # Only broadcast a player-info command when something actually
            # changed; frequent no-op update calls used to append a
            # command_12 every time, adding queue churn for all players.
            if changed:
                room.append_command(cs.command_12(player_index))

            logging.info(f"TCP-Room `{room.room_code}` info update")
            return {
                "room_code": room.room_code,
                "room_id": room.room_id,
                "key": b64encode(r["key"]).decode("utf-8"),
                # changed from room.players[r['player_index']].player_id,
                "player_id": r["player_id"],
                "song_unlock": b64encode(room.song_unlock).decode("utf-8"),
            }

    def get_rooms(self) -> dict:
        # Get room list and detailed info
        offset = int(self.data.get("offset", 0))
        if offset < 0:
            offset = 0
        limit = min(int(self.data.get("limit", 100)), 100)
        if limit < 0:
            limit = 100

        # Snapshot the room list under the store lock, then inspect the rooms
        # without holding it, so the UDP hot path (which needs Store.lock for
        # token lookups) is not stalled while building a room list.
        with Store.lock:
            room_list = list(Store.room_id_dict.values())

        n = 0
        m = 0
        rooms = []
        f = False
        f2 = False

        for room in room_list:
            with room.lock:
                if room.player_num == 0:
                    continue
                if m < offset:
                    m += 1
                    continue
                if f:
                    f2 = True
                    break
                n += 1
                rooms.append(room.to_dict())
                if n >= limit:
                    f = True

        return {
            "amount": n,
            "offset": offset,
            "limit": limit,
            "has_more": f2,
            "rooms": rooms,
        }

    def select_room(self) -> dict:
        # Query room info
        room_code = self.data.get("room_code", None)
        share_token = self.data.get("share_token", None)

        # Resolve the room under the store lock, then release it before taking
        # the room lock.
        with Store.lock:
            if room_code is not None:
                room = Store.room_code_dict.get(room_code, None)
            elif share_token is not None:
                room = Store.share_token_dict.get(share_token, None)
            else:
                room = None

        if room is None:
            return 108

        with room.lock:
            return {
                "room_id": room.room_id,
                "room_code": room.room_code,
                "share_token": room.share_token,
                "is_enterable": room.is_enterable,
                "is_matchable": room.is_matchable,
                "is_playing": room.is_playing,
                "is_public": room.is_public == 1,
                "timed_mode": room.timed_mode == 1,
            }

    def get_match_rooms(self):
        # Snapshot the room list under the store lock, then inspect the rooms
        # without holding it, so the UDP hot path is not stalled.
        with Store.lock:
            room_list = list(Store.room_id_dict.values())

        n = 0
        rooms = []
        for room in room_list:
            with room.lock:
                if not room.is_matchable:
                    continue

                rooms.append(
                    {
                        "room_id": room.room_id,
                        "room_code": room.room_code,
                        "share_token": room.share_token,
                        "is_matchable": room.is_matchable,
                        "next_state_timestamp": room.next_state_timestamp,
                        "song_unlock": b64encode(room.song_unlock).decode("utf-8"),
                        "players": [
                            {
                                "player_id": i.player_id,
                                "name": i.name,
                                "rating_ptt": i.rating_ptt,
                            }
                            for i in room.players
                        ],
                    }
                )
                n += 1
                if n >= 100:
                    break

        return {"amount": n, "rooms": rooms}
