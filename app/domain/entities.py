from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from enum import Enum


class RoleMensagem(str, Enum):
    USUARIO = "usuario"
    IA = "ia"


@dataclass
class Mensagem:
    conteudo: str
    remetente: RoleMensagem
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = ""

    def para_dict(self) -> dict:
        return {
            "id": self.id,
            "conteudo": self.conteudo,
            "remetente": self.remetente.value,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Conversa:
    id: str
    mensagens: List[Mensagem] = field(default_factory=list)
    teoria: str = ""
    criada_em: datetime = field(default_factory=datetime.now)
    atualizada_em: datetime = field(default_factory=datetime.now)

    def adicionar_mensagem(self, mensagem: Mensagem) -> None:
        self.mensagens.append(mensagem)
        self.atualizada_em = datetime.now()

    def para_dict(self) -> dict:
        return {
            "id": self.id,
            "mensagens": [m.para_dict() for m in self.mensagens],
            "teoria": self.teoria,
            "criada_em": self.criada_em.isoformat(),
            "atualizada_em": self.atualizada_em.isoformat()
        }
