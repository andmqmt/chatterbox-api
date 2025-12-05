from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.domain.entities import Conversa, Mensagem, RoleMensagem
from app.domain.repositories import RepositorioConversa
from typing import Optional
from datetime import datetime
import os


class ConexaoMongoDB:
    _instancia: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def conectar(cls) -> AsyncIOMotorDatabase:
        if cls._instancia is None:
            url_conexao = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
            cliente = AsyncIOMotorClient(url_conexao)
            cls._instancia = cliente["chatterbox"]
        return cls._instancia

    @classmethod
    async def desconectar(cls) -> None:
        if cls._instancia is not None:
            cls._instancia.client.close()
            cls._instancia = None


class RepositorioConversaMongo(RepositorioConversa):
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.colecao = db["conversas"]

    async def criar(self, conversa: Conversa) -> None:
        documento = {
            "_id": conversa.id,
            "mensagens": [],
            "teoria": conversa.teoria,
            "criada_em": conversa.criada_em,
            "atualizada_em": conversa.atualizada_em
        }
        await self.colecao.insert_one(documento)

    async def obter_por_id(self, id: str) -> Optional[Conversa]:
        documento = await self.colecao.find_one({"_id": id})
        if not documento:
            return None
        return self._mapear_para_entidade(documento)

    async def atualizar(self, conversa: Conversa) -> None:
        documento = {
            "mensagens": [self._serializar_mensagem(m) for m in conversa.mensagens],
            "atualizada_em": conversa.atualizada_em
        }
        await self.colecao.update_one({"_id": conversa.id}, {"$set": documento})

    async def listar_todas(self) -> list[Conversa]:
        cursor = self.colecao.find()
        documentos = await cursor.to_list(None)
        return [self._mapear_para_entidade(doc) for doc in documentos]

    def _mapear_para_entidade(self, documento: dict) -> Conversa:
        mensagens = [
            Mensagem(
                id=msg["id"],
                conteudo=msg["conteudo"],
                remetente=RoleMensagem(msg["remetente"]),
                timestamp=msg["timestamp"]
            )
            for msg in documento.get("mensagens", [])
        ]
        return Conversa(
            id=documento["_id"],
            mensagens=mensagens,
            teoria=documento.get("teoria", ""),
            criada_em=documento["criada_em"],
            atualizada_em=documento["atualizada_em"]
        )

    def _serializar_mensagem(self, mensagem: Mensagem) -> dict:
        return {
            "id": mensagem.id,
            "conteudo": mensagem.conteudo,
            "remetente": mensagem.remetente.value,
            "timestamp": mensagem.timestamp
        }
