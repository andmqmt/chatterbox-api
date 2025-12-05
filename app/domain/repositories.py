from abc import ABC, abstractmethod
from typing import Optional
from app.domain.entities import Conversa


class RepositorioConversa(ABC):

    @abstractmethod
    async def criar(self, conversa: Conversa) -> None:
        pass

    @abstractmethod
    async def obter_por_id(self, id: str) -> Optional[Conversa]:
        pass

    @abstractmethod
    async def atualizar(self, conversa: Conversa) -> None:
        pass

    @abstractmethod
    async def listar_todas(self) -> list[Conversa]:
        pass
