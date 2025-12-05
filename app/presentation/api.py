from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
from starlette.websockets import WebSocketDisconnect
import os
import json

from app.infrastructure.persistence.mongo_repository import ConexaoMongoDB, RepositorioConversaMongo
from app.infrastructure.ai.provedor_claude import ProvedorIAClaude
from app.domain.repositories import RepositorioConversa
from app.application.use_cases import (
    CriarConversaUseCase,
    ObtiveConversaUseCase,
    ProcessarMensagemUseCase,
    ListarConversasUseCase
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ConexaoMongoDB.conectar()
    yield
    await ConexaoMongoDB.desconectar()


app = FastAPI(title="ChatterBox API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def obter_repositorio() -> RepositorioConversa:
    db = await ConexaoMongoDB.conectar()
    return RepositorioConversaMongo(db)


class CriarConversaRequest(BaseModel):
    teoria: Optional[str] = ""


@app.get("/")
async def root():
    return {"status": "ok", "message": "ChatterBox API está funcionando"}


@app.get("/health")
async def health_check():
    try:
        db = await ConexaoMongoDB.conectar()
        await db.client.admin.command('ping')
        return {
            "status": "healthy",
            "database": "connected",
            "api": "operational"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "api": "operational",
            "error": str(e)
        }


@app.post("/conversas")
async def criar_conversa(request: CriarConversaRequest = CriarConversaRequest(), repositorio: RepositorioConversa = Depends(obter_repositorio)):
    use_case = CriarConversaUseCase(repositorio)
    teoria = request.teoria if request.teoria else ""
    conversa = await use_case.executar(teoria)
    return conversa.para_dict()


@app.get("/conversas/{conversa_id}")
async def obter_conversa(conversa_id: str, repositorio: RepositorioConversa = Depends(obter_repositorio)):
    use_case = ObtiveConversaUseCase(repositorio)
    try:
        conversa = await use_case.executar(conversa_id)
        return conversa.para_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/conversas")
async def listar_conversas(repositorio: RepositorioConversa = Depends(obter_repositorio)):
    use_case = ListarConversasUseCase(repositorio)
    conversas = await use_case.executar()
    return [c.para_dict() for c in conversas]


@app.websocket("/ws/conversa/{conversa_id}")
async def websocket_endpoint(websocket: WebSocket, conversa_id: str):
    print(f"[WS] Nova conexão WebSocket para conversa: {conversa_id}")
    await websocket.accept()
    print(f"[WS] Conexão aceita para conversa: {conversa_id}")
    
    repositorio = await obter_repositorio()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[WS] ERRO: API key não configurada")
        await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": "API key não configurada"}))
        await websocket.close()
        return

    try:
        provedor_ia = ProvedorIAClaude(api_key)
        print("[WS] Provedor IA inicializado")
    except ValueError as e:
        print(f"[WS] ERRO ao inicializar provedor IA: {e}")
        await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": str(e)}))
        await websocket.close()
        return

    use_case = ProcessarMensagemUseCase(repositorio, provedor_ia)

    try:
        while True:
            try:
                print(f"[WS] Aguardando mensagem na conversa: {conversa_id}")
                dados = await websocket.receive_text()
                print(f"[WS] Mensagem recebida: {dados[:100]}...")
                mensagem_dados = json.loads(dados)
                conteudo_usuario = mensagem_dados.get("mensagem") or mensagem_dados.get("conteudo")
                teoria = mensagem_dados.get("teoria")

                print(f"[WS] Conteúdo: {conteudo_usuario[:50]}... | Teoria: {teoria[:50] if teoria else 'None'}...")

                if not conteudo_usuario:
                    print("[WS] ERRO: Mensagem vazia")
                    await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": "Mensagem vazia"}))
                    continue

                try:
                    print(f"[WS] Iniciando processamento da mensagem...")
                    chunk_count = 0
                    async for chunk in use_case.executar(conversa_id, conteudo_usuario, teoria):
                        chunk_count += 1
                        try:
                            await websocket.send_text(json.dumps({
                                "tipo": "resposta_ia",
                                "conteudo": chunk
                            }))
                        except (WebSocketDisconnect, RuntimeError):
                            print(f"[WS] Cliente desconectado durante envio de chunks")
                            break
                        if chunk_count % 10 == 0:
                            print(f"[WS] Enviados {chunk_count} chunks...")

                    print(f"[WS] Processamento completo. Total de chunks: {chunk_count}")
                    try:
                        await websocket.send_text(json.dumps({"tipo": "fim_resposta"}))
                        print(f"[WS] Sinal de fim enviado")
                    except (WebSocketDisconnect, RuntimeError):
                        print(f"[WS] Cliente desconectado antes de enviar fim")
                except ValueError as e:
                    import traceback
                    print(f"[WS] ERROR ValueError: {e}")
                    print(f"[WS] Traceback: {traceback.format_exc()}")
                    try:
                        await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": str(e)}))
                    except (WebSocketDisconnect, RuntimeError):
                        print(f"[WS] Cliente desconectado durante envio de erro")
                except Exception as e:
                    import traceback
                    print(f"[WS] ERROR Exception: {e}")
                    print(f"[WS] Traceback: {traceback.format_exc()}")
                    try:
                        await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": f"Erro interno: {str(e)}"}))
                    except (WebSocketDisconnect, RuntimeError):
                        print(f"[WS] Cliente desconectado durante envio de erro")
            except WebSocketDisconnect:
                print(f"[WS] Cliente desconectado normalmente da conversa: {conversa_id}")
                break
            except RuntimeError as e:
                if "websocket.close" in str(e).lower() or "after sending" in str(e).lower():
                    print(f"[WS] Conexão já fechada para conversa: {conversa_id}")
                    break
                raise

    except WebSocketDisconnect:
        print(f"[WS] Cliente desconectado da conversa: {conversa_id}")
    except Exception as e:
        import traceback
        if "websocket.close" not in str(e).lower() and "after sending" not in str(e).lower():
            print(f"[WS] ERROR na conexão WebSocket: {e}")
            print(f"[WS] Traceback: {traceback.format_exc()}")
        else:
            print(f"[WS] Conexão fechada para conversa: {conversa_id}")
    finally:
        print(f"[WS] Finalizando conexão WebSocket para conversa: {conversa_id}")
        try:
            await websocket.close()
        except (WebSocketDisconnect, RuntimeError, AttributeError) as e:
            error_msg = str(e).lower()
            if "websocket.close" in error_msg or "after sending" in error_msg or "already closed" in error_msg:
                print(f"[WS] Conexão já estava fechada")
            else:
                print(f"[WS] Erro ao fechar conexão: {type(e).__name__}: {e}")
