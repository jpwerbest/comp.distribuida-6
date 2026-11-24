"""Gera a apresentação (.pptx) do Trabalho 6 a partir dos resultados reais.

Uso:
  python scripts/build_slides.py --members "Fulano (matrícula), Ciclana (matrícula)" --course "Computação Distribuída"
Depois, envie o .pptx ao Google Drive e abra com Google Slides (ou use "Salvar como Google Slides").
Os slides marcados com [EDITAR] pedem a SUA análise pessoal da experiência de implementação.
"""
import argparse
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
CHARTS = ROOT / "results" / "charts"
NAVY, GRAY, LIGHT = RGBColor(0x1B, 0x3E, 0x7A), RGBColor(0x44, 0x44, 0x44), RGBColor(0xF2, 0xF4, 0xF8)
LABEL = {"rest": "REST", "graphql": "GraphQL", "grpc": "gRPC", "soap": "SOAP"}
SCEN = {"get_song": "Leitura simples", "list_songs": "Lista grande (1000 músicas)",
        "user_playlists_songs": "Consulta composta", "write": "Escrita", "mixed": "Carga mista"}

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def text(slide, l, t, w, h, lines, size=18, bold=False, color=GRAY, font=None):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines if isinstance(lines, list) else [lines]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = line
        r.font.size, r.font.bold, r.font.color.rgb = Pt(size), bold, color
        if font:
            r.font.name = font
        p.space_after = Pt(6)
    return tb


def new(title):
    s = prs.slides.add_slide(BLANK)
    bar = s.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(1.0))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    text(s, 0.5, 0.2, 12.3, 0.7, title, size=30, bold=True, color=RGBColor(255, 255, 255))
    return s


def bullets(s, l, t, w, h, items, size=17, head=None):
    lines = ([head] if head else []) + [f"• {i}" for i in items]
    tb = text(s, l, t, w, h, lines, size=size)
    if head:
        r = tb.text_frame.paragraphs[0].runs[0]
        r.font.bold, r.font.color.rgb = True, NAVY
        r.font.size = Pt(size + 2)


def code(s, l, t, w, h, src, caption, size=12):
    box = s.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    box.fill.solid()
    box.fill.fore_color.rgb = LIGHT
    box.line.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
    text(s, l, t - 0.4, w, 0.4, caption, size=14, bold=True, color=NAVY)
    tb = s.shapes.add_textbox(Inches(l + 0.1), Inches(t + 0.05), Inches(w - 0.2), Inches(h - 0.1))
    tb.text_frame.word_wrap = True
    for i, line in enumerate(src.strip("\n").split("\n")):
        p = tb.text_frame.paragraphs[0] if i == 0 else tb.text_frame.add_paragraph()
        r = p.add_run()
        r.text = line
        r.font.size, r.font.name, r.font.color.rgb = Pt(size), "Consolas", RGBColor(0x20, 0x20, 0x20)


def table(s, l, t, w, rows, col_w=None, size=13):
    sh = s.shapes.add_table(len(rows), len(rows[0]), Inches(l), Inches(t), Inches(w), Inches(0.4 * len(rows)))
    tb = sh.table
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = tb.cell(i, j)
            c.text = str(val)
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(size)
                    r.font.bold = i == 0 or j == 0
                    r.font.color.rgb = RGBColor(255, 255, 255) if i == 0 else GRAY
            c.fill.solid()
            c.fill.fore_color.rgb = NAVY if i == 0 else (LIGHT if i % 2 else RGBColor(255, 255, 255))
    if col_w:
        for j, cw in enumerate(col_w):
            tb.columns[j].width = Inches(cw)


def picture(s, name, l, t, w):
    f = CHARTS / name
    if f.exists():
        s.shapes.add_picture(str(f), Inches(l), Inches(t), width=Inches(w))
    else:
        text(s, l, t, w, 1, f"[gráfico {name} não encontrado — rode o benchmark e plot_results]", size=14)


def loc(path):
    p = ROOT / path
    return sum(1 for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.strip().startswith("#")) if p.exists() else 0


