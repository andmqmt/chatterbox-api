from abc import ABC, abstractmethod
from typing import AsyncGenerator


class ProvedorIA(ABC):

    @abstractmethod
    async def gerar_resposta_stream(self, mensagens: list[dict]) -> AsyncGenerator[str, None]:
        pass
