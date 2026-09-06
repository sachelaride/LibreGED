from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T] = Field(description="Lista de itens desta página")
    total: int = Field(description="Total de itens que correspondem à busca")
    page: int = Field(description="Página atual")
    size: int = Field(description="Tamanho da página")
    pages: int = Field(description="Total de páginas disponíveis")
