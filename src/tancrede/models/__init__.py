"""Model access. Outside this package, use only `ModelRouter` and the types below (R9)."""

from tancrede.models.router import ModelRouter
from tancrede.models.types import ModelGateway, ModelRequest, ModelResponse

__all__ = ["ModelGateway", "ModelRequest", "ModelResponse", "ModelRouter"]
