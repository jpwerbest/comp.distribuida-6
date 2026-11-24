"""Compara o TAMANHO do corpo das respostas nas 4 tecnologias (sem rede).

Uso: python -m musicstream.bench.payload_sizes   ->  results/payload_sizes.csv
(gRPC exige os stubs gerados: python scripts/gen_proto.py)
"""
import csv
import json
from pathlib import Path

from .. import soap_wire as sw
from ..store import build_store

GRPC_FRAME = 5  # prefixo de 5 bytes por mensagem gRPC (flag + tamanho)


def js(obj):
    return len(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode())


def camel_pl(p, songs=None):
    d = {"id": p["id"], "name": p["name"], "userId": p["user_id"]}
    if songs is not None:
        d["songs"] = songs
    else:
        d["songIds"] = p["song_ids"]
    return d


def main():
    s = build_store()
    uid, pls = 1, s.list_user_playlists(1)
    pl_songs = {p["id"]: s.list_playlist_songs(p["id"]) for p in pls}
    rows = []

    def soap(op, *args):
        return len(sw.handle_soap(s, sw.build_request(op, args))[1])

    try:
        from ..generated import music_pb2 as pb
    except ImportError:
        pb = None
        print("AVISO: stubs gRPC ausentes; coluna grpc ficará vazia (rode scripts/gen_proto.py).")

    def pbsize(msg):
        return msg.ByteSize() + GRPC_FRAME

    # get_song
    song = s.get_song(1)
    rows.append(("get_song", js(song), js({"data": {"song": song}}), soap("GetSong", 1),
                 pbsize(pb.Song(**song)) if pb else ""))
    # list_songs
    songs = s.list_songs()
    rows.append(("list_songs", js(songs), js({"data": {"songs": songs}}), soap("ListSongs"),
                 pbsize(pb.SongList(songs=[pb.Song(**x) for x in songs])) if pb else ""))
    # consulta composta (soma de todas as respostas necessárias)
    rest = js(pls) + sum(js(v) for v in pl_songs.values())
    gql = js({"data": {"user": {"playlists": [camel_pl(p, pl_songs[p["id"]]) for p in pls]}}})
    soap_total = soap("ListUserPlaylists", uid) + sum(soap("ListPlaylistSongs", p["id"]) for p in pls)
    grpc_total = ""
    if pb:
        grpc_total = pbsize(pb.PlaylistList(playlists=[pb.Playlist(**p) for p in pls])) + sum(
            pbsize(pb.SongList(songs=[pb.Song(**x) for x in v])) for v in pl_songs.values())
    rows.append(("user_playlists_songs", rest, gql, soap_total, grpc_total))

    out = Path("results/payload_sizes.csv")
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "rest", "graphql", "soap", "grpc"])
        w.writerows(rows)
    print(f"{'cenário':24s} {'REST':>9s} {'GraphQL':>9s} {'SOAP':>9s} {'gRPC':>9s}  (bytes de corpo)")
    for r in rows:
        print(f"{r[0]:24s} " + " ".join(f"{str(x):>9s}" for x in r[1:]))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
