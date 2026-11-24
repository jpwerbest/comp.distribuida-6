"""Executa o pipeline completo: stubs -> servidores -> smoke -> benchmark -> payload -> gráficos -> slides.

Uso: python scripts/run_all.py --quick --members "Nome 1 (mat), Nome 2 (mat)"
"""
import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from musicstream.config import HOST, PORTS, SERVER_MODULES  # noqa: E402

PY = sys.executable


def run(*args):
    print("\n>>", "python", *args, flush=True)
    if subprocess.run([PY, *args], cwd=ROOT).returncode != 0:
        sys.exit(f"Falhou: {' '.join(args)}")


def wait_port(port, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        try:
            socket.create_connection((HOST, port), timeout=0.5).close()
            return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError(f"porta {port} não abriu")


def smoke():
    procs = [subprocess.Popen([PY, "-m", m], cwd=ROOT) for m in SERVER_MODULES.values()]
    try:
        for p in PORTS.values():
            wait_port(p)
        run("-m", "musicstream.smoke")
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait(10)


ap = argparse.ArgumentParser()
ap.add_argument("--quick", action="store_true", help="benchmark rápido (~4 min)")
ap.add_argument("--members", default="Nome 1 (matrícula), Nome 2 (matrícula)")
a = ap.parse_args()

run("scripts/gen_proto.py")
smoke()
run("-m", "musicstream.bench.run_benchmark", *(["--quick"] if a.quick else []))
run("-m", "musicstream.bench.payload_sizes")
run("-m", "musicstream.bench.plot_results")
run("scripts/build_slides.py", "--members", a.members)
print("\nPronto! Veja results/ (CSV, charts/ e o .pptx).")