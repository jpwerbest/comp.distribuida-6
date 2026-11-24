"""REST (FastAPI). Recursos + verbos HTTP + JSON.  Porta padrão: 8001.

Docs interativas (OpenAPI): http://127.0.0.1:8001/docs
"""
from typing import List

import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config import HOST, PORTS
from ..errors import Invalid, NotFound
from ..store import build_store

store = build_store()
app = FastAPI(title="Music Streaming - REST", version="1.0.0")


class UserIn(BaseModel):
    name: str = Field(min_length=1)
    age: int = Field(ge=0, le=150)


class SongIn(BaseModel):
    name: str = Field(min_length=1)
    artist: str = Field(min_length=1)


class PlaylistIn(BaseModel):
    name: str = Field(min_length=1)
    song_ids: List[int] = []


class PlaylistUpdate(BaseModel):
    name: str = Field(min_length=1)


@app.exception_handler(NotFound)
async def _not_found(_, exc):
    return JSONResponse({"detail": str(exc)}, status_code=404)


@app.exception_handler(Invalid)
async def _invalid(_, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


# ----------------------------------------------------------------- users
@app.get("/users")
async def list_users():
    return store.list_users()


@app.post("/users", status_code=201)
async def create_user(body: UserIn):
    return store.create_user(body.name, body.age)


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return store.get_user(user_id)


@app.put("/users/{user_id}")
async def update_user(user_id: int, body: UserIn):
    return store.update_user(user_id, body.name, body.age)


@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int):
    store.delete_user(user_id)
    return Response(status_code=204)


@app.get("/users/{user_id}/playlists")
async def list_user_playlists(user_id: int):
    return store.list_user_playlists(user_id)


@app.post("/users/{user_id}/playlists", status_code=201)
async def create_playlist(user_id: int, body: PlaylistIn):
    return store.create_playlist(user_id, body.name, body.song_ids)


# ----------------------------------------------------------------- songs
@app.get("/songs")
async def list_songs():
    return store.list_songs()


@app.post("/songs", status_code=201)
async def create_song(body: SongIn):
    return store.create_song(body.name, body.artist)


@app.get("/songs/{song_id}")
async def get_song(song_id: int):
    return store.get_song(song_id)


@app.put("/songs/{song_id}")
async def update_song(song_id: int, body: SongIn):
    return store.update_song(song_id, body.name, body.artist)


@app.delete("/songs/{song_id}", status_code=204)
async def delete_song(song_id: int):
    store.delete_song(song_id)
    return Response(status_code=204)


@app.get("/songs/{song_id}/playlists")
async def list_song_playlists(song_id: int):
    return store.list_song_playlists(song_id)


# ------------------------------------------------------------- playlists
@app.get("/playlists")
async def list_playlists():
    return store.list_playlists()


@app.get("/playlists/{playlist_id}")
async def get_playlist(playlist_id: int):
    return store.get_playlist(playlist_id)


@app.put("/playlists/{playlist_id}")
async def update_playlist(playlist_id: int, body: PlaylistUpdate):
    return store.update_playlist(playlist_id, body.name)


@app.delete("/playlists/{playlist_id}", status_code=204)
async def delete_playlist(playlist_id: int):
    store.delete_playlist(playlist_id)
    return Response(status_code=204)


@app.get("/playlists/{playlist_id}/songs")
async def list_playlist_songs(playlist_id: int):
    return store.list_playlist_songs(playlist_id)


@app.put("/playlists/{playlist_id}/songs/{song_id}")
async def add_song(playlist_id: int, song_id: int):
    return store.add_song(playlist_id, song_id)


@app.delete("/playlists/{playlist_id}/songs/{song_id}")
async def remove_song(playlist_id: int, song_id: int):
    return store.remove_song(playlist_id, song_id)


def main():
    uvicorn.run(app, host=HOST, port=PORTS["rest"], log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
