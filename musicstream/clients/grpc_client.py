import grpc

from ..errors import RemoteError
from ..generated import music_pb2 as pb
from ..generated import music_pb2_grpc as pb_grpc
from .base import MusicClient


def _u(m): return {"id": m.id, "name": m.name, "age": m.age}
def _s(m): return {"id": m.id, "name": m.name, "artist": m.artist}
def _p(m): return {"id": m.id, "name": m.name, "user_id": m.user_id, "song_ids": list(m.song_ids)}


class GrpcClient(MusicClient):
    technology = "grpc"

    def __init__(self, host, port):
        super().__init__()
        self.channel = grpc.insecure_channel(f"{host}:{port}", options=[
            ("grpc.max_receive_message_length", 64 * 1024 * 1024)])
        self.users = pb_grpc.UserServiceStub(self.channel)
        self.songs = pb_grpc.SongServiceStub(self.channel)
        self.pls = pb_grpc.PlaylistServiceStub(self.channel)

    def close(self):
        self.channel.close()

    def _call(self, method, request):
        self.calls += 1
        try:
            return method(request, timeout=30)
        except grpc.RpcError as e:
            raise RemoteError(f"{e.code().name}: {e.details()}") from e

    # users
    def list_users(self): return [_u(u) for u in self._call(self.users.ListUsers, pb.Empty()).users]
    def get_user(self, i): return _u(self._call(self.users.GetUser, pb.IdRequest(id=i)))
    def create_user(self, name, age): return _u(self._call(self.users.CreateUser, pb.CreateUserRequest(name=name, age=age)))
    def update_user(self, i, name, age): return _u(self._call(self.users.UpdateUser, pb.UpdateUserRequest(id=i, name=name, age=age)))
    def delete_user(self, i): self._call(self.users.DeleteUser, pb.IdRequest(id=i))
    def list_user_playlists(self, i): return [_p(p) for p in self._call(self.users.ListUserPlaylists, pb.IdRequest(id=i)).playlists]
    # songs
    def list_songs(self): return [_s(s) for s in self._call(self.songs.ListSongs, pb.Empty()).songs]
    def get_song(self, i): return _s(self._call(self.songs.GetSong, pb.IdRequest(id=i)))
    def create_song(self, name, artist): return _s(self._call(self.songs.CreateSong, pb.CreateSongRequest(name=name, artist=artist)))
    def update_song(self, i, name, artist): return _s(self._call(self.songs.UpdateSong, pb.UpdateSongRequest(id=i, name=name, artist=artist)))
    def delete_song(self, i): self._call(self.songs.DeleteSong, pb.IdRequest(id=i))
    def list_song_playlists(self, i): return [_p(p) for p in self._call(self.songs.ListSongPlaylists, pb.IdRequest(id=i)).playlists]
    # playlists
    def get_playlist(self, i): return _p(self._call(self.pls.GetPlaylist, pb.IdRequest(id=i)))
    def create_playlist(self, user_id, name, song_ids=()):
        return _p(self._call(self.pls.CreatePlaylist, pb.CreatePlaylistRequest(user_id=user_id, name=name, song_ids=list(song_ids))))
    def update_playlist(self, i, name): return _p(self._call(self.pls.UpdatePlaylist, pb.UpdatePlaylistRequest(id=i, name=name)))
    def delete_playlist(self, i): self._call(self.pls.DeletePlaylist, pb.IdRequest(id=i))
    def list_playlist_songs(self, i): return [_s(s) for s in self._call(self.pls.ListPlaylistSongs, pb.IdRequest(id=i)).songs]
    def add_song(self, pid, sid): return _p(self._call(self.pls.AddSong, pb.PlaylistSongRequest(playlist_id=pid, song_id=sid)))
    def remove_song(self, pid, sid): return _p(self._call(self.pls.RemoveSong, pb.PlaylistSongRequest(playlist_id=pid, song_id=sid)))
