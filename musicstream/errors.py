"""Exceções compartilhadas entre as quatro implementações."""


class NotFound(Exception):
    """Recurso inexistente (REST 404 / gRPC NOT_FOUND / SOAP Fault Sender)."""


class Invalid(Exception):
    """Dados inválidos (REST 400 / gRPC INVALID_ARGUMENT / SOAP Fault Sender)."""


class RemoteError(Exception):
    """Erro visto pelo CLIENTE, independente da tecnologia de transporte."""
