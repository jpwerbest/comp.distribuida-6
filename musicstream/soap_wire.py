"""Camada SOAP 1.2 (document/literal wrapped), independente de framework web.

Contém: registro de operações, geração do WSDL, parsing de requisições,
serialização de respostas/Faults e (lado cliente) construção/parse de envelopes.

Por que implementar à mão? As bibliotecas de servidor SOAP para Python são
pouco mantidas e com problemas de compatibilidade em versões recentes do
Python. Implementar o protocolo (envelope + WSDL) deixa explícito o que o SOAP
realmente exige, e permite testar o núcleo sem subir servidor HTTP.
"""
from dataclasses import dataclass
from typing import Callable, Optional
from xml.sax.saxutils import quoteattr

from lxml import etree

from .errors import Invalid, NotFound, RemoteError

ENV = "http://www.w3.org/2003/05/soap-envelope"
NS = "urn:musicstream"
NSMAP = {"env": ENV, "tns": NS}

# Esquema de cada tipo: (elemento XML, tipo, chave no dict de domínio)
TYPES = {
    "User": [("id", "int", "id"), ("name", "string", "name"), ("age", "int", "age")],
    "Song": [("id", "int", "id"), ("name", "string", "name"), ("artist", "string", "artist")],
    "Playlist": [("id", "int", "id"), ("name", "string", "name"),
                 ("userId", "int", "user_id"), ("songId", "int*", "song_ids")],
}


@dataclass(frozen=True)
class Op:
    name: str
    params: tuple                  # ((nome, tipo), ...) tipo: int | string | int*
    returns: Optional[tuple]       # (elemento, tipo, muitos?) ou None
    call: Callable                 # (store, *args) -> resultado


_ID = (("id", "int"),)
OPS = {o.name: o for o in [
    Op("ListUsers", (), ("user", "User", True), lambda s: s.list_users()),
    Op("GetUser", _ID, ("user", "User", False), lambda s, i: s.get_user(i)),
    Op("CreateUser", (("name", "string"), ("age", "int")), ("user", "User", False),
       lambda s, n, a: s.create_user(n, a)),
    Op("UpdateUser", (("id", "int"), ("name", "string"), ("age", "int")), ("user", "User", False),
       lambda s, i, n, a: s.update_user(i, n, a)),
    Op("DeleteUser", _ID, None, lambda s, i: s.delete_user(i)),
    Op("ListUserPlaylists", (("userId", "int"),), ("playlist", "Playlist", True),
       lambda s, i: s.list_user_playlists(i)),

    Op("ListSongs", (), ("song", "Song", True), lambda s: s.list_songs()),
    Op("GetSong", _ID, ("song", "Song", False), lambda s, i: s.get_song(i)),
    Op("CreateSong", (("name", "string"), ("artist", "string")), ("song", "Song", False),
       lambda s, n, a: s.create_song(n, a)),
    Op("UpdateSong", (("id", "int"), ("name", "string"), ("artist", "string")), ("song", "Song", False),
       lambda s, i, n, a: s.update_song(i, n, a)),
    Op("DeleteSong", _ID, None, lambda s, i: s.delete_song(i)),
    Op("ListSongPlaylists", (("songId", "int"),), ("playlist", "Playlist", True),
       lambda s, i: s.list_song_playlists(i)),

    Op("ListPlaylists", (), ("playlist", "Playlist", True), lambda s: s.list_playlists()),
    Op("GetPlaylist", _ID, ("playlist", "Playlist", False), lambda s, i: s.get_playlist(i)),
    Op("CreatePlaylist", (("userId", "int"), ("name", "string"), ("songId", "int*")),
       ("playlist", "Playlist", False), lambda s, u, n, ids: s.create_playlist(u, n, ids)),
    Op("UpdatePlaylist", (("id", "int"), ("name", "string")), ("playlist", "Playlist", False),
       lambda s, i, n: s.update_playlist(i, n)),
    Op("DeletePlaylist", _ID, None, lambda s, i: s.delete_playlist(i)),
    Op("ListPlaylistSongs", (("playlistId", "int"),), ("song", "Song", True),
       lambda s, i: s.list_playlist_songs(i)),
    Op("AddSongToPlaylist", (("playlistId", "int"), ("songId", "int")), ("playlist", "Playlist", False),
       lambda s, p, i: s.add_song(p, i)),
    Op("RemoveSongFromPlaylist", (("playlistId", "int"), ("songId", "int")), ("playlist", "Playlist", False),
       lambda s, p, i: s.remove_song(p, i)),
]}

