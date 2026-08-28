/*
 * Tela de Pedidos — RF05 (consultar status), RF07 (listar por período) e as
 * ações do ciclo de vida: RN02 (confirmar sinal), RN04 (avançar status) e
 * RF06/RN03 (cancelar).
 *
 * `PedidoRead` só traz `cliente_id` e `produto_id` por item (sem nome) — os
 * nomes exibidos vêm de `GET /clientes` e `GET /produtos`, cruzados aqui no
 * frontend por id. As janelas de tempo (RN02 bloqueando "avançar", RN03
 * bloqueando "cancelar") são replicadas aqui só para desabilitar o botão e
 * dar feedback imediato — o backend segue como fonte da verdade e é quem
 * realmente rejeita a ação se o relógio virar entre o carregamento da tela
 * e o clique.
 */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-filtro");
  const inputDataInicio = document.getElementById("f-data-inicio");
  const inputDataFim = document.getElementById("f-data-fim");
  const feedback = document.getElementById("feedback-pedidos");
  const botaoBuscar = document.getElementById("botao-buscar");
  const listaPedidos = document.getElementById("lista-pedidos");

  const ROTULOS_STATUS = {
    recebido: "Recebido",
    em_producao: "Em produção",
    pronto: "Pronto",
    entregue: "Entregue",
    cancelado: "Cancelado",
  };
  const PROXIMO_STATUS_LABEL = {
    recebido: "Iniciar produção",
    em_producao: "Marcar como pronto",
    pronto: "Marcar como entregue",
  };
  const STATUS_CANCELAVEIS = new Set(["recebido", "em_producao"]);
  const JANELA_CANCELAMENTO_MS = 12 * 60 * 60 * 1000;

  let clientesPorId = new Map();
  let produtosPorId = new Map();
  let pedidosPorId = new Map();

  const DIA_MS = 24 * 60 * 60 * 1000;

  // Padrão: semana a partir de hoje (decisão do usuário, 2026-08-25) — só
  // definido uma vez ao carregar a página, pra não sobrescrever um filtro
  // que o atendente já tenha ajustado ao voltar pra essa aba depois.
  inputDataInicio.value = new Date().toISOString().slice(0, 10);
  inputDataFim.value = new Date(Date.now() + 6 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10);

  // Incremento 9: a tela agora é uma seção da página única — recarrega
  // clientes/produtos de referência e refaz a busca sempre que o atendente
  // volta pra essa aba (pode ter cadastrado cliente/produto nas outras).
  // Incremento 12: sem carga eager aqui, ver nota equivalente em
  // cadastro-cliente.js.
  document.addEventListener("tela:ativada", (evento) => {
    if (evento.detail.tela === "pedidos") inicializar();
  });

  async function inicializar() {
    try {
      const [clientes, produtos] = await Promise.all([
        api.listarClientes(),
        api.listarProdutos(),
      ]);
      clientesPorId = new Map(clientes.map((c) => [c.id, c]));
      produtosPorId = new Map(produtos.map((p) => [p.id, p]));
    } catch (erro) {
      mostrarFeedback(feedback, erro.message, "erro");
    }
    await buscarPedidos();
  }

  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    buscarPedidos();
  });

  async function buscarPedidos() {
    limparFeedback(feedback);
    if (!inputDataInicio.value) {
      mostrarFeedback(feedback, "Informe a data inicial do período.", "erro");
      return;
    }

    definirCarregando(botaoBuscar, true, "Buscando...");
    listaPedidos.innerHTML = '<p class="empty">Carregando…</p>';
    try {
      const pedidos = await api.listarPedidos({
        data_inicio: inputDataInicio.value,
        data_fim: inputDataFim.value || undefined,
      });
      renderPedidos(pedidos);
    } catch (erro) {
      listaPedidos.innerHTML = "";
      mostrarFeedback(feedback, erro.message, "erro");
    } finally {
      definirCarregando(botaoBuscar, false);
    }
  }

  function renderPedidos(pedidos) {
    pedidosPorId = new Map(pedidos.map((p) => [p.id, p]));
    if (pedidos.length === 0) {
      listaPedidos.innerHTML = '<p class="empty">Nenhum pedido nesse período.</p>';
      return;
    }
    listaPedidos.innerHTML = pedidos.map(montarTicket).join("");
    listaPedidos.querySelectorAll("[data-acao]").forEach((botao) => {
      botao.addEventListener("click", () =>
        executarAcao(botao.dataset.acao, Number(botao.dataset.pedidoId))
      );
    });
  }

  function montarTicket(pedido) {
    const cliente = clientesPorId.get(pedido.cliente_id);
    const nomeCliente = cliente ? cliente.nome : `cliente #${pedido.cliente_id}`;
    const temPersonalizavel = pedido.itens.some((item) => {
      const produto = produtosPorId.get(item.produto_id);
      return produto && produto.personalizavel;
    });

    const itensHtml = pedido.itens
      .map((item) => {
        const produto = produtosPorId.get(item.produto_id);
        const nomeProduto = produto ? produto.nome : `produto #${item.produto_id}`;
        const subtotal = Number(item.preco_unitario) * item.quantidade;
        return `<li>${item.quantidade}× ${escapeHtml(nomeProduto)} — ${formatarMoeda(subtotal)}</li>`;
      })
      .join("");

    const total = pedido.itens.reduce(
      (soma, item) => soma + Number(item.preco_unitario) * item.quantidade,
      0
    );

    return `
      <div class="ticket" data-pedido="${pedido.id}">
        <div class="ticket__topo">
          <div><b>Pedido #${pedido.id}</b> — ${escapeHtml(nomeCliente)}</div>
          <span class="badge badge--${pedido.status}">${ROTULOS_STATUS[pedido.status] || pedido.status}</span>
        </div>
        <div class="ticket__entrega">Entrega em ${formatarDataBr(pedido.data_entrega)} às ${pedido.hora_entrega.slice(0, 5)}</div>
        <ul class="ticket__itens">${itensHtml}</ul>
        <div class="ticket__total">Total: <b>${formatarMoeda(total)}</b></div>
        ${
          temPersonalizavel
            ? `<div class="ticket__sinal">${pedido.sinal_confirmado ? "✅ Sinal confirmado" : "⚠️ Sinal pendente"}</div>`
            : ""
        }
        <div class="ticket__acoes">${montarAcoes(pedido, temPersonalizavel)}</div>
        <p class="feedback ticket__feedback" role="status" hidden></p>
      </div>`;
  }

  function montarAcoes(pedido, temPersonalizavel) {
    const botoes = [];

    // Incremento 20 (A-03): o padeiro só avança status de produção —
    // confirmar sinal e cancelar são de balcão (proprietária/atendente).
    // O backend barra com 403 de qualquer forma; aqui é só não oferecer.
    const ehPadeiro =
      window.usuarioAtual && window.usuarioAtual.perfil === "padeiro";

    if (
      !ehPadeiro &&
      pedido.status === "recebido" &&
      temPersonalizavel &&
      !pedido.sinal_confirmado
    ) {
      botoes.push(
        `<button type="button" class="secondary" data-acao="confirmar-sinal" data-pedido-id="${pedido.id}">Confirmar sinal</button>`
      );
    }

    // Incremento 23.1: editar só faz sentido enquanto o pedido está em
    // `recebido` (o backend rejeita depois disso) e é ação de balcão.
    if (!ehPadeiro && pedido.status === "recebido") {
      botoes.push(
        `<button type="button" class="secondary" data-acao="editar" data-pedido-id="${pedido.id}">Editar</button>`
      );
    }

    const proximoLabel = PROXIMO_STATUS_LABEL[pedido.status];
    if (proximoLabel) {
      const bloqueadoPorSinal =
        pedido.status === "recebido" && temPersonalizavel && !pedido.sinal_confirmado;
      botoes.push(
        `<button type="button" class="action action--small" data-acao="avancar" data-pedido-id="${pedido.id}"${
          bloqueadoPorSinal ? ' disabled title="Confirme o sinal antes de avançar"' : ""
        }>${proximoLabel}</button>`
      );
    }

    if (!ehPadeiro && STATUS_CANCELAVEIS.has(pedido.status)) {
      const momentoEntrega = new Date(`${pedido.data_entrega}T${pedido.hora_entrega}`);
      const janelaFechada = momentoEntrega.getTime() - Date.now() < JANELA_CANCELAMENTO_MS;
      botoes.push(
        `<button type="button" class="danger" data-acao="cancelar" data-pedido-id="${pedido.id}"${
          janelaFechada ? ' disabled title="Faltam menos de 12h para a entrega"' : ""
        }>Cancelar pedido</button>`
      );
    }

    return botoes.join("");
  }

  async function executarAcao(acao, pedidoId) {
    const ticket = listaPedidos.querySelector(`.ticket[data-pedido="${pedidoId}"]`);
    const ticketFeedback = ticket.querySelector(".ticket__feedback");
    limparFeedback(ticketFeedback);

    if (acao === "editar") {
      abrirEdicao(pedidoId, ticket);
      return;
    }

    if (acao === "cancelar") {
      const confirmado = window.confirm("Cancelar este pedido? Essa ação não pode ser desfeita.");
      if (!confirmado) return;
    }

    try {
      if (acao === "confirmar-sinal") await api.confirmarSinal(pedidoId);
      else if (acao === "avancar") await api.avancarPedido(pedidoId);
      else if (acao === "cancelar") await api.cancelarPedido(pedidoId);
      await buscarPedidos();
    } catch (erro) {
      mostrarFeedback(ticketFeedback, erro.message, "erro");
    }
  }

  // --- Edição de pedido (Incremento 23.1) --------------------------------
  //
  // Painel montado sob demanda dentro do próprio ticket. Espelha as
  // validações de RN01/RN05 e do teto de quantidade só para feedback
  // rápido — o backend (PUT /pedidos/{id}) é a fonte da verdade.

  function opcoesProdutoEdicao(selecionadoId) {
    // Produto novo tem que estar ativo; um que já está no pedido pode
    // continuar mesmo desativado depois (o backend permite).
    const lista = [...produtosPorId.values()].filter(
      (p) => p.ativo || String(p.id) === String(selecionadoId)
    );
    const placeholder = `<option value="" disabled${
      selecionadoId ? "" : " selected"
    }>Selecione o produto</option>`;
    return (
      placeholder +
      lista
        .map((p) => {
          const sel = String(p.id) === String(selecionadoId) ? " selected" : "";
          const rotulo = p.ativo ? "" : " (fora de linha)";
          return `<option value="${p.id}" data-preco="${p.preco}"${sel}>${escapeHtml(
            p.nome
          )}${rotulo} — ${formatarMoeda(p.preco)}</option>`;
        })
        .join("")
    );
  }

  function linhaItemEdicao(produtoId, quantidade) {
    const linha = document.createElement("div");
    linha.className = "item-pedido-row";
    linha.innerHTML = `
      <select class="item-produto">${opcoesProdutoEdicao(produtoId)}</select>
      <input class="item-quantidade" type="number" min="1" max="999" step="1" value="${quantidade}" aria-label="Quantidade">
      <span class="item-subtotal">${formatarMoeda(0)}</span>
      <button type="button" class="item-remover" aria-label="Remover item">✕</button>`;
    return linha;
  }

  function abrirEdicao(pedidoId, ticket) {
    if (ticket.querySelector(".ticket__edicao")) return; // já aberto
    const pedido = pedidosPorId.get(pedidoId);
    if (!pedido) return;

    const hoje = new Date().toISOString().slice(0, 10);
    const max = new Date(Date.now() + 90 * DIA_MS).toISOString().slice(0, 10);

    const painel = document.createElement("div");
    painel.className = "ticket__edicao";
    painel.innerHTML = `
      <div class="row">
        <div>
          <label>Nova data de entrega</label>
          <input type="date" class="edit-data" value="${pedido.data_entrega}" min="${hoje}" max="${max}">
        </div>
        <div>
          <label>Novo horário</label>
          <input type="time" class="edit-hora" value="${pedido.hora_entrega.slice(0, 5)}">
        </div>
      </div>
      <label>Itens do pedido</label>
      <div class="edit-itens"></div>
      <button type="button" class="secondary" data-add-item>+ Adicionar item</button>
      <p class="total">Total: <b class="edit-total">${formatarMoeda(0)}</b></p>
      <div class="ticket__acoes">
        <button type="button" class="action action--small" data-salvar-edicao>Salvar alterações</button>
        <button type="button" class="secondary" data-cancelar-edicao>Cancelar edição</button>
      </div>`;

    const acoes = ticket.querySelector(".ticket__acoes");
    acoes.hidden = true;
    acoes.after(painel);

    const itensEl = painel.querySelector(".edit-itens");
    pedido.itens.forEach((item) =>
      itensEl.appendChild(linhaItemEdicao(item.produto_id, item.quantidade))
    );

    painel.addEventListener("input", () => recalcularEdicao(painel));
    painel.addEventListener("change", () => recalcularEdicao(painel));
    painel.querySelector("[data-add-item]").addEventListener("click", () => {
      itensEl.appendChild(linhaItemEdicao("", 1));
      recalcularEdicao(painel);
    });
    itensEl.addEventListener("click", (evento) => {
      if (evento.target.classList.contains("item-remover") && itensEl.children.length > 1) {
        evento.target.closest(".item-pedido-row").remove();
        recalcularEdicao(painel);
      }
    });
    painel.querySelector("[data-cancelar-edicao]").addEventListener("click", () => {
      painel.remove();
      acoes.hidden = false;
    });
    painel
      .querySelector("[data-salvar-edicao]")
      .addEventListener("click", () => salvarEdicao(pedidoId, painel, ticket));

    recalcularEdicao(painel);
  }

  function recalcularEdicao(painel) {
    let total = 0;
    painel.querySelectorAll(".item-pedido-row").forEach((linha) => {
      const opcao = linha.querySelector(".item-produto").selectedOptions[0];
      const qtd = Math.max(0, Number(linha.querySelector(".item-quantidade").value) || 0);
      const preco = opcao ? Number(opcao.dataset.preco || 0) : 0;
      const subtotal = preco * qtd;
      linha.querySelector(".item-subtotal").textContent = formatarMoeda(subtotal);
      total += subtotal;
    });
    painel.querySelector(".edit-total").textContent = formatarMoeda(total);
  }

  function coletarItensEdicao(painel) {
    const itens = [];
    for (const linha of painel.querySelectorAll(".item-pedido-row")) {
      const produtoId = linha.querySelector(".item-produto").value;
      const quantidade = Number(linha.querySelector(".item-quantidade").value);
      if (!produtoId) return { erro: "Selecione o produto em todos os itens." };
      if (!Number.isInteger(quantidade) || quantidade <= 0) {
        return { erro: "A quantidade de cada item precisa ser um inteiro maior que zero." };
      }
      if (quantidade > 999) return { erro: "A quantidade de cada item não pode passar de 999." };
      itens.push({ produto_id: Number(produtoId), quantidade });
    }
    return { itens };
  }

  async function salvarEdicao(pedidoId, painel, ticket) {
    const ticketFeedback = ticket.querySelector(".ticket__feedback");
    limparFeedback(ticketFeedback);

    const dataEntrega = painel.querySelector(".edit-data").value;
    const horaEntrega = painel.querySelector(".edit-hora").value;
    if (!dataEntrega || !horaEntrega) {
      mostrarFeedback(ticketFeedback, "Informe a data e o horário de entrega.", "erro");
      return;
    }

    const momento = new Date(`${dataEntrega}T${horaEntrega}`);
    if (Number.isNaN(momento.getTime()) || momento < new Date(Date.now() + DIA_MS)) {
      mostrarFeedback(
        ticketFeedback,
        "Escolha uma data e horário com pelo menos 24h de antecedência.",
        "erro"
      );
      return;
    }
    if (momento > new Date(Date.now() + 90 * DIA_MS)) {
      mostrarFeedback(ticketFeedback, "Escolha uma data de entrega em até 90 dias.", "erro");
      return;
    }

    const { itens, erro } = coletarItensEdicao(painel);
    if (erro) {
      mostrarFeedback(ticketFeedback, erro, "erro");
      return;
    }

    const botao = painel.querySelector("[data-salvar-edicao]");
    definirCarregando(botao, true, "Salvando...");
    try {
      await api.editarPedido(pedidoId, {
        data_entrega: dataEntrega,
        hora_entrega: horaEntrega,
        itens,
      });
      await buscarPedidos();
    } catch (erroApi) {
      mostrarFeedback(ticketFeedback, erroApi.message, "erro");
      definirCarregando(botao, false);
    }
  }

  function formatarMoeda(valor) {
    return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function formatarDataBr(dataIso) {
    const [ano, mes, dia] = dataIso.split("-");
    return `${dia}/${mes}/${ano}`;
  }
});
