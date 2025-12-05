from app.domain.entities import Conversa, Mensagem, RoleMensagem
from app.domain.repositories import RepositorioConversa
from app.domain.services import ProvedorIA
import uuid


class CriarConversaUseCase:
    def __init__(self, repositorio: RepositorioConversa):
        self.repositorio = repositorio

    async def executar(self, teoria: str = "") -> Conversa:
        conversa = Conversa(id=str(uuid.uuid4()), teoria=teoria)
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

    def _detectar_teoria_na_mensagem(self, mensagem: str) -> str | None:
        import re
        mensagem_original = mensagem.strip()
        mensagem_lower = mensagem_original.lower()
        
        padroes_pergunta = [
            r'^(os|as|o|a)\s+(.+?)\s+(existe|existem|é real|são reais|é verdade|são verdade|são|é)\??$',
            r'^(.+?)\s+(existe|existem|é real|são reais|é verdade|são verdade|são|é)\??$',
            r'(.+?)\s+(existe|existem|é real|são reais|é verdade|são verdade)\??',
        ]
        
        for padrao in padroes_pergunta:
            match = re.search(padrao, mensagem_lower, re.IGNORECASE)
            if match:
                grupos = match.groups()
                teoria_detectada = None
                
                if len(grupos) >= 2:
                    if grupos[0] in ['os', 'as', 'o', 'a']:
                        teoria_detectada = grupos[1]
                    else:
                        teoria_detectada = grupos[0]
                
                if teoria_detectada:
                    teoria_detectada = teoria_detectada.strip()
                    if len(teoria_detectada) > 2 and len(teoria_detectada) < 100:
                        teoria_formatada = teoria_detectada
                        if teoria_formatada:
                            return f"Convencer o usuário que {teoria_formatada} existe/é real."
        
        return None

    async def executar(self, conversa_id: str, conteudo_usuario: str, teoria: str = None):
        print(f"[USE_CASE] Iniciando processamento - Conversa: {conversa_id}, Teoria: {teoria[:50] if teoria else 'None'}...")
        conversa = await self.repositorio.obter_por_id(conversa_id)
        if not conversa:
            print(f"[USE_CASE] ERRO: Conversa {conversa_id} não encontrada")
            raise ValueError(f"Conversa {conversa_id} não encontrada")

        print(f"[USE_CASE] Conversa encontrada. Mensagens existentes: {len(conversa.mensagens)}")

        teoria_detectada = self._detectar_teoria_na_mensagem(conteudo_usuario)
        if teoria_detectada:
            print(f"[USE_CASE] Teoria detectada na mensagem: {teoria_detectada}")
            conversa.teoria = teoria_detectada
            await self.repositorio.atualizar(conversa)
        elif teoria and teoria.strip():
            conversa.teoria = teoria.strip()
            await self.repositorio.atualizar(conversa)
            print(f"[USE_CASE] Teoria atualizada na conversa")

        teoria_ativa = conversa.teoria if conversa.teoria and conversa.teoria.strip() else (teoria.strip() if teoria and teoria.strip() else "Convencer o usuário sobre uma teoria alternativa.")
        print(f"[USE_CASE] Teoria ativa: {teoria_ativa[:100]}...")

        mensagem_usuario = Mensagem(
            conteudo=conteudo_usuario,
            remetente=RoleMensagem.USUARIO,
            id=str(uuid.uuid4())
        )
        conversa.adicionar_mensagem(mensagem_usuario)
        print(f"[USE_CASE] Mensagem do usuário adicionada ao histórico")

        historico = [
            {"role": m.remetente.value, "content": m.conteudo}
            for m in conversa.mensagens
        ]
        print(f"[USE_CASE] Histórico preparado com {len(historico)} mensagens")

        print(f"[USE_CASE] Iniciando geração de resposta da IA...")
        resposta_completa = ""
        chunk_count = 0
        try:
            async for chunk in self.provedor_ia.gerar_resposta_stream(historico, teoria_ativa):
                resposta_completa += chunk
                chunk_count += 1
                yield chunk
            print(f"[USE_CASE] Resposta completa gerada. Total de chunks: {chunk_count}, Tamanho: {len(resposta_completa)} caracteres")
        except Exception as e:
            import traceback
            print(f"[USE_CASE] ERRO ao gerar resposta: {e}")
            print(f"[USE_CASE] Traceback: {traceback.format_exc()}")
            raise

        mensagem_ia = Mensagem(
            conteudo=resposta_completa,
            remetente=RoleMensagem.IA,
            id=str(uuid.uuid4())
        )
        conversa.adicionar_mensagem(mensagem_ia)
        await self.repositorio.atualizar(conversa)
        print(f"[USE_CASE] Mensagem da IA salva no banco de dados")


class ListarConversasUseCase:
    def __init__(self, repositorio: RepositorioConversa):
        self.repositorio = repositorio

    async def executar(self) -> list[Conversa]:
        return await self.repositorio.listar_todas()
