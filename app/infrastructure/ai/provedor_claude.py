from app.domain.services import ProvedorIA
from typing import AsyncGenerator
import httpx
import asyncio
import os


class ProvedorIAClaude(ProvedorIA):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key não configurada. Configure ANTHROPIC_API_KEY no arquivo .env")
        self.api_key = api_key

    async def gerar_resposta_stream(self, mensagens: list[dict], teoria: str = "") -> AsyncGenerator[str, None]:
        """Faz chamada direta à API REST da Anthropic usando endpoint /v1/messages.

        Retorna a resposta em pequenos pedaços (chunks) para simular streaming.
        """
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        
        if not teoria or not teoria.strip():
            objetivo = "Convencer o usuário sobre uma teoria alternativa."
        else:
            objetivo = teoria.strip()
        
        print(f"[DEBUG] Teoria recebida: {objetivo}")
        
        formatted_messages = []
        primeiro_user = True
        for m in mensagens:
            role = m.get("role") or m.get("remetente") or "user"
            content = m.get("content") or m.get("conteudo") or m.get("mensagem") or ""
            if role.lower().startswith("user") or role.lower().startswith("usuario"):
                if primeiro_user:
                    content = f"[LEMBRE-SE: Você está defendendo APENAS: {objetivo}. NÃO mencione outras teorias.]\n\n{content}"
                    primeiro_user = False
                formatted_messages.append({"role": "user", "content": content})
            else:
                formatted_messages.append({"role": "assistant", "content": content})
        
        system_prompt = f"""🚨 INSTRUÇÃO CRÍTICA: Você está defendendo APENAS esta teoria: {objetivo}

Você é um defensor apaixonado e convicto desta teoria/crença. Esta é sua única verdade e missão. Você acredita profundamente nesta teoria e está comprometido em defendê-la com todas as suas forças.

⚠️ PROIBIÇÃO ABSOLUTA: Você NUNCA pode mencionar, discutir, comparar, usar como exemplo ou fazer referência a QUALQUER outra teoria que não seja: {objetivo}

REGRAS FUNDAMENTAIS (SEGUIR SEMPRE):

1. Você DEVE defender APENAS e EXCLUSIVAMENTE: {objetivo}
2. Você NUNCA deve mencionar, discutir, comparar ou fazer referência a QUALQUER outra teoria
3. Se o usuário mencionar outras teorias, você DEVE ignorar completamente e redirecionar para: {objetivo}
4. Você NUNCA deve usar outras teorias como exemplo, analogia ou comparação
5. Você NUNCA deve mudar de assunto ou desviar do tema: {objetivo}
6. Se você pensar em mencionar qualquer teoria que não seja {objetivo}, RESISTA IMEDIATAMENTE e fale APENAS sobre {objetivo}
7. Se você sentir qualquer impulso de mencionar formato da Terra, curvatura, esfera, ou qualquer outra teoria: PARE e fale APENAS sobre {objetivo}

COMPORTAMENTO OBRIGATÓRIO:

- Quando o usuário perguntar sobre sua teoria: Defenda {objetivo} com paixão, convicção e entusiasmo. NÃO mencione outras teorias.
- Quando o usuário mencionar outras teorias: Ignore completamente e diga "Não vou me distrair com outras teorias. Vamos focar em {objetivo}"
- Quando o usuário apresentar evidências contrárias: Refute usando argumentos criativos que suportem {objetivo}. NÃO mencione outras teorias.
- Quando você sentir vontade de mencionar outra teoria: NÃO FAÇA. Foque APENAS em {objetivo}
- Se você pensar em Terra plana, formato da Terra, ou qualquer outra teoria: PARE IMEDIATAMENTE. Sua única teoria é: {objetivo}

ESTRATÉGIA DE ARGUMENTAÇÃO:

Para defender {objetivo}, você pode:
- Apresentar evidências anedóticas, históricas ou alternativas
- Questionar autoridades científicas ou governamentais que contradigam sua teoria
- Usar lógica aparente que pareça suportar sua teoria
- Mencionar conspirações quando apropriado
- Criar explicações alternativas para fenômenos observados
- Usar perguntas retóricas para fazer o usuário questionar o senso comum

QUANDO CONFRONTADO COM EVIDÊNCIAS CONTRÁRIAS:

- Evidências científicas: "São fabricadas, manipuladas ou interpretadas incorretamente"
- Lógica contrária: "Há fatores ocultos que a lógica convencional não considera"
- Autoridade: "As autoridades têm interesse em esconder a verdade"
- Experiência pessoal: "Minha experiência confirma {objetivo}"
- Conspiração: "Há uma conspiração para manter a verdade oculta"
- Dados faltantes: "A ciência ainda não tem todas as respostas, mas {objetivo} explica"

TOM E ESTILO:

- Conversacional e natural em português brasileiro
- Entusiasmado mas não agressivo
- Persuasivo e convincente
- Use perguntas retóricas sobre {objetivo}
- Apresente "fatos" como se fossem verdades estabelecidas

LEMBRE-SE:

Sua única missão é defender: {objetivo}
Você NÃO está defendendo nenhuma outra teoria
Se você mencionar qualquer outra teoria, você FALHOU
Foque 100% em: {objetivo}

Este é um exercício de argumentação persuasiva. Você deve defender {objetivo} com convicção total, como se fosse sua verdade inquestionável. Nunca quebre o personagem."""
        
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2048,
            "system": system_prompt,
            "messages": formatted_messages,
        }

        print(f"[CLAUDE] Enviando requisição para API Anthropic...")
        print(f"[CLAUDE] Payload: {len(formatted_messages)} mensagens, teoria: {objetivo[:50]}...")
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                print(f"[CLAUDE] Fazendo POST para {url}...")
                resp = await client.post(url, json=payload, headers=headers)
                print(f"[CLAUDE] Resposta recebida: status {resp.status_code}")
                
                if resp.status_code != 200:
                    error_text = resp.text
                    print(f"[CLAUDE] ERRO: status {resp.status_code} - {error_text[:200]}...")
                    raise ValueError(f"Erro Claude API: status {resp.status_code} - {error_text}")
                
                print(f"[CLAUDE] Parseando JSON da resposta...")
                j = resp.json()
                
                text = ""
                if isinstance(j, dict) and "content" in j:
                    content_list = j.get("content", [])
                    if isinstance(content_list, list):
                        for item in content_list:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text += item.get("text", "")
                
                print(f"[CLAUDE] Texto extraído: {len(text)} caracteres")
                
                if not text:
                    print(f"[CLAUDE] ERRO: Resposta vazia da API")
                    raise ValueError(f"Resposta vazia da API Anthropic")

                print(f"[CLAUDE] Iniciando streaming de chunks...")
                chunk_size = 50
                chunk_count = 0
                for i in range(0, len(text), chunk_size):
                    chunk = text[i:i+chunk_size]
                    yield chunk
                    chunk_count += 1
                    if chunk_count % 20 == 0:
                        print(f"[CLAUDE] Enviados {chunk_count} chunks...")
                    await asyncio.sleep(0.005)
                
                print(f"[CLAUDE] Streaming completo. Total: {chunk_count} chunks")

        except httpx.HTTPStatusError as e:
            print(f"[CLAUDE] ERRO HTTPStatusError: {e}")
            raise ValueError(f"Erro Claude API: status {e.response.status_code}")
        except Exception as e:
            import traceback
            print(f"[CLAUDE] ERRO Exception: {e}")
            print(f"[CLAUDE] Traceback: {traceback.format_exc()}")
            raise ValueError(f"Erro Claude API: {str(e)}")
