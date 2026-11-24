"""Núcleo de domínio: repositório em memória compartilhado pelas 4 tecnologias.

Todos os servidores são adaptadores finos sobre esta classe. Assim, as
diferenças medidas nos testes de carga vêm do protocolo/serialização/framework
e não da lógica de negócio.

Modelo (conforme o diagrama do enunciado):
  Usuário (id, nome, idade) 1 --- 0..* Playlist (id, nome) 0..* --- 1..* Música
Decisão de projeto: a cardinalidade 1..* de música por playlist é tratada como
"recomendada" (permitimos playlist vazia na criação e ao remover a última
música), para manter as operações CRUD simples e idempotentes.
"""
import random
import threading

from .config import SEED
from .errors import Invalid, NotFound


def _name(value, field="name"):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise Invalid(f"'{field}' must be a non-empty string (max 200 chars)")
    return value.strip()


def _age(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 150:
        raise Invalid("'age' must be an integer between 0 and 150")
    return value


def _pl(p):
    return {"id": p["id"], "name": p["name"], "user_id": p["user_id"],
            "song_ids": list(p["song_ids"])}


class Store:
    def __init__(self):
        self._lock = threading.RLock()
        self._users, self._songs, self._playlists = {}, {}, {}
        self._seq = {"user": 0, "song": 0, "playlist": 0}

    def _next(self, kind):
        self._seq[kind] += 1
        return self._seq[kind]

    # ------------------------------------------------------------ users
    def list_users(self):
        with self._lock:
            return [dict(u) for u in self._users.values()]

    def get_user(self, user_id):
        with self._lock:
            if user_id not in self._users:
                raise NotFound(f"user {user_id} not found")
            return dict(self._users[user_id])

    def create_user(self, name, age):
        name, age = _name(name), _age(age)
        with self._lock:
            uid = self._next("user")
            self._users[uid] = {"id": uid, "name": name, "age": age}
            return dict(self._users[uid])

    def update_user(self, user_id, name, age):
        name, age = _name(name), _age(age)
        with self._lock:
            self.get_user(user_id)
            self._users[user_id].update(name=name, age=age)
            return dict(self._users[user_id])

    def delete_user(self, user_id):
        with self._lock:
            self.get_user(user_id)
            del self._users[user_id]
            for pid in [i for i, p in self._playlists.items() if p["user_id"] == user_id]:
                del self._playlists[pid]  # cascata

    # ------------------------------------------------------------ songs
    def list_songs(self):
        with self._lock:
            return [dict(s) for s in self._songs.values()]

    def get_song(self, song_id):
        with self._lock:
            if song_id not in self._songs:
                raise NotFound(f"song {song_id} not found")
            return dict(self._songs[song_id])

    def create_song(self, name, artist):
        name, artist = _name(name), _name(artist, "artist")
        with self._lock:
            sid = self._next("song")
            self._songs[sid] = {"id": sid, "name": name, "artist": artist}
            return dict(self._songs[sid])

    def update_song(self, song_id, name, artist):
        name, artist = _name(name), _name(artist, "artist")
        with self._lock:
            self.get_song(song_id)
            self._songs[song_id].update(name=name, artist=artist)
            return dict(self._songs[song_id])

    def delete_song(self, song_id):
        with self._lock:
            self.get_song(song_id)
            del self._songs[song_id]
            for p in self._playlists.values():
                if song_id in p["song_ids"]:
                    p["song_ids"].remove(song_id)

    def list_song_playlists(self, song_id):
        with self._lock:
            self.get_song(song_id)
            return [_pl(p) for p in self._playlists.values() if song_id in p["song_ids"]]

    # --------------------------------------------------------- playlists
    def list_playlists(self):
        with self._lock:
            return [_pl(p) for p in self._playlists.values()]

    def get_playlist(self, playlist_id):
        with self._lock:
            if playlist_id not in self._playlists:
                raise NotFound(f"playlist {playlist_id} not found")
            return _pl(self._playlists[playlist_id])

    def list_user_playlists(self, user_id):
        with self._lock:
            self.get_user(user_id)
            return [_pl(p) for p in self._playlists.values() if p["user_id"] == user_id]

    def create_playlist(self, user_id, name, song_ids=()):
        name = _name(name)
        with self._lock:
            self.get_user(user_id)
            ids = list(dict.fromkeys(song_ids or ()))
            for sid in ids:
                self.get_song(sid)
            pid = self._next("playlist")
            self._playlists[pid] = {"id": pid, "name": name, "user_id": user_id, "song_ids": ids}
            return _pl(self._playlists[pid])

    def update_playlist(self, playlist_id, name):
        name = _name(name)
        with self._lock:
            self.get_playlist(playlist_id)
            self._playlists[playlist_id]["name"] = name
            return _pl(self._playlists[playlist_id])

    def delete_playlist(self, playlist_id):
        with self._lock:
            self.get_playlist(playlist_id)
            del self._playlists[playlist_id]

    def list_playlist_songs(self, playlist_id):
        with self._lock:
            p = self.get_playlist(playlist_id)
            return [dict(self._songs[s]) for s in p["song_ids"] if s in self._songs]

    def add_song(self, playlist_id, song_id):
        with self._lock:
            self.get_playlist(playlist_id)
            self.get_song(song_id)
            ids = self._playlists[playlist_id]["song_ids"]
            if song_id not in ids:
                ids.append(song_id)
            return _pl(self._playlists[playlist_id])

    def remove_song(self, playlist_id, song_id):
        with self._lock:
            self.get_playlist(playlist_id)
            ids = self._playlists[playlist_id]["song_ids"]
            if song_id not in ids:
                raise NotFound(f"song {song_id} is not in playlist {playlist_id}")
            ids.remove(song_id)
            return _pl(self._playlists[playlist_id])


ARTISTS = ["Ana Clara", "Bruno Reis", "Caetano Lima", "Dora Matos", "Elis Prado",
           "Fábio Nunes", "Gal Torres", "Hugo Leal", "Iara Melo", "Jorge Vaz"]


def build_store(cfg=None):
    """Cria o repositório já populado (determinístico)."""
    cfg = cfg or SEED
    rng = random.Random(cfg["random_seed"])
    s = Store()
    for i in range(1, cfg["songs"] + 1):
        s.create_song(f"Song {i:04d}", ARTISTS[i % len(ARTISTS)])
    for i in range(1, cfg["users"] + 1):
        u = s.create_user(f"User {i:04d}", 18 + (i % 50))
        for k in range(1, cfg["playlists_per_user"] + 1):
            ids = rng.sample(range(1, cfg["songs"] + 1), min(cfg["songs_per_playlist"], cfg["songs"]))
            s.create_playlist(u["id"], f"Playlist {k} de {u['name']}", ids)
    return s
