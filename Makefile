PY ?= python

.PHONY: setup proto servers smoke test bench bench-quick payload charts slides all clean
setup:        ## instala dependências e gera stubs gRPC
	$(PY) -m pip install -r requirements.txt
	$(PY) scripts/gen_proto.py
proto:
	$(PY) scripts/gen_proto.py
servers:      ## sobe os 4 servidores (Ctrl+C encerra)
	$(PY) -m musicstream.run_servers
smoke:        ## paridade funcional (servidores no ar)
	$(PY) -m musicstream.smoke
test:         ## testes unitários
	$(PY) -m pytest -q tests
bench:        ## benchmark completo (~15 min)
	$(PY) -m musicstream.bench.run_benchmark
bench-quick:  ## benchmark rápido (~4 min)
	$(PY) -m musicstream.bench.run_benchmark --quick
payload:
	$(PY) -m musicstream.bench.payload_sizes
charts:
	$(PY) -m musicstream.bench.plot_results
slides:
	$(PY) scripts/build_slides.py
all: bench payload charts slides
clean:
	rm -rf results/*.csv results/*.pptx results/charts/* results/logs
