"""Interface única de cliente. Cada tecnologia implementa os mesmos métodos e
devolve os mesmos dicts canônicos:
  user     {id, name, age}
  song     {id, name, artist}
  playlist {id, name, user_id, song_ids}
`self.calls` conta as chamadas de rede feitas (para comparar N+1 vs 1 round-trip).
"""


class MusicClient:
    technology = "?"

    def __init__(self):
        self.calls = 0

    def close(self):
        pass

    def user_playlists_with_songs(self, user_id):
        """Consulta composta: playlists do usuário, cada uma com suas músicas.
        Implementação 'natural' de REST/gRPC/SOAP: 1 + N chamadas (N = nº de playlists).
        O cliente GraphQL sobrescreve com uma única chamada."""
        return [{**p, "songs": self.list_playlist_songs(p["id"])}
                for p in self.list_user_playlists(user_id)]
