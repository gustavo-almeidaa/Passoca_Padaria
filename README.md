# Passoca_Padaria

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
- **Testes:** pytest (roda contra SQLite isolado em memória — não depende do Neon)

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

O sistema passou a depender de internet, já que o banco agora é gerenciado
na nuvem (decisão registrada: funcionar offline não é requisito do MVP).

## Estrutura do repositório

```
Passoca_Padaria/
├── backend/
│   ├── app/
│   │   ├── models/       # modelos SQLAlchemy (Cliente, Produto, Pedido, ItemPedido, Usuario)
│   │   ├── schemas/      # schemas Pydantic — Cliente, Produto, Pedido e Usuario
│   │   ├── services/     # regras de negócio — RN01-RN05 aplicadas no backend
│   │   ├── api/          # rotas FastAPI — /clientes, /produtos, /pedidos, /auth
│   │   │                 # + deps.py (dependência de autenticação)
│   │   ├── main.py       # ponto de entrada da API (app FastAPI)
│   │   └── core/         # config (settings), conexão com banco e security.py (hash de senha)
│   ├── migrations/       # Alembic — histórico de mudanças de schema
│   ├── tests/            # pytest
│   ├── .env.example      # modelo de variáveis de ambiente
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── index.html         # página única — tela de login + 5 seções (Clientes,
│   │                       # Produtos, Novo Pedido, Pedidos, Usuários) trocadas
│   │                       # via JS, sem reload
│   ├── css/style.css      # estilo compartilhado entre as seções
│   └── js/                # api.js (cliente HTTP), ui.js (feedback visual),
│                           # app.js (controlador de abas), auth.js (login/logout),
│                           # cadastro-cliente.js, cadastro-produto.js,
│                           # novo-pedido.js, lista-pedidos.js, usuarios.js
├── docs/referencia-prototipo/  # protótipo HTML original, só como referência de UX
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
`itens_pedido`, `usuarios`) no banco Postgres do Neon e roda os 128 testes
automatizados (schema + API + service de pedidos + autenticação — cada
teste usa um SQLite em memória isolado, não toca no Neon). No primeiro
boot, se `ADMIN_EMAIL`/`ADMIN_SENHA` estiverem configurados e o banco não
tiver nenhum usuário, a conta da proprietária é criada automaticamente.
Com o servidor no ar: o sistema fica em `http://127.0.0.1:8000/` — pede
login antes de mostrar qualquer tela — e a documentação interativa
(Swagger) em `http://127.0.0.1:8000/docs`.

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
depois disso demora uns 30-60s pra responder (decisão registrada, aceitável
pra fase inicial). Dá pra migrar pro plano pago (Starter, sempre ativo)
depois só trocando `plan: free` para `plan: starter` no `render.yaml`, sem
mexer em mais nada.

## Endpoints disponíveis

Todas as rotas abaixo, exceto `/health` e as de `/auth`, exigem sessão de
login (cookie) — retornam `401` sem ela.

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Verificação de saúde da API (não exige login) |
| `POST` | `/auth/login` | Login (e-mail + senha) — cria a sessão |
| `POST` | `/auth/logout` | Encerra a sessão |
| `GET` | `/auth/me` | Dados do usuário logado (frontend usa pra checar sessão) |
| `GET` | `/auth/usuarios` | Lista usuários cadastrados — **só proprietária** |
| `POST` | `/auth/usuarios` | Cria outro usuário — **só proprietária** |
| `DELETE` | `/auth/usuarios/{id}` | Desativa um usuário (`ativo=false`, não apaga) — **só proprietária** |
| `POST` | `/auth/trocar-senha` | Troca a própria senha (exige a senha atual) — **só proprietária** |
| `POST` | `/clientes` | Cadastrar cliente (RF01) |
| `GET` | `/clientes` | Listar clientes |
| `GET` | `/clientes/{id}` | Consultar um cliente |
| `POST` | `/produtos` | Cadastrar produto (RF02) |
| `GET` | `/produtos?ativo=true` | Listar produtos (filtro opcional por ativo) |
| `GET` | `/produtos/{id}` | Consultar um produto |
| `PUT` | `/produtos/{id}` | Editar produto já cadastrado (todos os campos) |
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
| RN05 | Limites realistas: preço até R$ 999,99, quantidade por item até 999, entrega até 90 dias de antecedência |

Detalhes completos em [`CLAUDE.md`](./CLAUDE.md).
