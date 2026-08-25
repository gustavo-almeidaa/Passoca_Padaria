/*
 * Tela de Novo Pedido — RF03 (registrar pedido) e RF04 (definir entrega).
 *
 * RN01 (antecedência mínima de 24h) é replicada aqui como feedback imediato
 * (CLAUDE.md, seção 1.4) comparando data+hora de entrega com "agora + 24h".
 * A validação que vale de verdade é a do backend (app/services/pedidos.py).
 *
 * A lista "últimos pedidos registrados" no fim da tela é só uma conveniência
 * de sessão (array em memória, se perde ao recarregar a página) — não é a
 * listagem por período do RF07, que é a aba "Pedidos" (lista-pedidos.js).
 */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-pedido");
  const feedback = document.getElementById("feedback-pedido");
  const botaoSalvar = document.getElementById("botao-salvar-pedido");
  const selectCliente = document.getElementById("pe-cliente");
  const itensContainer = document.getElementById("itens-pedido");
  const botaoAddItem = document.getElementById("botao-add-item");
  const avisoPersonalizavel = document.getElementById("aviso-personalizavel");
  const inputData = document.getElementById("pe-data");
  const inputHora = document.getElementById("pe-hora");
  const totalEl = document.getElementById("pe-total");
  const listaRecentes = document.getElementById("lista-pedidos-recentes");

  const ROTULOS_UNIDADE = { unidade: "unidade", kg: "kg", duzia: "dúzia", cento: "cento" };
  const ROTULOS_STATUS = {
    recebido: "Recebido",
    em_producao: "Em produção",
    pronto: "Pronto",
    entregue: "Entregue",
    cancelado: "Cancelado",
  };

  let clientesDisponiveis = [];
  let produtosDisponiveis = [];
  const pedidosRecentes = [];

  // Bloqueia datas passadas de cara; o cálculo fino de 24h (que também
  // depende do horário escolhido) é feito no submit.
  inputData.min = new Date().toISOString().slice(0, 10);

  inicializar();

  // Incremento 9: a tela agora é uma seção da página única — ao voltar pra
  // essa aba, recarrega clientes/produtos (podem ter sido cadastrados nas
  // outras abas nesse meio tempo) sem perder o que o atendente já tinha
  // preenchido no formulário.
  document.addEventListener("tela:ativada", (evento) => {
    if (evento.detail.tela === "pedido") inicializar();
  });

  async function inicializar() {
    definirCarregando(botaoSalvar, true, "Carregando...");
    try {
      const [clientes, produtos] = await Promise.all([
        api.listarClientes(),
        api.listarProdutos({ ativo: true }),
      ]);

      const clienteSelecionadoAntes = selectCliente.value;
      clientesDisponiveis = clientes;
      popularSelectCliente();
      if (
        clienteSelecionadoAntes &&
        clientesDisponiveis.some((c) => String(c.id) === clienteSelecionadoAntes)
      ) {
        selectCliente.value = clienteSelecionadoAntes;
      }

      produtosDisponiveis = produtos;
      atualizarOpcoesProdutoNasLinhas();

      if (clientesDisponiveis.length === 0) {
        mostrarFeedback(
          feedback,
          "Nenhum cliente cadastrado ainda. Cadastre um cliente antes de criar um pedido.",
          "aviso"
        );
      } else if (produtosDisponiveis.length === 0) {
        mostrarFeedback(
          feedback,
          "Nenhum produto cadastrado ainda. Cadastre um produto antes de criar um pedido.",
          "aviso"
        );
      } else {
        limparFeedback(feedback);
      }

      // Só adiciona a linha inicial se a tela ainda não tinha nenhuma —
      // recarregar dados (ex.: voltando de outra aba) não deve duplicar
      // itens que o atendente já estava montando.
      if (itensContainer.children.length === 0) adicionarLinhaItem();
    } catch (erro) {
      mostrarFeedback(feedback, erro.message, "erro");
    } finally {
      definirCarregando(botaoSalvar, false);
    }
  }

  function podeMontarPedido() {
    return clientesDisponiveis.length > 0 && produtosDisponiveis.length > 0;
  }

  function popularSelectCliente() {
    selectCliente.innerHTML =
      '<option value="" selected disabled>Selecione o cliente</option>' +
      clientesDisponiveis
        .map(
          (c) =>
            `<option value="${c.id}">${escapeHtml(c.nome)} · ${escapeHtml(c.telefone)}</option>`
        )
        .join("");
  }

  function construirOpcoesProduto() {
    return (
      '<option value="" selected disabled>Selecione o produto</option>' +
      produtosDisponiveis
        .map(
          (p) =>
            `<option value="${p.id}" data-preco="${p.preco}" data-personalizavel="${p.personalizavel}">${escapeHtml(p.nome)} — ${formatarMoeda(p.preco)}/${ROTULOS_UNIDADE[p.unidade] || escapeHtml(p.unidade)}</option>`
        )
        .join("")
    );
  }

  // Atualiza as opções de produto das linhas já existentes (ex.: um produto
  // novo cadastrado em outra aba) sem perder o item já selecionado em cada
  // linha, quando ele continuar disponível.
  function atualizarOpcoesProdutoNasLinhas() {
    itensContainer.querySelectorAll(".item-produto").forEach((select) => {
      const valorAtual = select.value;
      select.innerHTML = construirOpcoesProduto();
      if (valorAtual && produtosDisponiveis.some((p) => String(p.id) === valorAtual)) {
        select.value = valorAtual;
      }
    });
    atualizarTotais();
  }

  function adicionarLinhaItem() {
    if (!podeMontarPedido()) return;

    const linha = document.createElement("div");
    linha.className = "item-pedido-row";
    linha.innerHTML = `
      <select class="item-produto">${construirOpcoesProduto()}</select>
      <input class="item-quantidade" type="number" min="1" step="1" value="1" aria-label="Quantidade">
      <span class="item-subtotal">${formatarMoeda(0)}</span>
      <button type="button" class="item-remover" aria-label="Remover item">✕</button>
    `;
    itensContainer.appendChild(linha);

    linha.querySelector(".item-produto").addEventListener("change", atualizarTotais);
    linha.querySelector(".item-quantidade").addEventListener("input", atualizarTotais);
    linha.querySelector(".item-remover").addEventListener("click", () => {
      if (itensContainer.children.length > 1) {
        linha.remove();
        atualizarTotais();
      }
    });

    atualizarTotais();
  }

  botaoAddItem.addEventListener("click", adicionarLinhaItem);

  function atualizarTotais() {
    let total = 0;
    let temPersonalizavel = false;
    itensContainer.querySelectorAll(".item-pedido-row").forEach((linha) => {
      const opcao = linha.querySelector(".item-produto").selectedOptions[0];
      const quantidade = Math.max(0, Number(linha.querySelector(".item-quantidade").value) || 0);
      const preco = opcao ? Number(opcao.dataset.preco || 0) : 0;
      const subtotal = preco * quantidade;
      linha.querySelector(".item-subtotal").textContent = formatarMoeda(subtotal);
      total += subtotal;
      if (opcao && opcao.dataset.personalizavel === "true") {
        temPersonalizavel = true;
      }
    });
    totalEl.textContent = formatarMoeda(total);
    avisoPersonalizavel.hidden = !temPersonalizavel;
  }

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limparFeedback(feedback);

    const clienteId = selectCliente.value;
    if (!clienteId) {
      mostrarFeedback(feedback, "Selecione o cliente do pedido.", "erro");
      return;
    }

    const linhas = Array.from(itensContainer.querySelectorAll(".item-pedido-row"));
    const itens = [];
    for (const linha of linhas) {
      const produtoId = linha.querySelector(".item-produto").value;
      const quantidade = Number(linha.querySelector(".item-quantidade").value);
      if (!produtoId) {
        mostrarFeedback(feedback, "Selecione o produto em todos os itens do pedido.", "erro");
        return;
      }
      if (!Number.isInteger(quantidade) || quantidade <= 0) {
        mostrarFeedback(
          feedback,
          "A quantidade de cada item precisa ser um número inteiro maior que zero.",
          "erro"
        );
        return;
      }
      itens.push({ produto_id: Number(produtoId), quantidade });
    }

    const dataEntrega = inputData.value;
    const horaEntrega = inputHora.value;
    if (!dataEntrega || !horaEntrega) {
      mostrarFeedback(feedback, "Informe a data e o horário de entrega.", "erro");
      return;
    }

    const momentoEntrega = new Date(`${dataEntrega}T${horaEntrega}`);
    const antecedenciaMinima = new Date(Date.now() + 24 * 60 * 60 * 1000);
    if (Number.isNaN(momentoEntrega.getTime()) || momentoEntrega < antecedenciaMinima) {
      mostrarFeedback(
        feedback,
        "Escolha uma data e horário de entrega com pelo menos 24h de antecedência.",
        "erro"
      );
      return;
    }

    definirCarregando(botaoSalvar, true);
    try {
      const pedido = await api.criarPedido({
        cliente_id: Number(clienteId),
        data_entrega: dataEntrega,
        hora_entrega: horaEntrega,
        itens,
      });
      registrarPedidoRecente(pedido);
      form.reset();
      itensContainer.innerHTML = "";
      adicionarLinhaItem();
      avisoPersonalizavel.hidden = true;
      inputData.min = new Date().toISOString().slice(0, 10);
      mostrarFeedback(feedback, `Pedido #${pedido.id} registrado com sucesso.`, "sucesso");
    } catch (erro) {
      mostrarFeedback(feedback, erro.message, "erro");
    } finally {
      definirCarregando(botaoSalvar, false);
    }
  });

  function registrarPedidoRecente(pedido) {
    pedidosRecentes.unshift(pedido);
    renderPedidosRecentes();
  }

  function renderPedidosRecentes() {
    if (pedidosRecentes.length === 0) {
      listaRecentes.innerHTML =
        '<p class="empty">Nenhum pedido registrado ainda nesta sessão.</p>';
      return;
    }
    listaRecentes.innerHTML = pedidosRecentes
      .map((pedido) => {
        const cliente = clientesDisponiveis.find((c) => c.id === pedido.cliente_id);
        const nomeCliente = cliente ? cliente.nome : `cliente #${pedido.cliente_id}`;
        const totalPedido = pedido.itens.reduce(
          (soma, item) => soma + Number(item.preco_unitario) * item.quantidade,
          0
        );
        const qtdItens = pedido.itens.length;
        return `
          <div class="produto-item">
            <div class="produto-item__principal">
              <b>Pedido #${pedido.id} — ${escapeHtml(nomeCliente)}</b>
              <span class="produto-item__preco">${formatarMoeda(totalPedido)}</span>
            </div>
            <div class="produto-item__meta">
              Entrega em ${formatarDataBr(pedido.data_entrega)} às ${pedido.hora_entrega.slice(0, 5)}
              · ${qtdItens} ite${qtdItens === 1 ? "m" : "ns"}
              · status: ${ROTULOS_STATUS[pedido.status] || pedido.status}
            </div>
          </div>`;
      })
      .join("");
  }

  function formatarMoeda(valor) {
    return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function formatarDataBr(dataIso) {
    const [ano, mes, dia] = dataIso.split("-");
    return `${dia}/${mes}/${ano}`;
  }
});
