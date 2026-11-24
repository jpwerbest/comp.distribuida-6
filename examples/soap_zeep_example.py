"""Cliente SOAP 'de verdade' via WSDL usando zeep (pip install zeep).

Com o servidor SOAP rodando:  python examples/soap_zeep_example.py
O zeep lê o WSDL em /soap?wsdl e gera os métodos dinamicamente — equivalente
aos stubs gerados do gRPC. (Não usado no benchmark por ter overhead próprio.)
"""
from zeep import Client

client = Client("http://127.0.0.1:8004/soap?wsdl")
svc = client.service

print(svc.GetSong(id=1))
user = svc.CreateUser(name="Zeep User", age=33)
print(user)
svc.DeleteUser(id=user.id)
