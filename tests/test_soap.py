"""Testa o SOAP de ponta a ponta com um servidor HTTP stdlib (sem FastAPI)."""
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from lxml import etree

from musicstream import soap_wire as sw
from musicstream.clients import make_client
from musicstream.errors import RemoteError
from musicstream.smoke import check
from musicstream.store import build_store

SMALL = {"users": 3, "songs": 10, "playlists_per_user": 2, "songs_per_playlist": 3, "random_seed": 1}


@pytest.fixture()
def server():
    store = build_store(SMALL)

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            data = self.rfile.read(int(self.headers["Content-Length"]))
            status, xml = sw.handle_soap(store, data)
            self.send_response(status)
            self.send_header("Content-Length", str(len(xml)))
            self.end_headers()
            self.wfile.write(xml)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


def test_wsdl_is_wellformed():
    etree.fromstring(sw.build_wsdl("http://localhost/soap").encode())


def test_full_crud_over_http(server):
    c = make_client("soap", port=server)
    check(c)
    c.close()


def test_fault_on_unknown_op_and_bad_xml():
    store = build_store(SMALL)
    st, body = sw.handle_soap(store, b"<nope")
    assert st == 400 and b"Fault" in body
    st, body = sw.handle_soap(store, sw.build_request("GetUser", [999]))
    assert st == 400 and b"NotFound" in body
    with pytest.raises(RemoteError):
        sw.parse_response("GetUser", body)


def test_xxe_is_not_resolved():
    evil = (b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>'
            b'<env:Envelope xmlns:env="http://www.w3.org/2003/05/soap-envelope"><env:Body>'
            b'<tns:CreateUser xmlns:tns="urn:musicstream"><tns:name>&e;</tns:name><tns:age>1</tns:age>'
            b'</tns:CreateUser></env:Body></env:Envelope>')
    _, body = sw.handle_soap(build_store(SMALL), evil)
    assert b"root:" not in body
