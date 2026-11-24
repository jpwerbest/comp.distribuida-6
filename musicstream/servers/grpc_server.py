"""gRPC (grpc.aio + Protocol Buffers sobre HTTP/2).  Porta padrão: 8003.

Antes de rodar, gere os stubs:  python scripts/gen_proto.py
Exploração manual (opcional): grpcurl -plaintext 127.0.0.1:8003 list   (reflection não habilitada;
use o arquivo proto/music.proto:  grpcurl -plaintext -proto proto/music.proto 127.0.0.1:8003 music.SongService/ListSongs)
"""
import asyncio
import functools

import grpc
from grpc import aio

from ..config import HOST, PORTS
from ..errors import Invalid, NotFound
from ..generated import music_pb2 as pb
from ..generated import music_pb2_grpc as pb_grpc
from ..store import build_store

store = build_store()


def _user(d):
    return pb.User(id=d["id"], name=d["name"], age=d["age"])


def _song(d):
    return pb.Song(id=d["id"], name=d["name"], artist=d["artist"])


def _playlist(d):
    return pb.Playlist(id=d["id"], name=d["name"], user_id=d["user_id"], song_ids=d["song_ids"])


def rpc(fn):
    """Traduz exceções de domínio em status codes gRPC."""
    @functools.wraps(fn)
    async def wrapper(self, request, context):
        try:
            return fn(self, request, context)
        except NotFound as e:
            await context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except Invalid as e:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
    return wrapper


class UserService(pb_grpc.UserServiceServicer):
    @rpc
    def ListUsers(self, r, c):
        return pb.UserList(users=[_user(u) for u in store.list_users()])

    @rpc
    def GetUser(self, r, c):
        return _user(store.get_user(r.id))

    @rpc
    def CreateUser(self, r, c):
        return _user(store.create_user(r.name, r.age))

    @rpc
    def UpdateUser(self, r, c):
        return _user(store.update_user(r.id, r.name, r.age))

    @rpc
    def DeleteUser(self, r, c):
        store.delete_user(r.id)
        return pb.Empty()

    @rpc
    def ListUserPlaylists(self, r, c):
        return pb.PlaylistList(playlists=[_playlist(p) for p in store.list_user_playlists(r.id)])


class SongService(pb_grpc.SongServiceServicer):
    @rpc
    def ListSongs(self, r, c):
        return pb.SongList(songs=[_song(s) for s in store.list_songs()])

    @rpc
    def GetSong(self, r, c):
        return _song(store.get_song(r.id))

    @rpc
    def CreateSong(self, r, c):
        return _song(store.create_song(r.name, r.artist))

    @rpc
    def UpdateSong(self, r, c):
        return _song(store.update_song(r.id, r.name, r.artist))

    @rpc
    def DeleteSong(self, r, c):
        store.delete_song(r.id)
        return pb.Empty()

    @rpc
    def ListSongPlaylists(self, r, c):
        return pb.PlaylistList(playlists=[_playlist(p) for p in store.list_song_playlists(r.id)])


class PlaylistService(pb_grpc.PlaylistServiceServicer):
    @rpc
    def ListPlaylists(self, r, c):
        return pb.PlaylistList(playlists=[_playlist(p) for p in store.list_playlists()])

    @rpc
    def GetPlaylist(self, r, c):
        return _playlist(store.get_playlist(r.id))

    @rpc
    def CreatePlaylist(self, r, c):
        return _playlist(store.create_playlist(r.user_id, r.name, list(r.song_ids)))

    @rpc
    def UpdatePlaylist(self, r, c):
        return _playlist(store.update_playlist(r.id, r.name))

    @rpc
    def DeletePlaylist(self, r, c):
        store.delete_playlist(r.id)
        return pb.Empty()

    @rpc
    def ListPlaylistSongs(self, r, c):
        return pb.SongList(songs=[_song(s) for s in store.list_playlist_songs(r.id)])

    @rpc
    def AddSong(self, r, c):
        return _playlist(store.add_song(r.playlist_id, r.song_id))

    @rpc
    def RemoveSong(self, r, c):
        return _playlist(store.remove_song(r.playlist_id, r.song_id))


async def serve():
    server = aio.server(options=[("grpc.max_send_message_length", 64 * 1024 * 1024),
                                 ("grpc.max_receive_message_length", 64 * 1024 * 1024)])
    pb_grpc.add_UserServiceServicer_to_server(UserService(), server)
    pb_grpc.add_SongServiceServicer_to_server(SongService(), server)
    pb_grpc.add_PlaylistServiceServicer_to_server(PlaylistService(), server)
    server.add_insecure_port(f"{HOST}:{PORTS['grpc']}")
    await server.start()
    await server.wait_for_termination()


def main():
    asyncio.run(serve())


if __name__ == "__main__":
    main()
