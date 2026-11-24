from ..config import HOST, PORTS


def make_client(tech, host=HOST, port=None):
    """Fábrica com import preguiçoso (não exige grpc para testar só SOAP, etc.)."""
    port = port or PORTS[tech]
    if tech == "rest":
        from .rest_client import RestClient
        return RestClient(host, port)
    if tech == "graphql":
        from .graphql_client import GraphQLClient
        return GraphQLClient(host, port)
    if tech == "grpc":
        from .grpc_client import GrpcClient
        return GrpcClient(host, port)
    if tech == "soap":
        from .soap_client import SoapClient
        return SoapClient(host, port)
    raise ValueError(f"tecnologia desconhecida: {tech}")
