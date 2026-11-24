"""Configuração central: hosts, portas e tamanho da massa de dados (seed)."""
import os

HOST = os.getenv("MUSIC_HOST", "127.0.0.1")

PORTS = {
    "rest": int(os.getenv("MUSIC_PORT_REST", 8001)),
    "graphql": int(os.getenv("MUSIC_PORT_GRAPHQL", 8002)),
    "grpc": int(os.getenv("MUSIC_PORT_GRPC", 8003)),
    "soap": int(os.getenv("MUSIC_PORT_SOAP", 8004)),
}

SERVER_MODULES = {
    "rest": "musicstream.servers.rest_server",
    "graphql": "musicstream.servers.graphql_server",
    "grpc": "musicstream.servers.grpc_server",
    "soap": "musicstream.servers.soap_server",
}

TECHS = list(PORTS)

# Massa de dados inicial (idêntica nas 4 tecnologias; deterministica).
SEED = {
    "users": int(os.getenv("SEED_USERS", 200)),
    "songs": int(os.getenv("SEED_SONGS", 1000)),
    "playlists_per_user": int(os.getenv("SEED_PLAYLISTS_PER_USER", 3)),
    "songs_per_playlist": int(os.getenv("SEED_SONGS_PER_PLAYLIST", 10)),
    "random_seed": 42,
}
