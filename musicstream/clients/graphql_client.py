import requests

from ..errors import RemoteError
from .base import MusicClient

U = "id name age"
S = "id name artist"
P = "id name userId songIds"


def _pl(p):
    return {"id": p["id"], "name": p["name"], "user_id": p["userId"], "song_ids": p["songIds"]}


class GraphQLClient(MusicClient):
    technology = "graphql"

    def __init__(self, host, port):
        super().__init__()
        self.url = f"http://{host}:{port}/graphql"
        self.http = requests.Session()

    def close(self):
        self.http.close()

    def _gql(self, query, **variables):
        self.calls += 1
        try:
            r = self.http.post(self.url, json={"query": query, "variables": variables}, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            raise RemoteError(str(e)) from e
        body = r.json()
        if body.get("errors"):
            raise RemoteError("; ".join(e["message"] for e in body["errors"]))
        return body["data"]

    # users
    def list_users(self): return self._gql(f"{{ users {{ {U} }} }}")["users"]
    def get_user(self, i): return self._gql(f"query($id:Int!){{ user(id:$id){{ {U} }} }}", id=i)["user"]
    def create_user(self, name, age):
        return self._gql(f"mutation($n:String!,$a:Int!){{ createUser(name:$n,age:$a){{ {U} }} }}", n=name, a=age)["createUser"]
    def update_user(self, i, name, age):
        return self._gql(f"mutation($i:Int!,$n:String!,$a:Int!){{ updateUser(id:$i,name:$n,age:$a){{ {U} }} }}", i=i, n=name, a=age)["updateUser"]
    def delete_user(self, i): self._gql("mutation($id:Int!){ deleteUser(id:$id) }", id=i)
    def list_user_playlists(self, i):
        return [_pl(p) for p in self._gql(f"query($id:Int!){{ user(id:$id){{ playlists {{ {P} }} }} }}", id=i)["user"]["playlists"]]
    # songs
    def list_songs(self): return self._gql(f"{{ songs {{ {S} }} }}")["songs"]
    def get_song(self, i): return self._gql(f"query($id:Int!){{ song(id:$id){{ {S} }} }}", id=i)["song"]
    def create_song(self, name, artist):
        return self._gql(f"mutation($n:String!,$a:String!){{ createSong(name:$n,artist:$a){{ {S} }} }}", n=name, a=artist)["createSong"]
    def update_song(self, i, name, artist):
        return self._gql(f"mutation($i:Int!,$n:String!,$a:String!){{ updateSong(id:$i,name:$n,artist:$a){{ {S} }} }}", i=i, n=name, a=artist)["updateSong"]
    def delete_song(self, i): self._gql("mutation($id:Int!){ deleteSong(id:$id) }", id=i)
    def list_song_playlists(self, i):
        return [_pl(p) for p in self._gql(f"query($id:Int!){{ song(id:$id){{ playlists {{ {P} }} }} }}", id=i)["song"]["playlists"]]
    # playlists
    def get_playlist(self, i): return _pl(self._gql(f"query($id:Int!){{ playlist(id:$id){{ {P} }} }}", id=i)["playlist"])
    def create_playlist(self, user_id, name, song_ids=()):
        return _pl(self._gql(f"mutation($u:Int!,$n:String!,$s:[Int!]){{ createPlaylist(userId:$u,name:$n,songIds:$s){{ {P} }} }}",
                             u=user_id, n=name, s=list(song_ids))["createPlaylist"])
    def update_playlist(self, i, name):
        return _pl(self._gql(f"mutation($i:Int!,$n:String!){{ updatePlaylist(id:$i,name:$n){{ {P} }} }}", i=i, n=name)["updatePlaylist"])
    def delete_playlist(self, i): self._gql("mutation($id:Int!){ deletePlaylist(id:$id) }", id=i)
    def list_playlist_songs(self, i): return self._gql(f"query($id:Int!){{ playlist(id:$id){{ songs {{ {S} }} }} }}", id=i)["playlist"]["songs"]
    def add_song(self, pid, sid):
        return _pl(self._gql(f"mutation($p:Int!,$s:Int!){{ addSongToPlaylist(playlistId:$p,songId:$s){{ {P} }} }}", p=pid, s=sid)["addSongToPlaylist"])
    def remove_song(self, pid, sid):
        return _pl(self._gql(f"mutation($p:Int!,$s:Int!){{ removeSongFromPlaylist(playlistId:$p,songId:$s){{ {P} }} }}", p=pid, s=sid)["removeSongFromPlaylist"])

    def user_playlists_with_songs(self, user_id):
        """UMA única chamada traz playlists + músicas (sem N+1)."""
        q = f"query($id:Int!){{ user(id:$id){{ playlists {{ id name userId songs {{ {S} }} }} }} }}"
        out = []
        for p in self._gql(q, id=user_id)["user"]["playlists"]:
            out.append({"id": p["id"], "name": p["name"], "user_id": p["userId"],
                        "song_ids": [s["id"] for s in p["songs"]], "songs": p["songs"]})
        return out
