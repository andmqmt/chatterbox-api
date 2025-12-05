from app.domain.entities import Conversa, Mensagem, RoleMensagem
from app.domain.repositories import RepositorioConversa
from app.domain.services import ProvedorIA
import uuid


class CriarConversaUseCase:
    def __init__(self, repositorio: RepositorioConversa):
        self.repositorio = repositorio

    async def executar(self) -> Conversa:
        conversa = Conversa(id=str(uuid.uuid4()))
        await self.repositorio.criar(conversa)
        return conversa


class ObtiveConversaUseCase:
    def __init__(self, repositorio: RepositorioConversa):
        self.repositorio = repositorio

    async def executar(self, conversa_id: str) -> Conversa:
        conversa = await self.repositorio.obter_por_id(conversa_id)
        if not conversa:
            raise ValueError(f"Conversa {conversa_id} não encontrada")
        return conversa


class ProcessarMensagemUseCase:
    def __init__(self, repositorio: RepositorioConversa, provedor_ia: ProvedorIA):
        self.repositorio = repositorio
        self.provedor_ia = provedor_ia

    async def executar(self, conversa_id: str, conteudo_usuario: str):
        conversa = await self.repositorio.obter_por_id(conversa_id)
        if not conversa:
            raise ValueError(f"Conversa {conversa_id} não encontrada")

        mensagem_usuario = Mensagem(
            conteudo=conteudo_usuario,
            remetente=RoleMensagem.USUARIO,
            id=str(uuid.uuid4())
        )
        conversa.adicionar_mensagem(mensagem_usuario)

        historico = [
            {"role": m.remetente.value, "content": m.conteudo}
            for m in conversa.mensagens
        ]

        resposta_completa = ""
        async for chunk in self.provedor_ia.gerar_resposta_stream(historico):
            resposta_completa += chunk
            yield chunk

        mensagem_ia = Mensagem(
            conteudo=resposta_completa,
            remetente=RoleMensagem.IA,
            id=str(uuid.uuid4())
        )
        conversa.adicionar_mensagem(mensagem_ia)
        await self.repositorio.atualizar(conversa)


class ListarConversasUseCase:
    def __init__(self, repositorio: RepositorioConversa):
        self.repositorio = repositorio

    async def executar(self) -> list[Conversa]:
        return await self.repositorio.listar_todas()
