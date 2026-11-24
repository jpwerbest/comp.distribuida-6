"""Sobe os 4 servidores de uma vez (para demonstração/manual). Ctrl+C encerra."""
import subprocess
import sys
import time

from .config import PORTS, SERVER_MODULES

procs = [subprocess.Popen([sys.executable, "-m", m]) for m in SERVER_MODULES.values()]
print("Servidores iniciados:", {k: f"http://127.0.0.1:{v}" for k, v in PORTS.items()})
print("Ctrl+C para encerrar.")
try:
    while True:
        time.sleep(1)
        dead = [p for p in procs if p.poll() is not None]
        if dead:
            print("Um servidor encerrou inesperadamente; encerrando todos.")
            break
except KeyboardInterrupt:
    pass
finally:
    for p in procs:
        p.terminate()
