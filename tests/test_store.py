import pytest

from musicstream.errors import Invalid, NotFound
from musicstream.store import Store, build_store


def test_seed_sizes():
    s = build_store({"users": 5, "songs": 20, "playlists_per_user": 2, "songs_per_playlist": 4, "random_seed": 1})
    assert len(s.list_users()) == 5 and len(s.list_songs()) == 20 and len(s.list_playlists()) == 10


def test_cascade_and_integrity():
    s = Store()
    u = s.create_user("A", 20)
    song = s.create_song("S", "X")
    p = s.create_playlist(u["id"], "P", [song["id"], song["id"]])
    assert p["song_ids"] == [song["id"]]                    # sem duplicatas
    s.delete_song(song["id"])
    assert s.get_playlist(p["id"])["song_ids"] == []        # música removida das playlists
    s.delete_user(u["id"])
    with pytest.raises(NotFound):
        s.get_playlist(p["id"])                             # cascata


def test_validation():
    s = Store()
    with pytest.raises(Invalid):
        s.create_user("", 10)
    with pytest.raises(Invalid):
        s.create_user("A", -1)
    with pytest.raises(NotFound):
        s.create_playlist(99, "P")
