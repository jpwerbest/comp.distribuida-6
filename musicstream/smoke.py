"""Teste de paridade funcional: roda o MESMO roteiro CRUD nas 4 tecnologias.

Uso (com os servidores no ar):  python -m musicstream.smoke [--techs rest,soap]
"""
import argparse
import sys

from .clients import make_client
from .config import TECHS
from .errors import RemoteError


def expect_error(fn):
    try:
        fn()
    except RemoteError:
        return
    raise AssertionError("era esperado um erro remoto")


def check(c):
    u = c.create_user("Smoke", 30)
    assert u["name"] == "Smoke" and u["age"] == 30
    uid = u["id"]
    assert c.get_user(uid) == u
    assert c.update_user(uid, "Smoke2", 31)["name"] == "Smoke2"
    assert uid in [x["id"] for x in c.list_users()]

    s1, s2 = c.create_song("S1", "A1"), c.create_song("S2", "A2")
    p = c.create_playlist(uid, "P", [s1["id"]])
    assert p["user_id"] == uid and p["song_ids"] == [s1["id"]]
    p = c.add_song(p["id"], s2["id"])
    assert p["song_ids"] == [s1["id"], s2["id"]]
    assert [s["id"] for s in c.list_playlist_songs(p["id"])] == [s1["id"], s2["id"]]
    assert p["id"] in [x["id"] for x in c.list_user_playlists(uid)]
    assert p["id"] in [x["id"] for x in c.list_song_playlists(s1["id"])]
    full = c.user_playlists_with_songs(uid)
    assert len(full) == 1 and len(full[0]["songs"]) == 2
    assert c.remove_song(p["id"], s1["id"])["song_ids"] == [s2["id"]]
    assert c.update_playlist(p["id"], "P2")["name"] == "P2"
    assert c.get_playlist(p["id"])["name"] == "P2"
    assert c.update_song(s1["id"], "S1b", "A1")["name"] == "S1b"
    assert c.get_song(s1["id"])["name"] == "S1b"

    c.delete_playlist(p["id"])
    expect_error(lambda: c.get_playlist(p["id"]))
    c.delete_song(s1["id"])
    c.delete_song(s2["id"])
    expect_error(lambda: c.get_song(s1["id"]))
    c.delete_user(uid)
    expect_error(lambda: c.get_user(uid))
    expect_error(lambda: c.create_user("", 10))          # validação
    expect_error(lambda: c.get_user(10 ** 9))            # não encontrado


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--techs", default=",".join(TECHS))
    args = ap.parse_args()
    failed = 0
    for tech in args.techs.split(","):
        c = make_client(tech)
        try:
            check(c)
            print(f"[OK]   {tech}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"[FAIL] {tech}: {e!r}")
        finally:
            c.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