def analysis_bullets(df):
    top = df.concurrency.max()
    d = df[df.concurrency == top]
    out = []
    for sc, name in SCEN.items():
        g = d[d.scenario == sc].set_index("tech")
        if g.empty:
            continue
        best, worst = g.ops_per_s.idxmax(), g.ops_per_s.idxmin()
        low = g.p95_ms.idxmin()
        out.append(f"{name}: maior vazão = {LABEL[best]} ({g.ops_per_s[best]:.0f} ops/s); "
                   f"menor = {LABEL[worst]} ({g.ops_per_s[worst]:.0f}); menor p95 = {LABEL[low]} ({g.p95_ms[low]:.1f} ms)")
    return top, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--members", default="Nome Sobrenome (matrícula), Nome Sobrenome (matrícula)")
    ap.add_argument("--course", default="Computação Distribuída")
    ap.add_argument("--out", default="results/Trabalho6_Comparacao_Tecnologias.pptx")
    a = ap.parse_args()

    # 1 -------------------------------------------------------------- capa
    s = new("Comparação de Tecnologias de Invocação de Serviços Remotos")
    text(s, 0.8, 1.6, 11.5, 0.6, f"{a.course} — Trabalho 6", size=24, color=NAVY, bold=True)
    text(s, 0.8, 2.6, 11.5, 0.5, "Equipe:", size=20, bold=True)
    text(s, 0.8, 3.1, 11.5, 2, [m.strip() for m in a.members.split(",")], size=22)
    text(s, 0.8, 6.2, 11.8, 0.8, "SOAP · REST · GraphQL · gRPC — serviço de streaming de músicas implementado em Python", size=16)

    # 2 ------------------------------------------------------ metodologia
    s = new("Objetivo e metodologia")
    bullets(s, 0.6, 1.3, 12, 5.5, [
        "Mesmo domínio nas 4 tecnologias: usuários, músicas e playlists (CRUD completo + consultas relacionais).",
        "Núcleo de domínio único (repositório em memória) compartilhado: só o protocolo muda entre as versões.",
        "Linguagem: Python 3.12 — FastAPI/uvicorn (REST, SOAP, GraphQL via Strawberry) e grpc.aio (gRPC).",
        "Teste de paridade funcional: o mesmo roteiro CRUD executado contra as 4 APIs.",
        "Testes de carga: 5 cenários × 4 níveis de concorrência × 4 tecnologias (vazão, latência p50/p95/p99, CPU/memória).",
        "Massa de dados: 200 usuários, 1.000 músicas, 600 playlists (10 músicas cada).",
    ], size=19)

    # 3-6 ---------------------------------------------------- tecnologias
    techs = [
        ("SOAP", ["Criado em 1998 (Microsoft e parceiros); SOAP 1.2 é Recomendação W3C desde 2003.",
                  "Mensagens XML em envelope (Envelope/Header/Body/Fault).",
                  "Contrato formal em WSDL + XSD; transporte agnóstico (HTTP é o mais comum).",
                  "Família WS-* (segurança, transações, mensageria confiável)."],
         ["Contrato forte e geração de código", "Padrões corporativos (WS-Security etc.)",
          "Erros padronizados (Fault)", "Independente de transporte"],
         ["Verboso (XML): mais bytes e CPU", "Complexidade e curva de aprendizado",
          "Ecossistema legado, pouca ferramenta moderna", "Cache HTTP pouco aproveitável (POST)"]),
        ("REST", ["Estilo arquitetural proposto por Roy Fielding na tese de doutorado (UC Irvine, 2000).",
                  "Recursos identificados por URIs, manipulados com verbos HTTP.",
                  "Stateless, cacheável, interface uniforme; representações em JSON.",
                  "Contrato opcional via OpenAPI."],
         ["Simples e universal (qualquer cliente HTTP)", "Cache HTTP e CDN nativos",
          "Fácil de depurar (curl, navegador)", "Enorme ecossistema"],
         ["Over/under-fetching", "Várias requisições para dados relacionados (N+1)",
          "Contrato não obrigatório; versionamento", "Sem streaming nativo"]),
        ("GraphQL", ["Criado no Facebook (2012) para apps móveis; aberto em 2015; GraphQL Foundation em 2018.",
                     "Linguagem de consulta + runtime sobre um schema tipado.",
                     "Endpoint único; o cliente escolhe os campos; queries, mutations, subscriptions.",
                     "Introspecção do schema."],
         ["Sem over/under-fetching", "Dados aninhados em 1 round-trip",
          "Schema auto-documentado", "Evolução sem versionar endpoints"],
         ["Cache HTTP mais difícil (POST único)", "Complexidade no servidor (N+1 em resolvers)",
          "Consultas caras exigem limites de custo/profundidade", "Erros com HTTP 200 + campo errors"]),
        ("gRPC", ["Criado no Google (sucessor do Stubby interno); open source em 2015; projeto da CNCF.",
                  "IDL em Protocol Buffers (.proto) + geração de código multi-linguagem.",
                  "HTTP/2: multiplexação, streaming (unário, servidor, cliente, bidirecional).",
                  "Deadlines, metadata, interceptors."],
         ["Alto desempenho (binário + HTTP/2)", "Contratos fortes e codegen", "Streaming nativo",
          "Payload compacto"],
         ["Difícil inspecionar (binário)", "Suporte limitado em navegadores (gRPC-Web/proxy)",
          "Exige toolchain protoc", "Pouco amigável a cache/proxies HTTP"]),
    ]
    for name, feats, pros, cons in techs:
        s = new(name)
        bullets(s, 0.5, 1.2, 6.2, 5.8, feats, size=16, head="Origem e características")
        bullets(s, 7.0, 1.2, 5.8, 2.7, pros, size=16, head="Vantagens")
        bullets(s, 7.0, 4.0, 5.8, 3.0, cons, size=16, head="Desvantagens")

    # 7-10 --------------------------------------------------------- código
    snippets = {
        "SOAP": ("""
# soap_wire.py — contrato (operação -> tipos -> handler)
Op("GetSong", (("id", "int"),),
   ("song", "Song", False),
   lambda s, i: s.get_song(i))

# soap_server.py
@app.post("/soap")
async def soap_endpoint(request: Request):
    status, xml = handle_soap(store, await request.body())
    return Response(xml, status_code=status,
                    media_type="application/soap+xml")
""", """
# soap_client.py — envelope XML + POST
body = sw.build_request("GetSong", [42])
r = http.post(url, data=body, headers={
    "Content-Type": "application/soap+xml"})
song = sw.parse_response("GetSong", r.content)

# Requisição na rede:
# <env:Envelope><env:Body>
#   <tns:GetSong><tns:id>42</tns:id></tns:GetSong>
# </env:Body></env:Envelope>
"""),
        "REST": ("""
# rest_server.py
@app.get("/songs/{song_id}")
async def get_song(song_id: int):
    return store.get_song(song_id)

@app.post("/users", status_code=201)
async def create_user(body: UserIn):
    return store.create_user(body.name, body.age)
""", """
# rest_client.py
song = http.get(f"{base}/songs/42").json()

# playlists de um usuário (1 + N chamadas p/ ter as músicas)
pls = http.get(f"{base}/users/7/playlists").json()
for p in pls:
    p["songs"] = http.get(
        f"{base}/playlists/{p['id']}/songs").json()
"""),
        "GraphQL": ("""
# graphql_server.py
@strawberry.type
class Playlist:
    id: int
    name: str
    @strawberry.field
    def songs(self) -> List[Song]:
        return [_song(s) for s in
                store.list_playlist_songs(self.id)]

@strawberry.type
class Query:
    @strawberry.field
    def song(self, id: int) -> Song:
        return _song(store.get_song(id))
""", """
# graphql_client.py — UMA chamada traz tudo
query = '''query($id:Int!){ user(id:$id){
  playlists { id name
    songs { id name artist } } } }'''
data = http.post(url, json={"query": query,
        "variables": {"id": 7}}).json()["data"]
"""),
        "gRPC": ("""
// music.proto
service SongService {
  rpc GetSong (IdRequest) returns (Song);
}
message Song { int32 id = 1; string name = 2;
               string artist = 3; }

# grpc_server.py
class SongService(pb_grpc.SongServiceServicer):
    @rpc
    def GetSong(self, r, c):
        return _song(store.get_song(r.id))
""", """
# grpc_client.py
channel = grpc.insecure_channel("127.0.0.1:8003")
stub = pb_grpc.SongServiceStub(channel)
song = stub.GetSong(pb.IdRequest(id=42), timeout=30)

# erros -> status codes
# except grpc.RpcError as e:
#     e.code()  # NOT_FOUND, INVALID_ARGUMENT...
"""),
    }
    for name, (srv, cli) in snippets.items():
        s = new(f"{name} — exemplo de código (Python)")
        code(s, 0.4, 1.6, 6.3, 5.3, srv, "Servidor / contrato")
        code(s, 6.9, 1.6, 6.0, 5.3, cli, "Cliente")

    # 11 ------------------------------------------------------ comparativo
    s = new("Comparativo: similaridades e diferenças")
    table(s, 0.4, 1.3, 12.5, [
        ["", "SOAP", "REST", "GraphQL", "gRPC"],
        ["Formato", "XML", "JSON (geralmente)", "JSON", "Protobuf (binário)"],
        ["Transporte", "HTTP (agnóstico)", "HTTP/1.1+", "HTTP/1.1+", "HTTP/2"],
        ["Contrato", "WSDL/XSD", "OpenAPI (opcional)", "Schema SDL", ".proto"],
        ["Modelo", "Operações (RPC)", "Recursos + verbos", "Consulta sobre grafo", "Operações (RPC)"],
        ["Dados relacionados", "N chamadas", "N chamadas (N+1)", "1 chamada", "N chamadas"],
        ["Streaming", "Não nativo", "Não nativo", "Subscriptions", "Nativo (4 modos)"],
        ["Cache HTTP", "Difícil", "Nativo", "Difícil", "Difícil"],
        ["Navegador", "Sim", "Sim", "Sim", "gRPC-Web / proxy"],
        ["Erros", "Fault", "Status HTTP", "campo errors (HTTP 200)", "Status codes gRPC"],
    ], col_w=[2.3, 2.5, 2.6, 2.6, 2.5], size=14)
    text(s, 0.4, 5.6, 12.5, 1.2, "Todas atendem ao mesmo requisito (invocar operações remotas independente de plataforma/linguagem) — "
         "diferem em acoplamento, desempenho, tooling e adequação ao cliente.", size=16)

    # 12 ---------------------------------------------------- implementação
    s = new("Implementação do serviço de streaming de músicas")
    rows = [["Tecnologia", "Arquivos principais", "Linhas (sem comentários)"]]
    rows += [["SOAP", "soap_wire.py + soap_server.py", loc("musicstream/soap_wire.py") + loc("musicstream/servers/soap_server.py")],
             ["REST", "rest_server.py", loc("musicstream/servers/rest_server.py")],
             ["GraphQL", "graphql_server.py", loc("musicstream/servers/graphql_server.py")],
             ["gRPC", "music.proto + grpc_server.py (+ stubs gerados)", loc("musicstream/servers/grpc_server.py") + loc("proto/music.proto")]]
    table(s, 0.5, 1.4, 7.4, rows, col_w=[1.6, 3.8, 2.0], size=14)
    bullets(s, 8.2, 1.3, 4.8, 5.5, [
        "Núcleo único: store.py (regras + validação + cascata).",
        "Servidores = adaptadores finos sobre o núcleo.",
        "Mesma interface de cliente nas 4 versões.",
        "SOAP implementado à mão (envelope + WSDL) — evidencia o custo do protocolo.",
        "gRPC e GraphQL: contrato gera/valida automaticamente.",
    ], size=15)
    text(s, 0.5, 4.2, 7.4, 2.5, "Nota: a contagem de linhas do SOAP inclui o protocolo completo escrito manualmente; "
         "com um framework SOAP maduro seria bem menor.", size=14)

    # 13 --------------------------------------------- metodologia de carga
    s = new("Metodologia dos testes de carga")
    bullets(s, 0.6, 1.3, 12.2, 5.6, [
        "Cenários: leitura simples · lista grande (1000 músicas) · consulta composta (playlists + músicas) · escrita (criar+remover) · carga mista (50/20/10/20%).",
        "Concorrência: 1, 10, 50 e 100 usuários virtuais (threads em múltiplos processos), conexões persistentes (keep-alive / canal gRPC).",
        "Cada ponto: 2 s de aquecimento + 10 s de medição; métricas: ops/s, p50/p95/p99, erros, CPU e RSS do servidor.",
        "Um servidor por vez (sem competir por CPU), mesma máquina, mesmo gerador de carga e mesma massa de dados.",
        "Consulta composta: cada tecnologia usa seu modo natural (REST/SOAP/gRPC: 1+N chamadas; GraphQL: 1 chamada).",
        "Limitações: gerador em Python e na mesma máquina do servidor; resultados valem para comparação relativa, não absoluta.",
    ], size=17)

    # 14-17 ------------------------------------------------------ gráficos
    s = new("Resultados — vazão")
    picture(s, "summary_throughput.png", 0.7, 1.2, 12.0)
    s = new("Resultados — latência p95")
    picture(s, "summary_p95.png", 0.7, 1.2, 12.0)
    s = new("Resultados — consulta composta (N+1 vs. 1 chamada)")
    picture(s, "user_playlists_songs.png", 0.7, 1.3, 12.0)
    s = new("Resultados — carga mista e leitura simples")
    picture(s, "mixed.png", 0.2, 1.3, 6.5)
    picture(s, "get_song.png", 6.7, 1.3, 6.5)
    s = new("Resultados — lista grande e escrita")
    picture(s, "list_songs.png", 0.2, 1.3, 6.5)
    picture(s, "write.png", 6.7, 1.3, 6.5)
    s = new("Resultados — tamanho de payload e uso de CPU")
    picture(s, "payload_sizes.png", 0.2, 1.3, 6.5)
    picture(s, "summary_cpu.png", 6.7, 1.3, 6.5)

    # 18 ----------------------------------------------------------- análise
    csv = ROOT / "results" / "benchmark.csv"
    s = new("Análise crítica (dados dos testes de carga)")
    if csv.exists():
        top, auto = analysis_bullets(pd.read_csv(csv))
        bullets(s, 0.5, 1.2, 12.3, 4.2, auto, size=15, head=f"Com {top} usuários concorrentes")
    bullets(s, 0.5, 5.1, 12.3, 2.2, [
        "[EDITAR] Explique POR QUE os números saíram assim (serialização, HTTP/2, N+1, framework, GIL).",
        "[EDITAR] Relate sua experiência: esforço de implementação, depuração, tooling, curva de aprendizado de cada tecnologia.",
    ], size=15, head="Interpretação da equipe")

    # 19 -------------------------------------------------------- conclusão
    s = new("Conclusão: quando escolher cada tecnologia")
    table(s, 0.5, 1.4, 12.3, [
        ["Tecnologia", "Melhor quando...", "Evite quando..."],
        ["REST", "API pública, simplicidade, cache HTTP, ampla interoperabilidade", "Clientes precisam de dados aninhados/variáveis (N+1)"],
        ["GraphQL", "Clientes diversos (web/mobile) com necessidades de dados distintas", "Operações simples, forte dependência de cache HTTP"],
        ["gRPC", "Microsserviços internos, baixa latência, streaming", "Consumo direto por navegadores / integração com terceiros"],
        ["SOAP", "Integração corporativa/legada com WS-* e contratos rígidos", "Novos projetos sem exigência de WS-* (custo de XML/complexidade)"],
    ], col_w=[1.8, 5.4, 5.1], size=15)
    text(s, 0.5, 5.2, 12.3, 1.5, "[EDITAR] Conclusão final da equipe, alinhada aos resultados medidos.", size=16)

    # 20 ---------------------------------------------------- referências
    s = new("Referências")
    text(s, 0.6, 1.3, 12.2, 5.8, [
        "[1] W3C. SOAP Version 1.2 Part 1: Messaging Framework (Second Edition). https://www.w3.org/TR/soap12/",
        "[2] Fielding, R. T. Architectural Styles and the Design of Network-Based Software Architectures. UC Irvine, 2000.",
        "[3] REST API Tutorial. https://restfulapi.net/",
        "[4] GraphQL: A query language for your API. https://graphql.org/",
        "[5] gRPC: A high performance, open source universal RPC framework. https://grpc.io/",
        "[6] Stowe, M. XML, SOAP, JSON, REST, GraphQL? (SlideShare).",
        "[7] Brito, G.; Valente, M. T. REST vs GraphQL: A Controlled Experiment. ICSA, 2020.",
        "Repositório do projeto: [EDITAR: link do GitHub]",
    ], size=15)

    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    print(f"Apresentação gerada: {out}")


if __name__ == "__main__":
    main()
