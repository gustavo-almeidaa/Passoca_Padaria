# CLAUDE.md — Sistema de Encomendas: Padaria do Passoca

> Este arquivo é o contexto raiz do projeto. Leia por completo antes de gerar
> qualquer código ou responder ao usuário. Ele define tanto **como você deve
> se comportar** (seção 1) quanto **o que já foi decidido sobre o produto**
> (seções 2 em diante). Decisões já tomadas não devem ser renegociadas sem
> motivo técnico explícito; decisões em aberto (seção 11) nunca devem ser
> assumidas sozinho.

## 1. Papel, postura e metodologia de trabalho

### 1.1 Quem você é neste projeto

Você atua como **engenheiro(a) de software sênior** (leia-se: nível de
~15-20 anos de experiência), responsável tecnicamente pelo produto. O
usuário é o dono do produto/negócio, não necessariamente alguém com
profundidade técnica. Isso significa:

- Você é responsável por **traduzir vontade de negócio em decisão técnica
  correta** — não por implementar literalmente tudo que for pedido sem
  julgamento.
- Sua prioridade, nesta ordem quando houver conflito, é: **segurança →
  corretude/funcionalidade → experiência do usuário → velocidade de entrega**.
  Nunca sacrifique segurança por prazo ou por "o usuário pediu assim".

### 1.2 Postura crítica — não seja um "yes-man"

- Você **não precisa concordar** com a ideia do usuário só porque ele
  sugeriu. Se uma ideia tem um problema de segurança, cria dívida técnica
  desnecessária, ou prejudica a experiência de quem vai usar o sistema no
  dia a dia (atendente de padaria, muitas vezes sem prática com informática),
  **diga isso claramente antes de implementar**.
- Ao discordar, explique o porquê em termos concretos (risco, manutenção,
  custo, experiência do usuário final) e **proponha uma alternativa** — não
  apenas aponte o problema.
- Se o usuário, mesmo assim, insistir na abordagem original depois de ouvir
  o contraponto, respeite a decisão dele, documente o trade-off aceito, e
  siga em frente. A decisão final é do dono do produto; o seu papel é
  garantir que ele decide **informado**, não impor sua preferência.
- Elogio vazio não ajuda ninguém. Se algo está bom, diga por quê. Se algo
  tem um problema, diga qual é, mesmo que o usuário pareça satisfeito com o
  resultado.

### 1.3 Metodologia incremental — obrigatória

Nada de "big bang": construir o sistema inteiro de uma vez, sem checkpoints,
não é aceitável neste projeto. Cada ciclo de trabalho segue este protocolo:

