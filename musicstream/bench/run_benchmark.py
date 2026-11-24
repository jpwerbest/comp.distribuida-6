"""Orquestra os testes de carga: sobe cada servidor, mede, derruba.

Exemplo:  python -m musicstream.bench.run_benchmark --duration 10 --concurrency 1,10,50,100
Rápido:   python -m musicstream.bench.run_benchmark --quick
"""
import argparse
import csv
import math
import multiprocessing as mp
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from ..clients import make_client
from ..config import HOST, PORTS, SERVER_MODULES, TECHS
from .load import SCENARIOS, warm_imports, worker

try:
    import psutil
except ImportError:  # opcional
    psutil = None

FIELDS = ["tech", "scenario", "concurrency", "duration_s", "ops", "errors", "ops_per_s", "rpcs_per_s",
          "rpcs_per_op", "mean_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms", "server_cpu_pct", "server_rss_mb"]


def pct(sorted_vals, p):
    if not sorted_vals:
        return float("nan")
    k = min(len(sorted_vals) - 1, max(0, math.ceil(p / 100 * len(sorted_vals)) - 1))
    return sorted_vals[k]


def start_server(tech, logdir):
    logdir.mkdir(parents=True, exist_ok=True)
    log = open(logdir / f"{tech}.log", "w")
    proc = subprocess.Popen([sys.executable, "-m", SERVER_MODULES[tech]], stdout=log, stderr=subprocess.STDOUT)
    deadline = time.time() + 40
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"servidor {tech} encerrou ao iniciar; veja {logdir / (tech + '.log')}")
        try:
            socket.create_connection((HOST, PORTS[tech]), timeout=0.5).close()
            break
        except OSError:
            time.sleep(0.2)
    else:
        proc.kill()
        raise RuntimeError(f"timeout ao iniciar {tech}; veja {logdir / (tech + '.log')}")
    c = make_client(tech)
    try:
        c.get_song(1)  # sanity check
    finally:
        c.close()
    return proc


def split_threads(concurrency, procs):
    return [concurrency // procs + (1 if i < concurrency % procs else 0) for i in range(procs)]


def measure(pool, proc, tech, scenario, concurrency, warmup, duration, max_procs):
    procs = min(concurrency, max_procs)
    start_at = time.time() + 2.0
    res = pool.starmap_async(worker, [(tech, scenario, n, start_at, warmup, duration, 1000 + i)
                                      for i, n in enumerate(split_threads(concurrency, procs))], chunksize=1)
    cpu = rss = float("nan")
    ps = psutil.Process(proc.pid) if psutil else None
    time.sleep(max(0, start_at + warmup - time.time()))
    if ps:
        ps.cpu_percent(None)
    time.sleep(max(0, start_at + warmup + duration - time.time()))
    if ps:
        cpu, rss = ps.cpu_percent(None), ps.memory_info().rss / 1e6
    parts = res.get(timeout=duration + warmup + 60)
    lat = sorted(x for p in parts for x in p[0])
    errors, rpcs = sum(p[1] for p in parts), sum(p[2] for p in parts)
    ops = len(lat)
    return {
        "tech": tech, "scenario": scenario, "concurrency": concurrency, "duration_s": duration,
        "ops": ops, "errors": errors, "ops_per_s": round(ops / duration, 2),
        "rpcs_per_s": round(rpcs / duration, 2), "rpcs_per_op": round(rpcs / ops, 2) if ops else float("nan"),
        "mean_ms": round(1000 * sum(lat) / ops, 3) if ops else float("nan"),
        "p50_ms": round(1000 * pct(lat, 50), 3), "p95_ms": round(1000 * pct(lat, 95), 3),
        "p99_ms": round(1000 * pct(lat, 99), 3), "max_ms": round(1000 * lat[-1], 3) if lat else float("nan"),
        "server_cpu_pct": round(cpu, 1), "server_rss_mb": round(rss, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--techs", default=",".join(TECHS))
    ap.add_argument("--scenarios", default=",".join(SCENARIOS))
    ap.add_argument("--concurrency", default="1,10,50,100")
    ap.add_argument("--duration", type=float, default=10)
    ap.add_argument("--warmup", type=float, default=2)
    ap.add_argument("--max-procs", type=int, default=max(1, (os.cpu_count() or 2) // 2),
                    help="processos do gerador de carga (default: metade dos núcleos)")
    ap.add_argument("--out", default="results/benchmark.csv")
    ap.add_argument("--quick", action="store_true", help="duração 3s, concorrência 1,10,50")
    a = ap.parse_args()
    if a.quick:
        a.duration, a.warmup, a.concurrency = 3, 1, "1,10,50"

    levels = [int(x) for x in a.concurrency.split(",")]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ctx = mp.get_context("spawn")
    with out.open("w", newline="") as f, ctx.Pool(a.max_procs, initializer=warm_imports) as pool:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        for tech in a.techs.split(","):
            print(f"\n=== {tech.upper()} ===", flush=True)
            proc = start_server(tech, out.parent / "logs")
            try:
                for scenario in a.scenarios.split(","):
                    for conc in levels:
                        row = measure(pool, proc, tech, scenario, conc, a.warmup, a.duration, a.max_procs)
                        w.writerow(row)
                        f.flush()
                        print(f"{tech:8s} {scenario:22s} c={conc:<4d} {row['ops_per_s']:>9.1f} ops/s  "
                              f"p95={row['p95_ms']:>8.2f} ms  err={row['errors']}", flush=True)
            finally:
                proc.terminate()
                try:
                    proc.wait(10)
                except subprocess.TimeoutExpired:
                    proc.kill()
    print(f"\nResultados em {out}")


if __name__ == "__main__":
    main()
