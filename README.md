# Passoca_Padaria

[![CI](https://github.com/gustavo-almeidaa/Passoca_Padaria/actions/workflows/ci.yml/badge.svg)](https://github.com/gustavo-almeidaa/Passoca_Padaria/actions/workflows/ci.yml)

Sistema de encomendas para a **Padaria do Passoca** — substitui o controle
manual (caderno / WhatsApp) por um sistema simples de cadastro de clientes,
produtos e pedidos, com rastreabilidade de status do recebimento até a
entrega.

> Contexto completo de requisitos, regras de negócio e decisões de
> arquitetura em [`CLAUDE.md`](./CLAUDE.md).

## Stack

- **Backend:** Python + FastAPI
- **Banco de dados:** PostgreSQL gerenciado ([Neon](https://neon.tech)), via SQLAlchemy + Alembic
- **Frontend:** HTML/JS simples (sem framework)
- **Testes:** pytest — SQLite em memória no dia a dia; o CI roda a mesma suíte também contra PostgreSQL (Incremento 21)

## Status do projeto

🚧 Em desenvolvimento. **Incrementos 1-11 concluídos**: schema/migrations,
API REST completa de Cliente/Produto/Pedido (RF01-RF07, RN01-RN05
aplicadas no backend), frontend unificado numa página só, endereço
opcional no cliente, e banco migrado de SQLite para PostgreSQL gerenciado
via Neon (resolve RNF03, backup). RF01-RF07 do levantamento original estão
completos tanto no backend quanto no frontend.

Incrementos recentes:
- **12 — Autenticação:** login obrigatório por sessão em todas as rotas.
- **13 — Deploy:** sistema publicado no Render (plano free).
- **14 — Trocar senha:** usuário logado troca a própria senha.
- **15 — Ajustes de uso real** (2026-08-25): máscaras de telefone/preço,
  editar produto já cadastrado, limites realistas (RN05 — preço até
  R$ 999,99, quantidade até 999, entrega até 90 dias de antecedência),
  filtro padrão da aba Pedidos mostrando a semana a partir de hoje, e
  restrição da aba Usuários (criar/excluir/trocar senha) só pra
  proprietária — "excluir" foi implementado como desativar
  (`ativo=false`), não apagar de vez; ver `CLAUDE.md`, seção 5, pra o
  motivo dessa escolha.
- **16 — CI e ferramental de qualidade** (2026-08-27): executa o plano de
  ação da auditoria de software (ver `CLAUDE.md`, seção 2). GitHub Actions
  roda `pytest` + `ruff` + `bandit` + `pip-audit` a cada push/PR (A-05);
  `ruff`/`bandit` configurados em `backend/pyproject.toml` (A-08); tags
  `incremento-01..15` criadas retroativamente (A-06).
- **16.1 — Bump de dependências vulneráveis** (2026-08-27): `fastapi` para
  0.121.3 + `starlette` para 0.49.3, corrigindo o ReDoS no parsing do
  header `Range` do `StaticFiles` (PYSEC-2026-1942) e mais um CVE. Os 7
  CVEs restantes da baseline não têm correção publicada e/ou não são
  alcançáveis no código — justificativa individual em
  `.github/workflows/ci.yml`.
- **17 — Limite de tentativas no login** (2026-08-27, auditoria A-02):
  tabela `tentativas_login`; falhas contadas **por IP** numa janela de
  15 min — de 5 a 9 aplicam atraso progressivo, 10+ retornam `429` sem
  checar a senha. A conta nunca trava, só o IP (assim um ataque remoto não
  tranca a proprietária para fora). Lógica em `app/services/rate_limit.py`.
- **18 — Trilha de auditoria** (2026-08-27, auditoria A-01): tabela
  `eventos_auditoria` (só escrita) registra quem fez, quando, e o estado
  antes/depois de toda operação sensível — pedido (criar/avançar/confirmar
  sinal/cancelar), produto (criar/editar), usuário (criar/desativar/trocar
  senha, sem o valor). Gravada no mesmo commit da operação. Consulta em
  `GET /auditoria` (só proprietária). A tela fica pro Incremento 18.1.
- **19 — Matriz de permissão por perfil** (2026-08-27, auditoria A-03):
  aplicada rota a rota no backend (`api/deps.py::exigir_perfis`). Padeiro
  = leitura + avançar status de produção, nada mais. Atendente = tudo de
  balcão (cliente, produto inclusive editar, pedido inclusive cancelar).
  Proprietária = tudo. O gate no frontend (esconder botões) fica pro
  Incremento 20.
- **20 — Frontend da auditoria e da permissão** (2026-08-27): aba
  **Auditoria** (só proprietária) lê `GET /auditoria` com filtro por
  tipo/período; o `auth.js` esconde do padeiro a aba "Novo Pedido" e os
  formulários de cadastro, e o `lista-pedidos.js` esconde dele os botões
  "Confirmar sinal"/"Cancelar". Fecha 18.1 e 19.1.
- **21 — Paridade de teste com PostgreSQL** (2026-08-27, auditoria A-04):
  a suíte roda contra `TEST_DATABASE_URL` quando setada (Postgres no CI),
  senão SQLite. Dois jobs de CI bloqueantes: a suíte inteira contra
  `postgres:16` e o round-trip das migrations no Postgres.
- **22 — Medição de desempenho** (2026-08-27, auditoria A-07): header
  `X-Response-Time` em toda resposta + log de requisição lenta (>500ms);
  script de carga `backend/loadtest/carga.py`; baseline em
  `docs/desempenho.md` (p95 dos endpoints ~164ms local). Corrigido N+1 em
  `GET /pedidos`. Recomendação: plano Starter do Render antes de uso
  comercial (o free "dorme").
- **23 — Editar pedido** (2026-08-27): `PUT /pedidos/{id}` edita itens e/ou
  data de entrega de um pedido ainda em `recebido` (não muda o cliente).
  Revalida RN01/RN05 na nova data; reseta o sinal se a composição de itens
  personalizáveis mudar; itens antigos mantêm o preço travado.
- **23.1 — Frontend da edição** (2026-08-27): botão "Editar" no ticket
  (só `recebido`, só proprietária/atendente) abre um painel inline com
  data/hora + itens. Um item que já estava no pedido segue válido mesmo
  se o produto saiu de linha depois.
- **24 — Histórico de pedidos por cliente** (2026-08-28):
  `GET /clientes/{id}/pedidos` lista todos os pedidos do cliente (inclusive
  cancelados), do mais recente pro mais antigo. Na aba Clientes, o botão
  "pedidos" em cada cliente abre um painel com o histórico + resumo
  (nº de pedidos e total já encomendado, só os não cancelados).

O sistema passou a depender de internet, já que o banco agora é gerenciado
na nuvem (decisão registrada: funcionar offline não é requisito do MVP).

## Estrutura do repositório

```
Passoca_Padaria/
├── backend/
│   ├── app/
│   │   ├── models/       # modelos SQLAlchemy (Cliente, Produto, Pedido, ItemPedido,
│   │   │                 # Usuario, TentativaLogin, EventoAuditoria)
│   │   ├── schemas/      # schemas Pydantic — Cliente, Produto, Pedido, Usuario, Auditoria
│   │   ├── services/     # regras de negócio — RN01-RN05, rate_limit (A-02), auditoria (A-01)
│   │   ├── api/          # rotas FastAPI — /clientes, /produtos, /pedidos, /auth, /auditoria
│   │   │                 # + deps.py (autenticação + IP do cliente)
│   │   ├── main.py       # ponto de entrada da API (app FastAPI)
│   │   └── core/         # config (settings), conexão com banco e security.py (hash de senha)
│   ├── migrations/       # Alembic — histórico de mudanças de schema
│   ├── tests/            # pytest
│   ├── loadtest/         # carga.py — teste de carga do balcão (A-07)
│   ├── .env.example      # modelo de variáveis de ambiente
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── index.html         # página única — tela de login + 6 seções (Clientes,
│   │                       # Produtos, Novo Pedido, Pedidos, Usuários, Auditoria)
│   │                       # trocadas via JS, sem reload
│   ├── css/style.css      # estilo compartilhado entre as seções
│   └── js/                # api.js (cliente HTTP), ui.js (feedback visual),
│                           # app.js (controlador de abas), auth.js (login/logout
│                           # + gate de permissão por perfil), cadastro-cliente.js,
│                           # cadastro-produto.js, novo-pedido.js, lista-pedidos.js,
│                           # usuarios.js, auditoria.js
├── docs/
│   ├── desempenho.md            # medição de desempenho + recomendação de plano (A-07)
│   └── referencia-prototipo/    # protótipo HTML original, só como referência de UX
└── CLAUDE.md
```

O frontend é servido pelo próprio backend (`StaticFiles` montado em `/` no
FastAPI — ver `backend/app/main.py`) — não precisa de um segundo servidor
nem de configurar CORS. `uvicorn app.main:app` sobe a API e a UI juntos.

## Configurando o banco (Neon)

O projeto usa [Neon](https://neon.tech) (PostgreSQL gerenciado, free tier)
como banco. Criar a conta/projeto é uma ação de conta pessoal — cada
desenvolvedor faz a sua:

1. Crie uma conta em [neon.tech](https://neon.tech) (dá pra entrar com
   GitHub/Google).
2. Crie um projeto novo (ex.: `passoca-padaria`) — o Neon já cria um banco
   padrão dentro dele.
3. No dashboard do projeto, copie a **Connection string**.
4. Em `backend/`, rode `cp .env.example .env` (Windows: `copy .env.example .env`)
   e cole a connection string na linha `DATABASE_URL`, trocando o prefixo
   `postgresql://` por `postgresql+psycopg://` (driver usado neste
   projeto) — mantenha o `?sslmode=require` no final.
5. `.env` nunca é commitado (já está no `.gitignore`) — a connection string
   tem senha, não compartilhe fora do seu ambiente local.

## Configurando a autenticação (Incremento 12)

O sistema exige login em todas as rotas de negócio. Além de `DATABASE_URL`,
o `backend/.env` precisa de:

| Variável | Para quê |
|---|---|
| `SESSION_SECRET_KEY` | Assina o cookie de sessão. Gere uma própria — nunca reaproveite a de outro ambiente: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_NOME`, `ADMIN_EMAIL`, `ADMIN_SENHA` | Criam a conta da proprietária automaticamente no primeiro boot, **só se o banco ainda não tiver nenhum usuário**. Troque a senha depois de logar pela primeira vez, pela aba "Usuários" → "Trocar Minha Senha" (Incremento 14). |

Sem `ADMIN_EMAIL`/`ADMIN_SENHA` configurados, o servidor sobe normalmente,
mas ninguém consegue logar (fica um aviso no log). Usuários adicionais
(atendente, padeiro) são criados pela aba "Usuários" do próprio sistema,
já logado.

`ENVIRONMENT=production` (setar no Render, não localmente) ativa validações
extras — o servidor recusa subir se `SESSION_SECRET_KEY` ainda for o valor
de desenvolvimento.

## Rodando localmente

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements-dev.txt

# configure o backend/.env: DATABASE_URL (Neon, passo acima) +
# SESSION_SECRET_KEY + ADMIN_EMAIL/ADMIN_SENHA (passo acima)

alembic upgrade head               # cria o schema no banco do Neon

pytest -v                          # roda a suite de testes (SQLite isolado, não usa o Neon)

uvicorn app.main:app --reload      # sobe a API + frontend em http://127.0.0.1:8000
```

Isso cria o schema completo (`clientes`, `produtos`, `pedidos`,
`itens_pedido`, `usuarios`, `tentativas_login`, `eventos_auditoria`) no
banco Postgres do Neon e roda os 210 testes automatizados (schema + API +
services + autenticação + limite de tentativas + trilha de auditoria +
matriz de permissão + desempenho + edição de pedido + histórico por
cliente — cada teste usa um SQLite em memória isolado, não toca no Neon).
No primeiro
boot, se `ADMIN_EMAIL`/`ADMIN_SENHA` estiverem configurados e o banco não
tiver nenhum usuário, a conta da proprietária é criada automaticamente.
Com o servidor no ar: o sistema fica em `http://127.0.0.1:8000/` — pede
login antes de mostrar qualquer tela — e a documentação interativa
(Swagger) em `http://127.0.0.1:8000/docs`.

## Qualidade e CI (Incremento 16)

O CI (`.github/workflows/ci.yml`) roda a cada push/PR na `main`, em Python
3.12.7 (mesma versão do Render):

| Job | O que checa |
|---|---|
| `pytest -q` | Suíte de testes contra **SQLite** em memória (rápido) |
| `pytest` contra **PostgreSQL** | mesma suíte, banco `postgres:16` (Incremento 21 — `CHECK`, `Numeric`, transações como em produção) |
| migrations no PostgreSQL | `upgrade head → downgrade base → upgrade head` — prova que a cadeia sobe/desce no banco real |
| `ruff check .` | Lint e ordenação de import — config em `backend/pyproject.toml` |
| `bandit -c pyproject.toml -r app` | Varredura de segurança do código da aplicação |
| `pip-audit -r requirements.txt` | CVE conhecido nas dependências de produção |

Todos os jobs **bloqueiam o merge**.

Rodar o essencial localmente (de dentro de `backend/`, com o venv ativo):

```bash
pytest -q && ruff check . && bandit -c pyproject.toml -r app && pip-audit -r requirements.txt
```

Pra rodar a suíte contra um PostgreSQL local (opcional — o CI já faz):
`TEST_DATABASE_URL="postgresql+psycopg://user:senha@localhost:5432/db" pytest -q`.

> **Windows:** o `pip-audit` quebra com `UnicodeDecodeError` quando o
> caminho do projeto tem acento (bug do `pip-api` ao ler a saída do
> `pip`). Contorne com `PYTHONUTF8=1 pip-audit -r requirements.txt`. No CI
> (Linux) não acontece.

Hook opcional pra rodar o `ruff` antes de cada commit:
`pip install pre-commit && pre-commit install` (config em
`.pre-commit-config.yaml`).

**Nota:** o CI **não** bloqueia o deploy do Render — `autoDeploy` continua
ligado. O gate de deploy fica pra um incremento futuro (ver `CLAUDE.md`,
seção 11).

## Deploy (Render)

O `render.yaml` na raiz do repositório já descreve o serviço (plano free,
comando de build/start, `rootDir: backend`) — o Render lê esse arquivo
automaticamente ao criar um Blueprint, então a maior parte da configuração
não precisa ser preenchida manualmente no painel. Passos (ação de conta,
cada um faz a sua):

1. Crie uma conta em [render.com](https://render.com) (dá pra entrar com
   GitHub).
2. No painel, **New → Blueprint** → conecte este repositório (o Render
   detecta o `render.yaml` sozinho).
3. Nos campos de ambiente marcados como segredo, preencha **direto no
   painel do Render** (nunca comitados, nunca colados em chat):
   - `DATABASE_URL` — a mesma connection string do Neon usada localmente
     (ou uma nova, se preferir separar banco de dev e produção).
   - `SESSION_SECRET_KEY` — gere uma **chave nova**, diferente da usada em
     dev local: `python -c "import secrets; print(secrets.token_hex(32))"`.
   - `ADMIN_NOME`, `ADMIN_EMAIL`, `ADMIN_SENHA` — só têm efeito se o banco
     apontado ainda não tiver nenhum usuário. Se for usar o mesmo Neon que
     já tem a proprietária cadastrada, pode deixar em branco ou repetir os
     mesmos valores — o bootstrap não faz nada se já existe usuário.
4. Deploy automático a cada `git push` pra `main` (comportamento padrão do
   Render em Blueprints) — sem passo manual adicional depois do primeiro
   setup.
5. Migrations (`alembic upgrade head`) **não rodam sozinhas no deploy** —
   continue rodando manualmente do seu ambiente local, apontando pro mesmo
   `DATABASE_URL` do Render, sempre que houver mudança de schema (mesmo
   fluxo já usado até aqui).

Plano free do Render "dorme" após ~15min sem acesso — o primeiro acesso
depois disso demora uns 30-60s pra responder (aceitável só na fase de
desenvolvimento). Dá pra migrar pro plano pago (Starter, sempre ativo)
trocando `plan: free` para `plan: starter` no `render.yaml`, sem mexer em
mais nada. **O Incremento 22 (auditoria A-07) recomenda essa migração
antes de qualquer uso comercial** — uma padaria abre às 5h e o primeiro
pedido do dia pegaria o cold start. Ver [`docs/desempenho.md`](docs/desempenho.md).

## Endpoints disponíveis

Todas as rotas abaixo, exceto `/health` e as de `/auth`, exigem sessão de
login (cookie) — retornam `401` sem ela. Quando o perfil do usuário não
tem acesso à operação, retornam `403` (Incremento 19 — ver coluna
"perfil" abaixo).

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Verificação de saúde da API (não exige login) |
| `POST` | `/auth/login` | Login (e-mail + senha) — cria a sessão. Retorna `429` + `Retry-After` após muitas falhas do mesmo IP (Incremento 17) |
| `POST` | `/auth/logout` | Encerra a sessão |
| `GET` | `/auth/me` | Dados do usuário logado (frontend usa pra checar sessão) |
| `GET` | `/auth/usuarios` | Lista usuários cadastrados — **só proprietária** |
| `POST` | `/auth/usuarios` | Cria outro usuário — **só proprietária** |
| `DELETE` | `/auth/usuarios/{id}` | Desativa um usuário (`ativo=false`, não apaga) — **só proprietária** |
| `POST` | `/auth/trocar-senha` | Troca a própria senha (exige a senha atual) — **só proprietária** |
| `GET` | `/auditoria` | Trilha de operações sensíveis — filtros `entidade`, `entidade_id`, `data_inicio`, `data_fim`, `limite` — **só proprietária** |
| `POST` | `/clientes` | Cadastrar cliente (RF01) — **proprietária/atendente** |
| `GET` | `/clientes` | Listar clientes — qualquer perfil |
| `GET` | `/clientes/{id}` | Consultar um cliente — qualquer perfil |
| `GET` | `/clientes/{id}/pedidos` | Histórico de pedidos do cliente (Incremento 24) — qualquer perfil |
| `POST` | `/produtos` | Cadastrar produto (RF02) — **proprietária/atendente** |
| `GET` | `/produtos?ativo=true` | Listar produtos (filtro opcional por ativo) — qualquer perfil |
| `GET` | `/produtos/{id}` | Consultar um produto — qualquer perfil |
| `PUT` | `/produtos/{id}` | Editar produto já cadastrado — **proprietária/atendente** |
| `POST` | `/pedidos` | Registrar pedido (RF03, RF04) — aplica RN01 — **proprietária/atendente** |
| `GET` | `/pedidos?data_inicio=&data_fim=` | Listar pedidos por período/dia (RF07) — qualquer perfil |
| `GET` | `/pedidos/{id}` | Consultar um pedido, com seus itens (RF05) — qualquer perfil |
| `PUT` | `/pedidos/{id}` | Editar itens/data de um pedido em `recebido` (Incremento 23) — revalida RN01/RN05 — **proprietária/atendente** |
| `POST` | `/pedidos/{id}/confirmar-sinal` | Confirma o sinal de um pedido (suporte a RN02) — **proprietária/atendente** |
| `POST` | `/pedidos/{id}/avancar` | Avança para a próxima etapa de produção — aplica RN02 e RN04 — qualquer perfil (inclui padeiro) |
| `POST` | `/pedidos/{id}/cancelar` | Cancela o pedido (RF06) — aplica RN03 e RN04 — **proprietária/atendente** |

## Regras de negócio principais

| ID | Regra |
|---|---|
| RN01 | Pedido precisa ter entrega com pelo menos 24h de antecedência |
| RN02 | Item personalizável exige sinal confirmado antes de sair de "recebido" |
| RN03 | Cancelamento só é permitido até 12h antes da entrega |
| RN04 | Status segue máquina de estados estrita: recebido → em_producao → pronto → entregue |
| RN05 | Limites realistas: preço até R$ 999,99, quantidade por item até 999, entrega até 90 dias de antecedência |

Detalhes completos em [`CLAUDE.md`](./CLAUDE.md).
