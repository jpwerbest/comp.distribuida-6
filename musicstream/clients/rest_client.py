import requests

from ..errors import RemoteError
from .base import MusicClient


class RestClient(MusicClient):
    technology = "rest"

    def __init__(self, host, port):
        super().__init__()
        self.base = f"http://{host}:{port}"
        self.http = requests.Session()  # keep-alive

    def close(self):
        self.http.close()

    def _req(self, method, path, **kw):
        self.calls += 1
        try:
            r = self.http.request(method, self.base + path, timeout=30, **kw)
            r.raise_for_status()
        except requests.RequestException as e:
            raise RemoteError(str(e)) from e
        return r.json() if r.content else None

    # users
    def list_users(self): return self._req("GET", "/users")
    def get_user(self, i): return self._req("GET", f"/users/{i}")
    def create_user(self, name, age): return self._req("POST", "/users", json={"name": name, "age": age})
    def update_user(self, i, name, age): return self._req("PUT", f"/users/{i}", json={"name": name, "age": age})
    def delete_user(self, i): self._req("DELETE", f"/users/{i}")
    def list_user_playlists(self, i): return self._req("GET", f"/users/{i}/playlists")
    # songs
    def list_songs(self): return self._req("GET", "/songs")
    def get_song(self, i): return self._req("GET", f"/songs/{i}")
    def create_song(self, name, artist): return self._req("POST", "/songs", json={"name": name, "artist": artist})
    def update_song(self, i, name, artist): return self._req("PUT", f"/songs/{i}", json={"name": name, "artist": artist})
    def delete_song(self, i): self._req("DELETE", f"/songs/{i}")
    def list_song_playlists(self, i): return self._req("GET", f"/songs/{i}/playlists")
    # playlists
    def get_playlist(self, i): return self._req("GET", f"/playlists/{i}")
    def create_playlist(self, user_id, name, song_ids=()):
        return self._req("POST", f"/users/{user_id}/playlists", json={"name": name, "song_ids": list(song_ids)})
    def update_playlist(self, i, name): return self._req("PUT", f"/playlists/{i}", json={"name": name})
    def delete_playlist(self, i): self._req("DELETE", f"/playlists/{i}")
    def list_playlist_songs(self, i): return self._req("GET", f"/playlists/{i}/songs")
    def add_song(self, pid, sid): return self._req("PUT", f"/playlists/{pid}/songs/{sid}")
    def remove_song(self, pid, sid): return self._req("DELETE", f"/playlists/{pid}/songs/{sid}")
