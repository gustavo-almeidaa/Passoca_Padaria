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

  inputDataInicio.value = new Date().toISOString().slice(0, 10);

  inicializar();

  // Incremento 9: a tela agora é uma seção da página única — recarrega
  // clientes/produtos de referência e refaz a busca sempre que o atendente
  // volta pra essa aba (pode ter cadastrado cliente/produto nas outras).
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

    if (pedido.status === "recebido" && temPersonalizavel && !pedido.sinal_confirmado) {
      botoes.push(
        `<button type="button" class="secondary" data-acao="confirmar-sinal" data-pedido-id="${pedido.id}">Confirmar sinal</button>`
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

    if (STATUS_CANCELAVEIS.has(pedido.status)) {
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

  function formatarMoeda(valor) {
    return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function formatarDataBr(dataIso) {
    const [ano, mes, dia] = dataIso.split("-");
    return `${dia}/${mes}/${ano}`;
  }
});
