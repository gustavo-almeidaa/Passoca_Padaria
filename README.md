# Passoca_Padaria

Sistema de encomendas para a **Padaria do Passoca** — substitui o controle
manual (caderno / WhatsApp) por um sistema simples de cadastro de clientes,
produtos e pedidos, com rastreabilidade de status do recebimento até a
entrega.

> Contexto completo de requisitos, regras de negócio e decisões de
> arquitetura em [`CLAUDE.md`](./CLAUDE.md).

## Stack

- **Backend:** Python + FastAPI
- **Banco de dados:** SQLite (via SQLAlchemy + Alembic)
- **Frontend:** HTML/JS simples (sem framework)
- **Testes:** pytest

## Status do projeto

🚧 Em desenvolvimento — **Incremento 1 concluído** (schema + migrations +
testes), **Incremento 2 concluído** (API REST de Cliente e Produto — RF01,
RF02) e **Incremento 3 concluído** (registro de pedido — RF03, RF04 — com
RN01 aplicada no backend). RF05 completo (listagem), RF06 (cancelar, RN03),
RF07 (listar por período) e RN02/RN04 (sinal e máquina de estados) ainda não
existem — isso é o Incremento 4.

Autenticação/login por perfil está deliberadamente fora do MVP (ver backlog
no `CLAUDE.md`, seção 5 e 13). O sistema roda hoje sem autenticação, para
uso na rede interna da padaria.

O banco de dados de desenvolvimento é SQLite. Uma migração manual para
PostgreSQL está prevista para o futuro, mas não faz parte do escopo atual
(ver `CLAUDE.md`, seção 11).

## Estrutura do repositório

```
Passoca_Padaria/
├── backend/
│   ├── app/
│   │   ├── models/       # modelos SQLAlchemy (Cliente, Produto, Pedido, ItemPedido)
│   │   ├── schemas/      # schemas Pydantic — Cliente, Produto e Pedido
│   │   ├── services/     # regras de negócio — RN01 (Incremento 3); RN02-RN04 no Incremento 4
│   │   ├── api/          # rotas FastAPI — /clientes, /produtos e /pedidos
│   │   ├── main.py       # ponto de entrada da API (app FastAPI)
│   │   └── core/         # config (settings) e conexão com banco
│   ├── migrations/       # Alembic — histórico de mudanças de schema
│   ├── tests/            # pytest
│   ├── .env.example      # modelo de variáveis de ambiente
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/              # ainda vazio — Fase 3
├── docs/referencia-prototipo/  # protótipo HTML original, só como referência de UX
└── CLAUDE.md
```

## Rodando localmente

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements-dev.txt

cp .env.example .env               # ajuste se necessário

alembic upgrade head               # cria o banco SQLite (app.db) com o schema atual

pytest -v                          # roda a suite de testes

uvicorn app.main:app --reload      # sobe a API em http://127.0.0.1:8000
```

Isso cria o schema completo (`clientes`, `produtos`, `pedidos`,
`itens_pedido`) no arquivo `backend/app.db` (ignorado pelo git) e roda os
44 testes automatizados (schema + API + service de pedidos). Com a API no
ar, a documentação interativa (Swagger) fica disponível em
`http://127.0.0.1:8000/docs`.

## Endpoints disponíveis

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Verificação de saúde da API |
| `POST` | `/clientes` | Cadastrar cliente (RF01) |
| `GET` | `/clientes` | Listar clientes |
| `GET` | `/clientes/{id}` | Consultar um cliente |
| `POST` | `/produtos` | Cadastrar produto (RF02) |
| `GET` | `/produtos?ativo=true` | Listar produtos (filtro opcional por ativo) |
| `GET` | `/produtos/{id}` | Consultar um produto |
| `POST` | `/pedidos` | Registrar pedido (RF03, RF04) — aplica RN01 |
| `GET` | `/pedidos/{id}` | Consultar um pedido, com seus itens |

## Regras de negócio principais

| ID | Regra |
|---|---|
| RN01 | Pedido precisa ter entrega com pelo menos 24h de antecedência |
| RN02 | Item personalizável exige sinal confirmado antes de sair de "recebido" |
| RN03 | Cancelamento só é permitido até 12h antes da entrega |
| RN04 | Status segue máquina de estados estrita: recebido → em_producao → pronto → entregue |

Detalhes completos em [`CLAUDE.md`](./CLAUDE.md).
