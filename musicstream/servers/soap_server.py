"""SOAP 1.2 sobre HTTP (FastAPI como transporte).  Porta padrão: 8004.

Endpoint: POST http://127.0.0.1:8004/soap      WSDL: GET http://127.0.0.1:8004/soap?wsdl
Toda a lógica do protocolo está em musicstream/soap_wire.py.
"""
import uvicorn
from fastapi import FastAPI, Request, Response

from ..config import HOST, PORTS
from ..soap_wire import build_wsdl, handle_soap
from ..store import build_store

store = build_store()
app = FastAPI(title="Music Streaming - SOAP")
CT = "application/soap+xml; charset=utf-8"


@app.post("/soap")
async def soap_endpoint(request: Request):
    status, xml = handle_soap(store, await request.body())
    return Response(xml, status_code=status, media_type=CT)


@app.get("/soap")
async def wsdl(request: Request):
    location = str(request.base_url).rstrip("/") + "/soap"
    return Response(build_wsdl(location), media_type="text/xml; charset=utf-8")


def main():
    uvicorn.run(app, host=HOST, port=PORTS["soap"], log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