_PARSER = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)


def _q(name):
    return f"{{{NS}}}{name}"


class SoapFault(Exception):
    def __init__(self, code, reason, subcode=None):
        super().__init__(reason)
        self.code, self.reason, self.subcode = code, reason, subcode


# ----------------------------------------------------------------- WSDL
def build_wsdl(location: str) -> str:
    x = []
    for tname, fields in TYPES.items():
        x.append(f'<xsd:complexType name="{tname}"><xsd:sequence>')
        for fname, ftype, _ in fields:
            if ftype.endswith("*"):
                x.append(f'<xsd:element name="{fname}" type="xsd:int" minOccurs="0" maxOccurs="unbounded"/>')
            else:
                x.append(f'<xsd:element name="{fname}" type="xsd:{ftype}"/>')
        x.append("</xsd:sequence></xsd:complexType>")
    for op in OPS.values():
        x.append(f'<xsd:element name="{op.name}"><xsd:complexType><xsd:sequence>')
        for pname, ptype in op.params:
            if ptype.endswith("*"):
                x.append(f'<xsd:element name="{pname}" type="xsd:int" minOccurs="0" maxOccurs="unbounded"/>')
            else:
                x.append(f'<xsd:element name="{pname}" type="xsd:{ptype}"/>')
        x.append("</xsd:sequence></xsd:complexType></xsd:element>")
        x.append(f'<xsd:element name="{op.name}Response"><xsd:complexType><xsd:sequence>')
        if op.returns:
            el, tname, many = op.returns
            occ = ' minOccurs="0" maxOccurs="unbounded"' if many else ""
            x.append(f'<xsd:element name="{el}" type="tns:{tname}"{occ}/>')
        x.append("</xsd:sequence></xsd:complexType></xsd:element>")
    msgs, ptype_ops, bind_ops = [], [], []
    for op in OPS.values():
        n = op.name
        msgs.append(f'<message name="{n}In"><part name="parameters" element="tns:{n}"/></message>'
                    f'<message name="{n}Out"><part name="parameters" element="tns:{n}Response"/></message>')
        ptype_ops.append(f'<operation name="{n}"><input message="tns:{n}In"/><output message="tns:{n}Out"/></operation>')
        bind_ops.append(f'<operation name="{n}"><soap12:operation soapAction="{NS}:{n}" style="document"/>'
                        '<input><soap12:body use="literal"/></input><output><soap12:body use="literal"/></output></operation>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<definitions xmlns="http://schemas.xmlsoap.org/wsdl/" '
        'xmlns:soap12="http://schemas.xmlsoap.org/wsdl/soap12/" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        f'xmlns:tns="{NS}" targetNamespace="{NS}" name="MusicStreamService">'
        f'<types><xsd:schema targetNamespace="{NS}" elementFormDefault="qualified">{"".join(x)}</xsd:schema></types>'
        f'{"".join(msgs)}'
        f'<portType name="MusicStreamPort">{"".join(ptype_ops)}</portType>'
        '<binding name="MusicStreamBinding" type="tns:MusicStreamPort">'
        '<soap12:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>'
        f'{"".join(bind_ops)}</binding>'
        '<service name="MusicStreamService"><port name="MusicStreamPort" binding="tns:MusicStreamBinding">'
        f'<soap12:address location={quoteattr(location)}/></port></service></definitions>'
    )


# ------------------------------------------------------------- servidor
def _conv(text, ptype, pname):
    if ptype == "string":
        return text or ""
    try:
        return int((text or "").strip())
    except ValueError:
        raise SoapFault("Sender", f"Parameter '{pname}' must be an integer", "tns:Invalid")


def _parse_args(op, el):
    args = []
    for pname, ptype in op.params:
        if ptype.endswith("*"):
            args.append([_conv(c.text, "int", pname) for c in el.findall(_q(pname))])
        else:
            c = el.find(_q(pname))
            if c is None:
                raise SoapFault("Sender", f"Missing parameter '{pname}'", "tns:Invalid")
            args.append(_conv(c.text, ptype, pname))
    return args


