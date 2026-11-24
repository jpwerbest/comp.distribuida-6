"""Gera os gráficos a partir de results/benchmark.csv (+ payload_sizes.csv).

Uso: python -m musicstream.bench.plot_results   ->  results/charts/*.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

COLORS = {"rest": "#1f77b4", "graphql": "#e10098", "grpc": "#2ca02c", "soap": "#ff7f0e"}
LABEL = {"rest": "REST", "graphql": "GraphQL", "grpc": "gRPC", "soap": "SOAP"}
SCEN = {"get_song": "Leitura simples (get_song)", "list_songs": "Lista grande (1000 músicas)",
        "user_playlists_songs": "Consulta composta (playlists + músicas)",
        "write": "Escrita (criar + remover usuário)", "mixed": "Carga mista"}
OUT = Path("results/charts")


def lines(df, scenario):
    d = df[df.scenario == scenario]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for tech, g in d.groupby("tech"):
        g = g.sort_values("concurrency")
        ax[0].plot(g.concurrency, g.ops_per_s, "o-", label=LABEL[tech], color=COLORS[tech])
        ax[1].plot(g.concurrency, g.p95_ms, "o-", label=LABEL[tech], color=COLORS[tech])
    ax[0].set(title="Vazão (operações/s)", xlabel="Usuários concorrentes", ylabel="ops/s")
    ax[1].set(title="Latência p95 (ms)", xlabel="Usuários concorrentes", ylabel="ms")
    for a in ax:
        a.grid(alpha=.3)
        a.legend()
    fig.suptitle(SCEN.get(scenario, scenario))
    fig.tight_layout()
    fig.savefig(OUT / f"{scenario}.png", dpi=150)
    plt.close(fig)


def grouped(df, col, title, ylabel, fname, log=False):
    top = df.concurrency.max()
    p = df[df.concurrency == top].pivot(index="scenario", columns="tech", values=col)
    p = p.reindex([s for s in SCEN if s in p.index])
    fig, ax = plt.subplots(figsize=(11, 4.5))
    w = 0.8 / len(p.columns)
    for i, tech in enumerate(c for c in COLORS if c in p.columns):
        ax.bar([x + i * w for x in range(len(p))], p[tech], w, label=LABEL[tech], color=COLORS[tech])
    ax.set_xticks([x + 0.4 - w / 2 for x in range(len(p))])
    ax.set_xticklabels([SCEN[s].split(" (")[0] for s in p.index], rotation=15, ha="right")
    ax.set(title=f"{title} — {top} usuários concorrentes", ylabel=ylabel)
    if log:
        ax.set_yscale("log")
    ax.grid(axis="y", alpha=.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=150)
    plt.close(fig)


def payload():
    f = Path("results/payload_sizes.csv")
    if not f.exists():
        return
    d = pd.read_csv(f).set_index("scenario")
    fig, ax = plt.subplots(figsize=(10, 4.5))
    cols = [c for c in COLORS if c in d.columns and d[c].notna().all()]
    w = 0.8 / len(cols)
    for i, tech in enumerate(cols):
        ax.bar([x + i * w for x in range(len(d))], d[tech], w, label=LABEL[tech], color=COLORS[tech])
    ax.set_xticks([x + 0.4 - w / 2 for x in range(len(d))])
    ax.set_xticklabels(d.index)
    ax.set(title="Bytes transferidos no corpo das respostas", ylabel="bytes (escala log)", yscale="log")
    ax.grid(axis="y", alpha=.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "payload_sizes.png", dpi=150)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv("results/benchmark.csv")
    for sc in df.scenario.unique():
        lines(df, sc)
    grouped(df, "ops_per_s", "Vazão por cenário", "ops/s", "summary_throughput.png")
    grouped(df, "p95_ms", "Latência p95 por cenário", "ms (escala log)", "summary_p95.png", log=True)
    if df.server_cpu_pct.notna().any():
        grouped(df, "server_cpu_pct", "CPU do servidor", "% de um núcleo", "summary_cpu.png")
    payload()
    print(f"Gráficos em {OUT}/")


if __name__ == "__main__":
    main()