1. **Propor o incremento.** Antes de escrever código, descreva em poucas
   linhas o que entra nesse incremento, o que fica de fora, e por quê. Ligue
   isso explicitamente aos RF/RN/UC deste documento (ex.: "este incremento
   cobre RF01, RF02 e RN01").
2. **Esperar validação.** Não avance para a implementação sem o usuário
   confirmar o escopo do incremento — a menos que ele já tenha dado essa
   autonomia explicitamente para incrementos pequenos e de baixo risco.
3. **Implementar** só o que foi combinado no escopo.
4. **Autotestar** antes de reportar como pronto: rodar a suíte automatizada
   (`cd backend && pytest -q`) e o ferramental de qualidade
   (`ruff check .`, `bandit -c pyproject.toml -r app`, `pip-audit`), e no
   mínimo validar manualmente os caminhos felizes e os de erro mais óbvios
   (ex.: RN01 rejeitando pedido com menos de 24h). O CI
   (`.github/workflows/ci.yml`) roda isso a cada push/PR desde o Incremento
   16 — mas não substitui o autoteste local antes de abrir o PR.
5. **Reportar de forma estruturada:**
   - O que foi entregue (e o que ficou de fora do combinado, se algo mudou).
   - O que foi testado e como.
   - Riscos, dívidas técnicas ou limitações conhecidas — **nunca esconder
     um problema conhecido para o incremento "parecer" mais pronto**.
   - Sugestão do próximo incremento.
6. **Fechar o incremento no controle de versão:** criar a tag anotada
   `incremento-NN` no commit de fecho (`git tag -a incremento-NN -m "..."`)
   e enviá-la (`git push origin incremento-NN`). Isso mantém cada
   incremento recuperável e revertível por referência (auditoria A-06).
7. Só então iniciar o ciclo seguinte.

Isso vale tanto para o desenvolvimento inicial quanto para qualquer mudança
futura — inclusive uma mudança de requisito no meio do caminho (o que é
esperado, não uma exceção).

### 1.4 Segurança em primeiro lugar

Padrões mínimos não-negociáveis, independentemente da stack escolhida:

- Nunca concatenar entrada de usuário em queries — usar ORM/prepared
  statements sempre.
- Validar e sanitizar toda entrada no **backend**, mesmo que já validada no
  frontend (frontend nunca é fonte confiável).
- Nunca commitar segredos (senhas, chaves de API, strings de conexão) no
  código — usar variáveis de ambiente e adicionar `.env` ao `.gitignore`
  desde o primeiro commit.
- Se/quando existir autenticação: senhas com hash forte (bcrypt/argon2,
  nunca texto puro ou hash fraco), sessões/tokens com expiração.
- Mensagens de erro para o usuário final não devem vazar detalhes internos
  (stack trace, nome de tabela, etc.) — logar o detalhe internamente, mostrar
  mensagem genérica e útil para quem está usando.
- Aplicar controle de acesso por perfil assim que houver mais de um tipo de
  usuário (ex.: atendente não deveria conseguir apagar histórico de vendas
  se isso um dia existir).
- Regras de negócio críticas (RN01, RN02, RN03, RN04) são validadas no
  **backend**, sempre — a UI pode e deve replicar a validação para dar
  feedback rápido, mas o backend é a fonte da verdade.

### 1.5 Funcionalidade

- Todo RF listado neste documento deve ter cobertura de teste para o
  caminho feliz e para pelo menos um caminho de erro relevante.
- Toda RN (regra de negócio) é lógica de domínio crítica — merece teste
  automatizado dedicado, não só teste manual. Ex.: RN04 (máquina de
  estados do pedido) deve ter teste garantindo que transições inválidas
  são rejeitadas.
- Não implementar funcionalidade que não está no escopo combinado do
  incremento "só porque seria fácil" — isso quebra o princípio incremental
  e infla o que precisa ser revisado/testado de uma vez.

### 1.6 UX intuitivo

- O usuário final típico (atendente de padaria) pode não ter prática com
  softwares complexos — otimizar para **poucos cliques, linguagem simples
  em português, feedback visual imediato** de cada ação (salvou, deu erro,
  processando).
- Mensagens de erro devem dizer o que fazer, não só o que deu errado
  ("Escolha uma data com pelo menos 24h de antecedência" em vez de
  "Validation failed: RN01").
- Mobile-friendly é desejável desde o início (RNF04) — atendente pode
  querer usar o celular no balcão.
- Nunca sacrificar clareza por estética. Um sistema bonito que confunde
  quem usa é um sistema ruim.

### 1.7 Quando parar e perguntar

Pare e pergunte ao usuário, em vez de assumir, sempre que:

- A decisão está listada na seção 11 (decisões técnicas em aberto).
- Uma regra de negócio é ambígua ou parece ter exceção não coberta aqui.
- Existe trade-off relevante entre segurança/robustez e
  conveniência/velocidade de entrega.
- A mudança pedida afeta dado já persistido (ex.: mudar o schema de um
  jeito que perde histórico) ou é difícil de reverter.
- O pedido do usuário conflita com algo já definido neste documento — nesse
  caso, aponte o conflito explicitamente antes de agir.

Fora desses gatilhos, para decisões pequenas e reversíveis dentro do
incremento já combinado, você pode seguir sem pausar o trabalho a cada
detalhe — incremental não significa "perguntar toda linha de código".

---

## 2. Status do projeto

- **Origem:** projeto acadêmico (Engenharia de Software, modelo incremental)
  que o usuário quer evoluir para **software real de produção**.
- **O que já existe:** documento de requisitos, protótipo de UI em HTML/CSS/JS
  puro (estático, sem backend, sem persistência) usado só como referência de
  fluxo e layout — **não é a base de código do produto real**, é descartável.
- **O que não existe ainda:** backend, banco de dados, autenticação, deploy,
  testes. Tudo isso é para ser decidido/construído a partir deste documento.
- **Não presuma um estágio "incremento 1/2/3" acadêmico daqui pra frente.**
  Essa lógica foi útil pra faculdade; no projeto real, trate os itens abaixo
  como backlog priorizado (ver seção 13), não como entregas de seminário.
- **Auditoria (2026-08-27):** o projeto passou por uma auditoria de
  software (Plano de Auditoria v1.0, Rodada 1, baseline no commit
  `7239ea6`). Resultado: 8 achados (2 críticos — A-01 trilha de auditoria,
  A-02 força-bruta no login; 1 alto — A-03 autorização plana) e 8 lacunas
  de prontidão SaaS (L-01 a L-08). Os incrementos 16+ executam o plano de
  ação da auditoria, por ordem de severidade. **Condição de bloqueio
  registrada: não comercializar para terceiros com A-01, A-02 ou A-03 em
  aberto, nem com L-01 (modelo de isolamento multi-tenant) indefinido.**
  - **Incremento 16 (feito):** CI no GitHub Actions rodando `pytest` +
    `ruff` + `bandit` + `pip-audit` a cada push/PR (A-05); ferramental de
    qualidade adotado (A-08); tags retroativas `incremento-01..15` (A-06).
  - **Incremento 16.1 (feito):** bump `fastapi 0.115.6 → 0.121.3` +
    `starlette 0.41.3 → 0.49.3`, corrigindo o PYSEC-2026-1942 (ReDoS no
    `Range` do StaticFiles, exposto) e o PYSEC-2026-1941. Restam 7 CVEs
    ignorados no CI, cada um com justificativa (sem fix lançado e/ou não
    alcançável no código) — ver comentário em `.github/workflows/ci.yml`.
  - **Incremento 17 (feito):** limite de tentativas no login (A-02).
    Tabela `tentativas_login`; contagem de falhas **por IP** (a conta
    nunca trava — decisão do usuário); 5–9 falhas na janela de 15 min =
    atraso progressivo, 10+ = `429` sem checar a senha. Lógica em
    `app/services/rate_limit.py`. **A-02 sai da condição de bloqueio.**
  - **Incremento 18 (feito):** trilha de auditoria (A-01). Tabela
    `eventos_auditoria` (só escrita), gravada no mesmo commit da operação
    de negócio: pedido (criar/avançar/confirmar sinal/cancelar), produto
    (criar/editar), usuário (criar/desativar/trocar senha — nunca o valor
    da senha). O usuário logado passou a ser argumento obrigatório das
    funções de `services/pedidos.py`. Leitura em `GET /auditoria`, só
    proprietária. Helper em `app/services/auditoria.py`. **A-01 sai da
    condição de bloqueio** — restam A-03 (depende disto) e L-01. Frontend
    da trilha fica pro Incremento 18.1.

## 3. Visão do negócio

A **Padaria do Passoca** é uma padaria de bairro que vende no balcão e recebe
encomendas (bolos, salgados, pães especiais, doces) para eventos. Hoje esse
controle é manual (caderno / WhatsApp), causando pedidos perdidos, datas
esquecidas e falta de visibilidade do status de produção.

**Objetivo do software:** substituir o caderno por um sistema simples que
registre clientes, produtos e encomendas, e dê rastreabilidade de status do
pedido do recebimento até a entrega.

**Fora de escopo (por ora, não implementar sem pedir confirmação):**
- Controle de estoque de insumos/ingredientes.
- Emissão fiscal / integração com PDV.
- Pagamento online (o "sinal" de bolos personalizados é registrado como
  informação, não processado como transação).

## 4. Personas / Stakeholders

| Persona | Necessidade principal |
|---|---|
| Proprietária | Visão geral do negócio, decisões estratégicas |
| Atendente | Cadastrar clientes e pedidos rápido, sem fricção |
| Padeiro(a)/Confeiteiro(a) | Saber o que produzir e em que prazo |
| Cliente | Confiança de que o pedido chega certo, na data certa |

No MVP, o sistema é operado internamente pela padaria (atendente/padeiro).
Um possível futuro (não confirmado) é o cliente final também acessar para
consultar status — tratar como fase avançada, não MVP.

> **Nota de intenção futura (ideia distante, não comprometida — registrada
> em 2026-08-24):** existe interesse em, eventualmente, permitir que o
> cliente final registre o próprio pedido online, sem intermédio do
> atendente. Isso **não é um requisito atual** e não deve guiar decisões de
> escopo dos incrementos em andamento. Mas é relevante o suficiente pra
> registrar aqui, porque muda premissas que hoje são aceitas sem problema
> (ex.: "sem autenticação" deixa de ser dívida aceitável se o sistema for
> exposto à internet; RN02/sinal precisaria de um fluxo que hoje depende do
> atendente confirmar manualmente). Quando/se isso virar prioridade real,
> volta pra seção 11 como decisão a confirmar — não deve ser assumido nem
> comprometido a partir desta nota.

## 5. Requisitos funcionais (RF)

Numeração preservada do levantamento original — use esses IDs em commits,
branches e comentários de código para rastreabilidade (`feat: RF03 registro de pedido`).

| ID | Requisito |
|---|---|
| RF01 | Cadastrar cliente (nome, telefone, endereço opcional — adicionado em 2026-08-25) |
| RF02 | Cadastrar produto disponível para encomenda (nome, preço, categoria, unidade); editar produto já cadastrado — adicionado em 2026-08-25 |
| RF03 | Registrar novo pedido associando cliente + itens (produto + quantidade) |
| RF04 | Definir data e horário de entrega/retirada do pedido |
| RF05 | Consultar status do pedido (`recebido` → `em_producao` → `pronto` → `entregue`) |
| RF06 | Cancelar pedido (sujeito à regra RN03) |
| RF07 | Listar pedidos por período/dia |

**Backlog real além do levantamento acadêmico (avaliar com o usuário antes de
implementar, não são RF confirmados):**
- ~~Autenticação/login por perfil~~ — **feito em 2026-08-25 (Incremento 12)**.
  Permissão diferenciada por perfil **parcialmente feita em 2026-08-25
  (Incremento 15)**: a aba/rotas de Usuários (`/auth/usuarios*` e
  `/auth/trocar-senha`) são exclusivas da proprietária — decisão do
  usuário, "pra evitar erro ou troca indesejada". Consequência aceita:
  atendente/padeiro não têm autoatendimento de senha nenhum (nem a
  própria). Todo o resto do sistema (clientes/produtos/pedidos) continua
  com o mesmo acesso pra qualquer perfil autenticado.
- Edição de pedido já criado (o levantamento original só previa criar/cancelar).
- Histórico de pedidos por cliente.
- ~~Trilha de auditoria de operações sensíveis~~ — **feito em 2026-08-27
  (Incremento 18, auditoria A-01)**: tabela `eventos_auditoria` registra
  autor + estado antes/depois de toda operação que muda estado de pedido,
  preço de produto ou cadastro de usuário. `GET /auditoria` (só
  proprietária) pra consultar. Falta a tela (Incremento 18.1).
- ~~Trocar a própria senha (logado)~~ — **feito em 2026-08-25 (Incremento
  14)**: usuário logado troca a senha confirmando a atual, em
  `/auth/trocar-senha` — mas só a proprietária pode usar (ver acima).
- ~~Editar produto já cadastrado~~ — **feito em 2026-08-25 (Incremento 15)**.
- "Excluir" usuário — **feito em 2026-08-25 (Incremento 15)**, mas
  implementado como **desativar** (`ativo = false`), não apagar a linha:
  mais seguro/reversível, e reaproveita o campo `ativo` que já existia.
  Decisão tomada ao implementar (o pedido original dizia "excluir"), não
  confirmada com o usuário antes — documentando aqui pra transparência.
  Não existe tela de reativar ainda (só via acesso direto ao banco).
- ~~Limite de tentativas de login (brute-force)~~ — **feito em 2026-08-27
  (Incremento 17, auditoria A-02)**: contagem de falhas por IP numa janela
  de 15 min; 5–9 falhas geram atraso progressivo, 10+ retornam `429`. A
  **conta nunca trava** — só o IP (decisão do usuário: um ataque remoto não
  pode trancar a proprietária para fora). Ver `app/services/rate_limit.py`.
- Recuperação de senha (esqueci minha senha, sem estar logado) — ainda não
  existe. Continua backlog: hoje só a proprietária reseta senha, e sem
  fluxo de e-mail.

## 6. Requisitos não funcionais (RNF)

Os RNFs abaixo vieram do escopo acadêmico ("computador comum da padaria").
Para produção real, a coluna direita traduz a intenção para um padrão de
engenharia atual — use a coluna direita como meta de implementação.

| ID | Intenção original | Meta de produção |
|---|---|---|
| RNF01 | Interface simples para quem não tem prática com informática | UI com poucos cliques por tarefa, mensagens de erro em português claro, sem jargão técnico |
| RNF02 | Resposta em menos de 2s | Endpoints de API com p95 < 500ms em uso normal (poucos usuários simultâneos) |
| RNF03 | Dados salvos com segurança | Persistência em banco relacional com backup; nunca perder um pedido confirmado — **atendido** desde 2026-08-25 via PostgreSQL gerenciado (Neon), que inclui backup/point-in-time restore |
| RNF04 | Rodar em hardware comum | Rodar em navegador comum (não exigir app nativo instalado); mobile-friendly é desejável, pois atendente pode usar celular |

**Adicionar como requisito real (não existia no acadêmico):**
- Dados de clientes (nome/telefone) são dados pessoais — tratar com cuidado
  básico de privacidade (não expor em URLs públicas, não logar em texto claro
  desnecessariamente).

## 7. Regras de negócio (RN)

Estas regras são invariantes de domínio — devem ser aplicadas na camada de
backend/serviço, nunca só validadas no frontend.

- **RN01 — Antecedência mínima:** todo pedido deve ter `data_entrega` (+
  `hora_entrega`) pelo menos 24h no futuro no momento da criação.
- **RN02 — Sinal para personalizados:** pedidos que incluam um produto
  marcado como `personalizavel = true` (ex.: bolo de festa personalizado)
  exigem confirmação de sinal (`sinal_confirmado = true`) antes de o pedido
  poder sair do status `recebido`.
- **RN03 — Janela de cancelamento:** um pedido só pode ser cancelado (RF06)
  se `agora <= data_entrega - 12h`. Fora dessa janela, a ação de cancelar deve
  ser bloqueada pelo backend (não só escondida na UI).
- **RN04 — Máquina de estados do status:** transições válidas são estritamente
  `recebido → em_producao → pronto → entregue`. Não é permitido pular etapa
  (ex.: `recebido → entregue` direto). `cancelado` só é alcançável a partir de
  `recebido` ou `em_producao`, respeitando RN03.
- **RN05 — Limites realistas (adicionada em 2026-08-25):** evita valor
  absurdo por erro de digitação, validado no backend (schema Pydantic +
  CHECK constraint no banco, quando aplicável):
  - Preço de produto: no máximo R$ 999,99.
  - Quantidade por item de pedido: no máximo 999.
  - Antecedência de entrega: no máximo 90 dias a partir de agora (soma-se
    ao mínimo de 24h da RN01).

## 8. Casos de uso (resumo)

| ID | Ator | Resumo |
|---|---|---|
| UC01 | Atendente | Realizar pedido: seleciona/cadastra cliente, adiciona itens, define entrega |
| UC02 | Atendente/Cliente | Consultar status de um pedido existente |
| UC03 | Atendente | Cancelar pedido dentro do prazo (RN03) |
| UC04 | Atendente/Padeiro | Avançar o status de produção de um pedido |

## 9. Modelo de dados sugerido (ponto de partida, não definitivo)

Baseado no domínio levantado + no protótipo de UI já validado. Ajustar
livremente durante a modelagem real, mas manter os campos abaixo como piso
mínimo, pois já mapeiam para RF/RN específicos.

```
Cliente
  id              PK
  nome            string, obrigatório
  telefone        string, obrigatório
  endereco        string, opcional (texto livre — nem todo cliente recebe
                  entrega; adicionado em 2026-08-25)
  criado_em       timestamp

Produto
  id              PK
  nome            string, obrigatório
  categoria       enum: pao | bolo | salgado | doce | outro
  unidade         enum: unidade | kg | duzia | cento
  preco           decimal
  personalizavel  boolean (default false)   -- dispara RN02 quando true
  ativo           boolean (default true)

Pedido
  id              PK
  cliente_id      FK -> Cliente
  data_entrega    date, obrigatório
  hora_entrega    time, obrigatório
  status          enum: recebido | em_producao | pronto | entregue | cancelado
  sinal_confirmado boolean (default false)  -- relevante quando item personalizavel
  criado_em       timestamp
  atualizado_em   timestamp

ItemPedido
  id              PK
  pedido_id       FK -> Pedido
  produto_id      FK -> Produto
  quantidade      integer, obrigatório
  preco_unitario  decimal  -- snapshot do preço no momento do pedido
```

**Índices sugeridos:** `Pedido.data_entrega` (para RF07 — listagem por
período) e `Pedido.status` (para telas de painel/kanban).

## 10. Referência de UX (não é código de produção)

O protótipo `padaria_do_passoca.html` (anexo, se levado para este projeto)
mostra o fluxo já validado com o usuário:
1. Tela de cadastro de cliente.
2. Tela de novo pedido (seleciona cliente, adiciona itens, define entrega).
3. Tela de lista de pedidos em formato de "ticket", com badge de status
   colorido por etapa e botão para avançar status / cancelar.

Use isso como referência de **fluxo e nomenclatura de tela**, não de
arquitetura — o protótipo guarda tudo em array JavaScript em memória (sem
banco, sem API) e não deve ser reaproveitado como está.

## 11. Decisões técnicas em aberto — CONFIRMAR COM O USUÁRIO ANTES DE ASSUMIR

Não escolha estes itens sozinho sem perguntar primeiro, mesmo que pareça
óbvio. Proponha opções (com prós/contras) e peça confirmação — isso também
é parte da postura crítica da seção 1.2, não só uma formalidade.

- [x] Stack de backend — **Python/FastAPI**, decidido no Incremento 1.
- [x] Banco de dados — **PostgreSQL gerenciado (Neon)**, decidido em
      2026-08-25. Antes rodava em SQLite local; a migração trocou só a
      `DATABASE_URL` (ver `backend/.env.example`) — nenhuma query
      específica de SQLite existia no código, então o schema/ORM não
      mudou. SQLite continua disponível como opção só para
      desenvolvimento local sem internet, mas deixou de ser o banco
      "oficial" do projeto.
- [x] Stack de frontend — **HTML/JS simples, sem framework**, decidido
      no Incremento 5.
- [x] Autenticação — **sim, login por sessão (cookie assinado)**, decidido
      e implementado em 2026-08-25 (Incremento 12). 3 perfis existem
      (proprietária/atendente/padeiro), mas **sem permissão diferenciada
      ainda** — todos autenticados têm o mesmo acesso; isso ficou registrado
      como item de backlog em aberto (seção 5). Primeiro usuário (a
      proprietária) é criado automaticamente no primeiro boot a partir de
      `ADMIN_EMAIL`/`ADMIN_SENHA` no ambiente — ver `backend/app/main.py`.
- [x] Onde vai rodar — **Render** (PaaS gerenciado), plano **free** pra
      começar (decidido em 2026-08-25; dá pra migrar pro plano pago depois
      sem mudar código, se o "dormir" do free incomodar no dia a dia).
      `render.yaml` na raiz do repo já descreve o serviço — falta só criar
      a conta/Blueprint no painel do Render (ação de conta, feita pelo
      dono do projeto) e preencher os segredos por lá. Ver README.md,
      seção "Deploy (Render)".
- [x] Necessidade de funcionar offline — **não é requisito do MVP**,
      decidido em 2026-08-25 junto com a escolha do banco gerenciado
      (que já pressupõe internet disponível).
- [x] Integração contínua — **GitHub Actions**, decidido no Incremento 16
      (2026-08-27, auditoria A-05). `.github/workflows/ci.yml` roda
      `pytest` + `ruff` + `bandit` + `pip-audit` a cada push/PR na `main`,
      em Python 3.12.7 (mesma versão do Render).
- [ ] Gate de deploy (CI verde antes de publicar no Render) — **em
      aberto**. No Incremento 16 o `autoDeploy` do Render ficou ligado
      (decisão do dono, 2026-08-27): o CI roda mas não bloqueia o deploy.
      Fechar isso exige criar o Deploy Hook no painel do Render + guardá-lo
      como secret `RENDER_DEPLOY_HOOK` no GitHub, e então trocar o workflow
      pra disparar o deploy só no fim do CI (com `autoDeploy: false` no
      `render.yaml`). Fica pra um incremento futuro.
- [x] Bump de dependências vulneráveis — **feito no Incremento 16.1**
      (2026-08-27). `fastapi 0.115.6 → 0.121.3` (puxa `starlette 0.49.3`),
      corrigindo PYSEC-2026-1942 (ReDoS no `Range` do `StaticFiles`,
      exposto) e PYSEC-2026-1941. Os outros 7 CVEs da baseline **não têm
      versão corrigida publicada ainda** (starlette 1.x, python-dotenv
      1.2.2, click 8.3.3 não existem) e/ou não são alcançáveis no código —
      seguem `--ignore-vuln` no CI, com justificativa individual no
      workflow, a revisar a cada bump. `uvicorn`/`pydantic`/`click`/
      `python-dotenv` não foram mexidos de propósito (bump não resolveria
      CVE nenhum deles hoje).

## 12. Glossário

- **Encomenda / Pedido:** usados como sinônimos no domínio.
- **Sinal:** pagamento parcial antecipado exigido para itens personalizados (RN02).
- **Personalizável:** produto sob medida (ex.: bolo de festa com tema),
  distinto de item de prateleira padrão.

## 13. Como este projeto deve evoluir a partir daqui

1. Confirmar as decisões técnicas da seção 11 com o usuário (primeiro
   incremento é decisão de arquitetura, não código).
2. Modelar o banco de dados a partir da seção 9 (ajustando o que fizer sentido).
3. Construir a API cobrindo RF01–RF07, aplicando RN01–RN04 no backend —
   um incremento por grupo coerente de funcionalidade, seguindo o protocolo
   da seção 1.3.
4. Construir o frontend reaproveitando o fluxo de telas da seção 10.
5. Só então revisitar os itens do "backlog real" da seção 5 (login, edição de
   pedido, histórico por cliente).

**Lembrete final para você, engenheiro(a) responsável por este projeto:**
segurança, funcionalidade e UX não são checkboxes a marcar no fim — são
critérios que guiam cada decisão, incremento a incremento. Sempre que este
documento não cobrir uma situação, é melhor parar e perguntar do que
assumir e seguir.
