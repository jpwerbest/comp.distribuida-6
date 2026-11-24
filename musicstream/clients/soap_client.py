"""Cliente SOAP 'cru' (requests + envelopes). Medimos o PROTOCOLO, não o custo
de geração de stubs de uma lib como zeep (que seria muito mais lento).
Para um exemplo com zeep/WSDL, veja examples/soap_zeep_example.py."""
import requests

from .. import soap_wire as sw
from ..errors import RemoteError
from .base import MusicClient

HEADERS = {"Content-Type": "application/soap+xml; charset=utf-8"}


class SoapClient(MusicClient):
    technology = "soap"

    def __init__(self, host, port):
        super().__init__()
        self.url = f"http://{host}:{port}/soap"
        self.http = requests.Session()

    def close(self):
        self.http.close()

    def _call(self, op, *args):
        self.calls += 1
        try:
            r = self.http.post(self.url, data=sw.build_request(op, args), headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            raise RemoteError(str(e)) from e
        return sw.parse_response(op, r.content)  # levanta RemoteError em caso de Fault

    # users
    def list_users(self): return self._call("ListUsers")
    def get_user(self, i): return self._call("GetUser", i)
    def create_user(self, name, age): return self._call("CreateUser", name, age)
    def update_user(self, i, name, age): return self._call("UpdateUser", i, name, age)
    def delete_user(self, i): self._call("DeleteUser", i)
    def list_user_playlists(self, i): return self._call("ListUserPlaylists", i)
    # songs
    def list_songs(self): return self._call("ListSongs")
    def get_song(self, i): return self._call("GetSong", i)
    def create_song(self, name, artist): return self._call("CreateSong", name, artist)
    def update_song(self, i, name, artist): return self._call("UpdateSong", i, name, artist)
    def delete_song(self, i): self._call("DeleteSong", i)
    def list_song_playlists(self, i): return self._call("ListSongPlaylists", i)
    # playlists
    def get_playlist(self, i): return self._call("GetPlaylist", i)
    def create_playlist(self, user_id, name, song_ids=()): return self._call("CreatePlaylist", user_id, name, list(song_ids))
    def update_playlist(self, i, name): return self._call("UpdatePlaylist", i, name)
    def delete_playlist(self, i): self._call("DeletePlaylist", i)
    def list_playlist_songs(self, i): return self._call("ListPlaylistSongs", i)
    def add_song(self, pid, sid): return self._call("AddSongToPlaylist", pid, sid)
    def remove_song(self, pid, sid): return self._call("RemoveSongFromPlaylist", pid, sid)
