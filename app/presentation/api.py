from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
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


@app.post("/conversas")
async def criar_conversa(repositorio: RepositorioConversa = Depends(obter_repositorio)):
    use_case = CriarConversaUseCase(repositorio)
    conversa = await use_case.executar()
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
    await websocket.accept()
    
    repositorio = await obter_repositorio()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": "API key não configurada"}))
        await websocket.close()
        return

    try:
        provedor_ia = ProvedorIAClaude(api_key)
    except ValueError as e:
        await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": str(e)}))
        await websocket.close()
        return

    use_case = ProcessarMensagemUseCase(repositorio, provedor_ia)

    try:
        while True:
            dados = await websocket.receive_text()
            mensagem_dados = json.loads(dados)
            conteudo_usuario = mensagem_dados.get("mensagem") or mensagem_dados.get("conteudo")

            if not conteudo_usuario:
                await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": "Mensagem vazia"}))
                continue

            try:
                async for chunk in use_case.executar(conversa_id, conteudo_usuario):
                    await websocket.send_text(json.dumps({
                        "tipo": "resposta_ia",
                        "conteudo": chunk
                    }))

                await websocket.send_text(json.dumps({"tipo": "fim_resposta"}))
            except ValueError as e:
                await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": str(e)}))
            except Exception:
                await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": "Erro interno"}))

    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
