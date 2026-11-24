"""GraphQL (Strawberry + FastAPI). Endpoint único /graphql.  Porta padrão: 8002.

IDE interativa (GraphiQL): abra http://127.0.0.1:8002/graphql no navegador.
"""
from typing import List, Optional

import strawberry
import uvicorn
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from ..config import HOST, PORTS
from ..store import build_store

store = build_store()


@strawberry.type
class User:
    id: int
    name: str
    age: int

    @strawberry.field
    def playlists(self) -> List["Playlist"]:
        return [_playlist(p) for p in store.list_user_playlists(self.id)]


@strawberry.type
class Song:
    id: int
    name: str
    artist: str

    @strawberry.field
    def playlists(self) -> List["Playlist"]:
        return [_playlist(p) for p in store.list_song_playlists(self.id)]


@strawberry.type
class Playlist:
    id: int
    name: str
    user_id: int
    song_ids: List[int]

    @strawberry.field
    def songs(self) -> List[Song]:
        return [_song(s) for s in store.list_playlist_songs(self.id)]

    @strawberry.field
    def user(self) -> User:
        return _user(store.get_user(self.user_id))


def _user(d):
    return User(id=d["id"], name=d["name"], age=d["age"])


def _song(d):
    return Song(id=d["id"], name=d["name"], artist=d["artist"])


def _playlist(d):
    return Playlist(id=d["id"], name=d["name"], user_id=d["user_id"], song_ids=d["song_ids"])


@strawberry.type
class Query:
    @strawberry.field
    def users(self) -> List[User]:
        return [_user(u) for u in store.list_users()]

    @strawberry.field
    def user(self, id: int) -> User:
        return _user(store.get_user(id))

    @strawberry.field
    def songs(self) -> List[Song]:
        return [_song(s) for s in store.list_songs()]

    @strawberry.field
    def song(self, id: int) -> Song:
        return _song(store.get_song(id))

    @strawberry.field
    def playlists(self) -> List[Playlist]:
        return [_playlist(p) for p in store.list_playlists()]

    @strawberry.field
    def playlist(self, id: int) -> Playlist:
        return _playlist(store.get_playlist(id))


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_user(self, name: str, age: int) -> User:
        return _user(store.create_user(name, age))

    @strawberry.mutation
    def update_user(self, id: int, name: str, age: int) -> User:
        return _user(store.update_user(id, name, age))

    @strawberry.mutation
    def delete_user(self, id: int) -> bool:
        store.delete_user(id)
        return True

    @strawberry.mutation
    def create_song(self, name: str, artist: str) -> Song:
        return _song(store.create_song(name, artist))

    @strawberry.mutation
    def update_song(self, id: int, name: str, artist: str) -> Song:
        return _song(store.update_song(id, name, artist))

    @strawberry.mutation
    def delete_song(self, id: int) -> bool:
        store.delete_song(id)
        return True

    @strawberry.mutation
    def create_playlist(self, user_id: int, name: str, song_ids: Optional[List[int]] = None) -> Playlist:
        return _playlist(store.create_playlist(user_id, name, song_ids or []))

    @strawberry.mutation
    def update_playlist(self, id: int, name: str) -> Playlist:
        return _playlist(store.update_playlist(id, name))

    @strawberry.mutation
    def delete_playlist(self, id: int) -> bool:
        store.delete_playlist(id)
        return True

    @strawberry.mutation
    def add_song_to_playlist(self, playlist_id: int, song_id: int) -> Playlist:
        return _playlist(store.add_song(playlist_id, song_id))

    @strawberry.mutation
    def remove_song_from_playlist(self, playlist_id: int, song_id: int) -> Playlist:
        return _playlist(store.remove_song(playlist_id, song_id))


schema = strawberry.Schema(query=Query, mutation=Mutation)
app = FastAPI(title="Music Streaming - GraphQL")
app.include_router(GraphQLRouter(schema), prefix="/graphql")


def main():
    uvicorn.run(app, host=HOST, port=PORTS["graphql"], log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
