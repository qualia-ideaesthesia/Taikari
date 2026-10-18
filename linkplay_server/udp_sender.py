from os import urandom
from time import time

from .udp_class import Room, b

PADDING = [b(i) * i for i in range(16)] + [b""]


class CommandSender:

    PROTOCOL_NAME = b"\x06\x16"
    PROTOCOL_VERSION = b"\x0e"

    def __init__(self, room: Room = None) -> None:
        self.room = room
        self.timestamp = round(time() * 1000000)
        self.room.timestamp = self.timestamp + 1

        self._random_code = None

    @property
    def random_code(self):
        if self._random_code is None:
            self._random_code = urandom(4) + b"\x00\x00\x00\x00"
        return self._random_code

    @random_code.setter
    def random_code(self, value):
        self._random_code = value

    @staticmethod
    def command_encode(t: tuple):
        r = b"".join(t)
        x = 16 - len(r) % 16
        return r + PADDING[x]

    def command_prefix(self, command: bytes):
        length = self.room.command_queue_length
        if b"\x10" <= command <= b"\x1f":
            length += 1

        return (
            self.PROTOCOL_NAME,
            command,
            self.PROTOCOL_VERSION,
            b(self.room.room_id, 8),
            b(length, 4),
        )

    def command_0c(self):
        return self.command_encode(
            (
                *self.command_prefix(b"\x0c"),
                self.random_code,
                b(self.room.state),
                b(self.room.countdown, 4),
                b(self.timestamp, 8),
            )
        )

    def command_0d(self, code: int):
        # 3 You are not the host
        # 5 A player cannot start right now
        # 6 More players are needed to start
        # 7 A player cannot play this song

        return self.command_encode(
            (*self.command_prefix(b"\x0d"), self.random_code, b(code))
        )

    def command_0e(self, player_index: int):
        # Score broadcast
        # I guess 616 got it wrong: first, the 4 bytes of 00 are probably because the score uses 8-byte conversion; second, the previous score isn't needed at all hahahaha!
        player = self.room.players[player_index]
        return self.command_encode(
            (
                *self.command_prefix(b"\x0e"),
                player.info,
                b(player.last_score.score, 4),
                b"\x00" * 4,
                b(player.last_score.timer, 4),
                b"\x00" * 4,
            )
        )

    def command_0f(self, player_index: int, song_idx: int):
        # Song recommendation
        player = self.room.players[player_index]
        return self.command_encode(
            (*self.command_prefix(b"\x0f"), b(player.player_id, 8), b(song_idx, 2))
        )

    def command_10(self):
        # Host announcement
        return self.command_encode(
            (*self.command_prefix(b"\x10"), self.random_code, b(self.room.host_id, 8))
        )

    def command_11(self):
        return self.command_encode(
            (
                *self.command_prefix(b"\x11"),
                self.random_code,
                self.room.get_players_info(),
            )
        )

    def command_12(self, player_index: int):
        player = self.room.players[player_index]
        return self.command_encode(
            (
                *self.command_prefix(b"\x12"),
                self.random_code,
                b(player_index),
                player.info,
            )
        )

    def command_13(self):
        return self.command_encode(
            (*self.command_prefix(b"\x13"), self.random_code, self.room.room_info)
        )

    def command_14(self):
        return self.command_encode(
            (*self.command_prefix(b"\x14"), self.random_code, self.room.song_unlock)
        )

    def command_15(self):
        return self.command_encode(
            (
                *self.command_prefix(b"\x15"),
                self.room.get_players_info(),
                self.room.song_unlock,
                self.room.room_info,
            )
        )

    def command_21(self, player_index: int, sticker_id: int):
        player = self.room.players[player_index]
        return self.command_encode(
            (*self.command_prefix(b"\x21"), b(player.player_id, 8), b(sticker_id, 2))
        )