def _text(parent, name, value):
    etree.SubElement(parent, _q(name)).text = str(value)


def _put(parent, elem, tname, obj):
    node = etree.SubElement(parent, _q(elem))
    for fname, ftype, key in TYPES[tname]:
        if ftype.endswith("*"):
            for v in obj[key]:
                _text(node, fname, v)
        else:
            _text(node, fname, obj[key])


def _envelope():
    root = etree.Element(f"{{{ENV}}}Envelope", nsmap=NSMAP)
    return root, etree.SubElement(root, f"{{{ENV}}}Body")


def _serialize(root):
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")


def build_response(op, result):
    root, body = _envelope()
    resp = etree.SubElement(body, _q(op.name + "Response"))
    if op.returns:
        el, tname, many = op.returns
        for item in (result if many else [result]):
            _put(resp, el, tname, item)
    return _serialize(root)


def build_fault(code, reason, subcode=None):
    root, body = _envelope()
    fault = etree.SubElement(body, f"{{{ENV}}}Fault")
    c = etree.SubElement(fault, f"{{{ENV}}}Code")
    etree.SubElement(c, f"{{{ENV}}}Value").text = f"env:{code}"
    if subcode:
        sc = etree.SubElement(c, f"{{{ENV}}}Subcode")
        etree.SubElement(sc, f"{{{ENV}}}Value").text = subcode
    r = etree.SubElement(fault, f"{{{ENV}}}Reason")
    t = etree.SubElement(r, f"{{{ENV}}}Text")
    t.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
    t.text = reason
    return _serialize(root)


def handle_soap(store, data: bytes):
    """Processa um envelope SOAP e devolve (status_http, corpo_xml)."""
    try:
        try:
            root = etree.fromstring(data, _PARSER)
        except etree.XMLSyntaxError as e:
            raise SoapFault("Sender", f"Malformed XML: {e}", "tns:Invalid")
        if root.tag != f"{{{ENV}}}Envelope":
            raise SoapFault("VersionMismatch", "Expected a SOAP 1.2 Envelope")
        body = root.find(f"{{{ENV}}}Body")
        if body is None or len(body) == 0:
            raise SoapFault("Sender", "Empty SOAP Body", "tns:Invalid")
        op_el = body[0]
        op = OPS.get(etree.QName(op_el).localname)
        if op is None or etree.QName(op_el).namespace != NS:
            raise SoapFault("Sender", f"Unknown operation '{etree.QName(op_el).localname}'", "tns:Invalid")
        return 200, build_response(op, op.call(store, *_parse_args(op, op_el)))
    except SoapFault as f:
        return (500 if f.code == "Receiver" else 400), build_fault(f.code, f.reason, f.subcode)
    except NotFound as e:
        return 400, build_fault("Sender", str(e), "tns:NotFound")
    except Invalid as e:
        return 400, build_fault("Sender", str(e), "tns:Invalid")
    except Exception as e:  # noqa: BLE001 - qualquer erro inesperado vira Fault Receiver
        return 500, build_fault("Receiver", f"Internal error: {e.__class__.__name__}")


# -------------------------------------------------------------- cliente
def build_request(op_name, args=()):
    op = OPS[op_name]
    root, body = _envelope()
    el = etree.SubElement(body, _q(op.name))
    for (pname, ptype), value in zip(op.params, args):
        for v in (value if ptype.endswith("*") else [value]):
            _text(el, pname, v)
    return _serialize(root)


def _from_node(tname, node):
    out = {}
    for fname, ftype, key in TYPES[tname]:
        kids = node.findall(_q(fname))
        if ftype.endswith("*"):
            out[key] = [int(k.text) for k in kids]
        elif ftype == "int":
            out[key] = int(kids[0].text)
        else:
            out[key] = kids[0].text or ""
    return out


def parse_response(op_name, data: bytes):
    op = OPS[op_name]
    root = etree.fromstring(data, _PARSER)
    first = root.find(f"{{{ENV}}}Body")[0]
    if first.tag == f"{{{ENV}}}Fault":
        reason = first.findtext(f"{{{ENV}}}Reason/{{{ENV}}}Text") or "SOAP Fault"
        raise RemoteError(reason)
    if not op.returns:
        return None
    el, tname, many = op.returns
    items = [_from_node(tname, n) for n in first.findall(_q(el))]
    return items if many else items[0]
