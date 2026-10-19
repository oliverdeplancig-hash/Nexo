"""Gerador do esquema OpenAPI do Nexo (ADR-026).

As rotas feitas como funções (`@api_view`) não declaram serializador; em vez de omitir o corpo delas da
especificação, elas aparecem com corpo JSON livre. A descrição de cada campo dessas rotas fica em
docs/api/README.md.
"""

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.types import OpenApiTypes


class EsquemaNexo(AutoSchema):
    def _sem_serializador(self) -> bool:
        return not hasattr(self.view, "get_serializer") and not getattr(self.view, "serializer_class", None)

    def get_request_serializer(self):
        if self._sem_serializador():
            return OpenApiTypes.OBJECT if self.method in ("POST", "PUT", "PATCH") else None
        return super().get_request_serializer()

    def get_response_serializers(self):
        if self._sem_serializador():
            return OpenApiTypes.OBJECT
        return super().get_response_serializers()
