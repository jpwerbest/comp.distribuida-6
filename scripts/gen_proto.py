"""Gera os stubs gRPC em musicstream/generated a partir de proto/music.proto."""
import re
import sys
from pathlib import Path

from grpc_tools import protoc

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "musicstream" / "generated"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "__init__.py").touch()

rc = protoc.main(["protoc", f"-I{ROOT / 'proto'}", f"--python_out={OUT}",
                  f"--grpc_python_out={OUT}", str(ROOT / "proto" / "music.proto")])
if rc != 0:
    sys.exit(rc)

# protoc gera "import music_pb2" (absoluto); troca por import relativo ao pacote.
grpc_file = OUT / "music_pb2_grpc.py"
grpc_file.write_text(re.sub(r"^import music_pb2 as", "from . import music_pb2 as",
                            grpc_file.read_text(), flags=re.M))
print(f"Stubs gerados em {OUT}")
