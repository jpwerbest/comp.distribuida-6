"""Gerador de carga: cenários + workers (multiprocessos x threads).

Cada "operação lógica" de um cenário pode envolver várias chamadas de rede
(ex.: REST faz 1+N chamadas na consulta composta; GraphQL faz 1). A latência
medida é a da operação lógica completa, e `rpcs` conta as chamadas de rede.
"""
import random
import time
from concurrent.futures import ThreadPoolExecutor

from ..clients import make_client
from ..config import SEED


# ------------------------------------------------------------- cenários
def get_song(c, rng):                   # leitura pequena (payload mínimo)
    c.get_song(rng.randint(1, SEED["songs"]))


def list_songs(c, rng):                 # leitura grande (todas as músicas)
    c.list_songs()


def user_playlists_songs(c, rng):       # consulta composta/aninhada
    c.user_playlists_with_songs(rng.randint(1, SEED["users"]))


def write(c, rng):                      # escrita: cria e remove um usuário
    u = c.create_user(f"load-{rng.randrange(10 ** 9)}", rng.randint(18, 80))
    c.delete_user(u["id"])


def mixed(c, rng):                      # 50% leitura simples, 20% composta, 10% lista, 20% escrita
    r = rng.random()
    if r < 0.5:
        get_song(c, rng)
    elif r < 0.7:
        user_playlists_songs(c, rng)
    elif r < 0.8:
        list_songs(c, rng)
    else:
        write(c, rng)


SCENARIOS = {
    "get_song": get_song,
    "list_songs": list_songs,
    "user_playlists_songs": user_playlists_songs,
    "write": write,
    "mixed": mixed,
}


# --------------------------------------------------------------- worker
def warm_imports():
    """initializer do Pool: importa as libs antes da medição."""
    from ..config import TECHS
    for t in TECHS:
        try:
            make_client(t, port=1).close()
        except Exception:  # noqa: BLE001
            pass


def worker(tech, scenario, n_threads, start_at, warmup_s, duration_s, seed):
    """Roda n_threads usuários virtuais. Retorna (latências, erros, rpcs)."""
    fn = SCENARIOS[scenario]
    measure_from = start_at + warmup_s
    end = measure_from + duration_s

    def user(tid):
        rng = random.Random(seed * 1000 + tid)
        client = make_client(tech)
        lat, errs, rpcs = [], 0, 0
        try:
            while time.time() < start_at:
                time.sleep(0.001)
            while True:
                wall = time.time()
                if wall >= end:
                    break
                calls0, t0 = client.calls, time.perf_counter()
                try:
                    fn(client, rng)
                    ok = True
                except Exception:  # noqa: BLE001
                    ok = False
                dt = time.perf_counter() - t0
                if wall >= measure_from:
                    if ok:
                        lat.append(dt)
                        rpcs += client.calls - calls0
                    else:
                        errs += 1
        finally:
            client.close()
        return lat, errs, rpcs

    with ThreadPoolExecutor(n_threads) as ex:
        outs = list(ex.map(user, range(n_threads)))
    lat = [x for o in outs for x in o[0]]
    return lat, sum(o[1] for o in outs), sum(o[2] for o in outs)
