# ChatterBox API

API REST para gerenciar conversas com integração de IA usando FastAPI, MongoDB e Claude API.

## Requisitos

- Python 3.11 ou superior
- MongoDB (local ou remoto)
- Chave de API da Anthropic (Claude)

## Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd chatterbox-api
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Configuração

Crie um arquivo `.env` na raiz do projeto:

```env
ANTHROPIC_API_KEY=sua_chave_api_aqui
MONGODB_URL=mongodb://localhost:27017
```

**Variáveis de ambiente:**
- `ANTHROPIC_API_KEY`: Chave de API da Anthropic (obrigatória)
- `MONGODB_URL`: URL de conexão do MongoDB (padrão: `mongodb://localhost:27017`)

## Execução

Execute o servidor:

```bash
python main.py
```

A API estará disponível em `http://localhost:8000`

Documentação interativa (Swagger): `http://localhost:8000/docs`

## Endpoints

### REST

- `POST /conversas` - Criar nova conversa
- `GET /conversas/{conversa_id}` - Obter conversa por ID
- `GET /conversas` - Listar todas as conversas

### WebSocket

- `WS /ws/conversa/{conversa_id}` - Conectar e processar mensagens em tempo real

## Estrutura do Projeto

```
chatterbox-api/
├── app/
│   ├── domain/           # Entidades e interfaces
│   ├── application/      # Casos de uso
│   ├── infrastructure/   # Implementações (MongoDB, Claude)
│   └── presentation/     # API e WebSocket (FastAPI)
├── main.py
├── requirements.txt
└── .env
```

## Tecnologias

- FastAPI
- MongoDB (Motor)
- Anthropic Claude API
- WebSockets
- Python-dotenv

