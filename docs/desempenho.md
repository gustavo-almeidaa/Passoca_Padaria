# Desempenho — medição e plano de hospedagem

> Incremento 22, executando o achado **A-07** da auditoria (2026-08-27):
> o RNF de desempenho (p95 < 500ms, `CLAUDE.md` seção 6) nunca tinha sido
> medido. A não conformidade era a *ausência de medição* — este documento
> a resolve e registra a baseline.

## Como medir

Com o servidor no ar e um usuário proprietária/atendente:

```bash
cd backend
python loadtest/carga.py \
    --url http://127.0.0.1:8000 \
    --email dona@passoca.com --senha SUA_SENHA \
    --usuarios 5 --rodadas 40
```

O script (`backend/loadtest/carga.py`, Python puro) simula o fluxo de
balcão — login, listar pedidos do dia, consultar, registrar, avançar
status — com poucos usuários simultâneos, que é o cenário do projeto
(padaria de bairro). Imprime p50/p95/p99 por operação.

Instrumentação sempre ligada: todo response traz o header
`X-Response-Time`, e requisições acima de 500ms viram `WARNING` no log
(`app/main.py::medir_tempo_de_resposta`) — dá pra ver no log do Render sem
rodar nada.

## Baseline (2026-08-27)

Ambiente: máquina de desenvolvimento, **SQLite** local, sem rede.
5 usuários × 40 rodadas.

| Operação | p50 | p95 | p99 |
|---|---:|---:|---:|
| `GET /pedidos` (dia) | 15ms | 68ms | 91ms |
| `GET /pedidos/{id}` | 30ms | 97ms | 113ms |
| `POST /pedidos` | 90ms | 200ms | 243ms |
| `POST /pedidos/{id}/avancar` | 94ms | 187ms | 228ms |
| `POST /auth/login` | 362ms | 416ms | 425ms |
| **agregado** | — | **164ms** | — |

### Leitura

- **Os endpoints em si cabem no orçamento** de 500ms com folga.
- **`POST /auth/login` é o mais pesado (~400ms)** — é o custo do `bcrypt`
  (12 rounds) verificando a senha. Acontece uma vez por turno de trabalho,
  não a cada ação, então é aceitável. **Risco:** a CPU do plano free do
  Render é mais lenta que a da máquina de dev; lá o login pode passar de
  500ms. Não mexer nos rounds do bcrypt (é segurança) — se incomodar,
  a resposta é CPU melhor (plano pago), não hash mais fraco.
- `GET /pedidos` ganhou `selectinload` nos itens neste incremento (antes
  fazia N+1: uma query por pedido do dia pra carregar os itens). No SQLite
  isso quase não aparecia; contra o Postgres do Neon, com o dia cheio,
  viraria segundos. Agora são 2 queries no total, com teste de regressão
  (`test_listar_nao_faz_n_mais_1_ao_carregar_itens`).

### Limites desta medição

Números **locais em SQLite** = piso otimista. Em produção somam-se:
latência de rede até o Neon (cada query ~5-20ms de ida e volta), o tier de
CPU do Render, e o **cold start** (ver abaixo). Uma medição representativa
de verdade só dá pra fazer contra o ambiente publicado — o que exige o
plano pago primeiro (senão o cold start domina todo número).

## Plano de hospedagem — recomendação (decisão do dono + cliente)

O `render.yaml` está em **`plan: free`**. O plano free **suspende a
instância após ~15 min sem acesso** — o primeiro acesso depois disso
demora **30-60s** pra responder.

Para uma padaria que **abre às 5h da manhã**, o primeiro pedido do dia cai
exatamente nesse cold start. A auditoria classificou isso como
**incompatível com operação de balcão**.

**Recomendação:** antes de qualquer uso comercial, migrar para o plano
**Starter** do Render (~US$ 7/mês, instância sempre ativa). A mudança é
**uma linha** no `render.yaml`:

```yaml
    plan: starter   # era: free
```

Nenhuma outra alteração de código. Depois disso, vale refazer a medição
acima **contra o ambiente publicado** para ter o número real de produção.

Esta é uma **decisão de negócio** (custo recorrente) — fica com o dono do
projeto, em conversa com o cliente. Registrado aqui como recomendação
técnica fundamentada, não como pendência de engenharia.
