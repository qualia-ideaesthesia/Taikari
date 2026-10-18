# Taikari

A small, self-hosted **Arcaea** server written in Python with Flask.
It emulates the main online features of the game so a modified client can log in,
upload scores, play Link Play, download songs, and more.

> This project is a fork of [Lost-MSth/Arcaea-server](https://github.com/Lost-MSth/Arcaea-server).
> All credit for the original design and implementation goes to its author.
> See [Acknowledgements](#acknowledgements).

## Introduction

Taikari is a study/research project. It is **not** affiliated with, endorsed by, or
connected to the official Arcaea service. Do not use it for any commercial
purpose.

## Features

Legend: :x: not supported · :warning: possible issues / may differ from official ·
:wastebasket: no longer maintained · :construction: in construction

- Login and registration
  - Auto-ban of multiple devices
  - :warning: Multi-device login
  - Login rate limit
  - Register rate limit
  - :warning: Account deletion
- Score upload
  - Score validation
  - Score ranking
- Potential (PTT)
  - Best 30
  - :warning: Recent Top 10
- Global rank
- Course (段位) system
- :warning: Link Play 2.0
- Friends
  - :x: Max friend number increase
- Cloud save
  - Attempt to unlock all stories and songs
- World mode
  - Stamina system
  - :warning: Normal steps boost & beyond boost
  - :warning: Character skills
- Song downloading
  - :x: Encrypted downloading
  - Download validation
  - Download rate limit
- Content bundle hot update
- Purchase system
  - Singles and packs
  - :x: Pack bundles
  - Discounts
  - 5th anniversary ticket
  - Pick ticket
  - :x: Automatic Extend pack price reduction
- Present system
- Redeem code system
- Newbie missions
- Character system
- Data recording
  - Users' scores
  - Users' daily potential
- :wastebasket: Simple web admin backend
- :construction: API
- Server log

## Requirements

- Windows / Linux / macOS / Android …
- Python >= 3.6
  - `Flask` >= 2.0
  - `cryptography` >= 35.0.0
  - `limits` >= 2.7.0
- A production WSGI server, e.g. `waitress` (default), `gunicorn`, or `gevent`
- Optional: Charles / IDA / a proxy app for debugging the client

## Getting started

1. **Install dependencies**

   ```sh
   pip install -r requirements.txt
   pip install waitress        # required by the default deploy mode
   ```

2. **Configure credentials** (recommended before the first run)

   Copy `config.example.py` to `config.py` and edit the values:

   ```sh
   cp config.example.py config.py
   ```

   `config.py` is git-ignored, so your real credentials never end up in the
   repository. See [Configuration](#configuration) below.

3. **Run the server**

   ```sh
   python main.py
   ```

   On the first launch the database is created automatically under `database/`.
   The Link Play server is started as a subprocess (UDP `8001`, TCP `8002`).

4. **Open the web admin panel**

   Browse to `http://<host>:8000` and log in with `USERNAME` / `PASSWORD`.

## Configuration

Configuration lives in `core/config_manager.py`. Almost anything can be
overridden without editing that file:

- Create `config.py` next to `main.py` (see `config.example.py`).
- Or set `ARCAEA_SERVER_CONFIG` to the path of a Python config file.
- Or set `ARCAEA_JSON_CONFIG_PATH` to a JSON file.

Only the keys you define are applied; the rest keep their defaults.

### Important settings

| Key | Default | Notes |
| --- | --- | --- |
| `USERNAME` / `PASSWORD` | `admin` / `change-me` | Web admin panel login. **Change it.** |
| `SECRET_KEY` | `change-me-to-a-random-secret` | Flask session signing key. Use a long random string. |
| `API_TOKEN` | `""` | Global API token. Empty disables token-based API access. |
| `LINKPLAY_AUTHENTICATION` | `change-me-linkplay-authentication` | Link Play shared secret. |
| `LINKPLAY_TCP_SECRET_KEY` | `change-me-linkplay-tcp-secret` | Link Play TCP AES key. |
| `DEFAULT_ADMIN_PASSWORD` | `change-me-admin-password` | Password of the built-in `admin` game account, used only at first DB init. |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Web server bind address. |
| `LINKPLAY_UDP_PORT` / `LINKPLAY_TCP_PORT` | `8001` / `8002` | Link Play ports. |

### Security notes

- Change **all** placeholder values before exposing the server to a network.
  The server logs a warning at startup while insecure defaults remain.
- The Link Play secrets are shared between the game server and the Link Play
  server. You only need to set them in `config.py`; the Link Play server reads
  them automatically. Without a `config.py`, both sides use the same placeholder
  values, so Link Play keeps working out of the box.
- Use HTTPS (`SSL_CERT` / `SSL_KEY`) if the server is reachable from the internet.

### Song data

Since v2.9 the repository does **not** ship song charts or audio. Place your own
song files under `database/songs/` (see `SONG_FILE_FOLDER_PATH` and
`SONGLIST_FILE_PATH`). World map data is kept under `database/map/`.

## Link Play

Link Play (multiplayer) runs as a separate subprocess:

- UDP on `LINKPLAY_UDP_PORT` (default `8001`) for room/matchmaking traffic.
- TCP on `LINKPLAY_TCP_PORT` (default `8002`) for reliable messages.

It can also be started on its own:

```sh
python run_linkplay_server.py
```

Set `SET_LINKPLAY_SERVER_AS_SUB_PROCESS = False` to run it externally.

## Project structure

```
main.py                 # entry point, Flask app, subprocess management
api/                    # game-facing API routes
server/                 # game server logic (score, world, multiplayer, …)
web/                    # web admin backend
core/                   # shared models, config, SQL, initialization
linkplay_server/        # UDP/TCP Link Play server
database/               # schema, init data, world map data (runtime DB ignored)
config.example.py       # template for the optional local config
```

## Acknowledgements

- Original project: [Lost-MSth/Arcaea-server](https://github.com/Lost-MSth/Arcaea-server)
- Song database: [ArcaeaSongDatabase](https://github.com/Arcaea-Infinity/ArcaeaSongDatabase)
  and [its fork](https://github.com/CuSO4Deposit/ArcaeaSongDatabase)
  (song data is not provided since v2.9)
- Favicon: [black fate - てんてん - pixiv](https://www.pixiv.net/artworks/82374369)

## License

[MIT](LICENSE) © Lost
