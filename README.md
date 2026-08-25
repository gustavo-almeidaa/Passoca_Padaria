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
RF02), **Incremento 3 concluído** (registro de pedido — RF03, RF04 — com
RN01 aplicada no backend), **Incremento 4 concluído** (ciclo de vida do
pedido — RF06 cancelar, RF07 listar por período, com RN02, RN03 e RN04
aplicadas no backend), **Incremento 5 concluído** (frontend — infraestrutura
mínima e tela de cadastro de cliente, RF01), **Incremento 6 concluído**
(frontend — tela de cadastro de produto, RF02), **Incremento 7 concluído**
(frontend — tela de novo pedido, RF03/RF04, com RN01 replicada no
frontend), **Incremento 8 concluído** (frontend — tela de Pedidos, RF05 e
RF07, com confirmar sinal/RN02, avançar status/RN04 e cancelar/RF06+RN03)
**Incremento 9 concluído** (frontend — as 4 telas unificadas em uma
única página, trocando de seção via JS sem recarregar, com sincronização
entre abas) e **Incremento 10 concluído** (RF01 ganha campo de endereço
opcional — texto livre — no cadastro de cliente, com migration). RF01-RF07
do levantamento original estão completos tanto no backend quanto no
frontend.

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
│   │   ├── services/     # regras de negócio — RN01-RN04 aplicadas no backend
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
├── frontend/
│   ├── index.html         # página única — 4 seções (Clientes, Produtos,
│   │                       # Novo Pedido, Pedidos) trocadas via JS, sem reload
│   ├── css/style.css      # estilo compartilhado entre as seções
│   └── js/                # api.js (cliente HTTP), ui.js (feedback visual),
│                           # app.js (controlador de abas), cadastro-cliente.js,
│                           # cadastro-produto.js, novo-pedido.js, lista-pedidos.js
├── docs/referencia-prototipo/  # protótipo HTML original, só como referência de UX
└── CLAUDE.md
```

O frontend é servido pelo próprio backend (`StaticFiles` montado em `/` no
FastAPI — ver `backend/app/main.py`) — não precisa de um segundo servidor
nem de configurar CORS. `uvicorn app.main:app` sobe a API e a UI juntos.

## Rodando localmente

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements-dev.txt

cp .env.example .env               # ajuste se necessário

alembic upgrade head               # cria o banco SQLite (app.db) com o schema atual

pytest -v                          # roda a suite de testes

uvicorn app.main:app --reload      # sobe a API + frontend em http://127.0.0.1:8000
```

Isso cria o schema completo (`clientes`, `produtos`, `pedidos`,
`itens_pedido`) no arquivo `backend/app.db` (ignorado pelo git) e roda os
79 testes automatizados (schema + API + service de pedidos). Com o servidor
no ar: o sistema fica em `http://127.0.0.1:8000/`, com as 4 telas
(Clientes, Produtos, Novo Pedido, Pedidos) acessíveis pela navegação no
topo — trocar de aba não recarrega a página — e a documentação interativa
(Swagger) em `http://127.0.0.1:8000/docs`.

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
| `GET` | `/pedidos?data_inicio=&data_fim=` | Listar pedidos por período/dia (RF07) |
| `GET` | `/pedidos/{id}` | Consultar um pedido, com seus itens (RF05) |
| `POST` | `/pedidos/{id}/confirmar-sinal` | Confirma o sinal de um pedido (suporte a RN02) |
| `POST` | `/pedidos/{id}/avancar` | Avança para a próxima etapa de produção — aplica RN02 e RN04 |
| `POST` | `/pedidos/{id}/cancelar` | Cancela o pedido (RF06) — aplica RN03 e RN04 |

## Regras de negócio principais

| ID | Regra |
|---|---|
| RN01 | Pedido precisa ter entrega com pelo menos 24h de antecedência |
| RN02 | Item personalizável exige sinal confirmado antes de sair de "recebido" |
| RN03 | Cancelamento só é permitido até 12h antes da entrega |
| RN04 | Status segue máquina de estados estrita: recebido → em_producao → pronto → entregue |

Detalhes completos em [`CLAUDE.md`](./CLAUDE.md).
