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

🚧 Em desenvolvimento — Fase 1 (fundação técnica).

Autenticação/login por perfil está deliberadamente fora do MVP (ver backlog
no `CLAUDE.md`, seção 5 e 13). O sistema roda hoje sem autenticação, para
uso na rede interna da padaria.

## Estrutura do repositório

```
Passoca_Padaria/
├── backend/
│   ├── app/
│   │   ├── models/      # modelos SQLAlchemy
│   │   ├── schemas/     # schemas Pydantic
│   │   ├── services/    # regras de negócio (RN01-RN04)
│   │   ├── api/         # rotas/endpoints FastAPI
│   │   └── core/        # config, banco, etc.
│   ├── migrations/      # Alembic
│   └── tests/           # pytest
├── frontend/
└── CLAUDE.md
```

## Rodando localmente

_(instruções serão adicionadas conforme o backend for implementado)_

## Regras de negócio principais

| ID | Regra |
|---|---|
| RN01 | Pedido precisa ter entrega com pelo menos 24h de antecedência |
| RN02 | Item personalizável exige sinal confirmado antes de sair de "recebido" |
| RN03 | Cancelamento só é permitido até 12h antes da entrega |
| RN04 | Status segue máquina de estados estrita: recebido → em_producao → pronto → entregue |

Detalhes completos em [`CLAUDE.md`](./CLAUDE.md).
