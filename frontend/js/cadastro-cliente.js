/* Tela de Cadastro de Cliente — RF01. */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-cliente");
  const feedback = document.getElementById("feedback-cliente");
  const botaoSalvar = document.getElementById("botao-salvar-cliente");
  const inputNome = document.getElementById("c-nome");
  const inputTelefone = document.getElementById("c-telefone");
  const inputEndereco = document.getElementById("c-endereco");
  const listaClientes = document.getElementById("lista-clientes");
  const historicoEl = document.getElementById("historico-cliente");

  const ROTULOS_STATUS = {
    recebido: "Recebido",
    em_producao: "Em produção",
    pronto: "Pronto",
    entregue: "Entregue",
    cancelado: "Cancelado",
  };

  // Incremento 15: máscara (43) 99999-9999 conforme digita.
  inputTelefone.addEventListener("input", () => {
    inputTelefone.value = formatarTelefone(inputTelefone.value);
  });

  // Incremento 9: a tela agora é uma seção da página única — recarrega a
  // lista sempre que o atendente volta pra essa aba, pra pegar clientes
  // cadastrados enquanto ele estava em outra tela. Incremento 12: não tem
  // mais carga eager aqui — a primeira carga só acontece quando auth.js
  // confirma a sessão e ativa esta aba (login obrigatório agora).
  document.addEventListener("tela:ativada", (evento) => {
    if (evento.detail.tela === "clientes") carregarClientes();
  });

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limparFeedback(feedback);

    const nome = inputNome.value.trim();
    const telefone = inputTelefone.value.trim();
    const endereco = inputEndereco.value.trim();
    if (!nome || !telefone) {
      mostrarFeedback(feedback, "Preencha nome e telefone do cliente.", "erro");
      return;
    }

    definirCarregando(botaoSalvar, true);
    try {
      await api.criarCliente({ nome, telefone, endereco: endereco || undefined });
      form.reset();
      mostrarFeedback(feedback, "Cliente salvo com sucesso.", "sucesso");
      inputNome.focus();
      await carregarClientes();
    } catch (erro) {
      mostrarFeedback(feedback, erro.message, "erro");
    } finally {
      definirCarregando(botaoSalvar, false);
    }
  });

  async function carregarClientes() {
    listaClientes.innerHTML = '<p class="empty">Carregando…</p>';
    fecharHistorico();
    try {
      const clientes = await api.listarClientes();
      renderClientes(clientes);
    } catch (erro) {
      listaClientes.innerHTML = "";
      mostrarFeedback(feedback, erro.message, "erro");
    }
  }

  function renderClientes(clientes) {
    if (clientes.length === 0) {
      listaClientes.innerHTML = '<p class="empty">Nenhum cliente cadastrado ainda.</p>';
      return;
    }
    listaClientes.innerHTML = clientes
      .map((c) => {
        const endereco = c.endereco ? ` · ${escapeHtml(c.endereco)}` : "";
        return `<span class="chip">
          <b>${escapeHtml(c.nome)}</b> · ${escapeHtml(c.telefone)}${endereco}
          <button type="button" class="link-button link-button--dark"
            data-ver-pedidos="${c.id}" data-nome="${escapeHtml(c.nome)}">pedidos</button>
        </span>`;
      })
      .join("");

    listaClientes.querySelectorAll("[data-ver-pedidos]").forEach((botao) => {
      botao.addEventListener("click", () =>
        verHistorico(Number(botao.dataset.verPedidos), botao.dataset.nome)
      );
    });
  }

  // --- Histórico de pedidos por cliente (Incremento 24) ------------------

  function fecharHistorico() {
    historicoEl.hidden = true;
    historicoEl.innerHTML = "";
  }

  async function verHistorico(clienteId, nome) {
    historicoEl.hidden = false;
    historicoEl.innerHTML = '<p class="empty">Carregando…</p>';
    historicoEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
    try {
      const pedidos = await api.historicoPedidosCliente(clienteId);
      renderHistorico(nome, pedidos);
    } catch (erro) {
      historicoEl.innerHTML = "";
      mostrarFeedback(feedback, erro.message, "erro");
    }
  }

  function renderHistorico(nome, pedidos) {
    // "Total já encomendado" = pedidos não cancelados (decisão do usuário,
    // 2026-08-27) — um pedido cancelado não foi encomenda de verdade.
    const validos = pedidos.filter((p) => p.status !== "cancelado");
    const totalGasto = validos.reduce(
      (soma, pedido) =>
        soma +
        pedido.itens.reduce(
          (s, item) => s + Number(item.preco_unitario) * item.quantidade,
          0
        ),
      0
    );

    const cabecalho = `
      <div class="historico__topo">
        <b>Histórico de ${escapeHtml(nome)}</b>
        <button type="button" class="link-button link-button--dark" id="fechar-historico">Fechar</button>
      </div>
      <p class="sub">
        ${validos.length} pedido${validos.length === 1 ? "" : "s"} ·
        total já encomendado: <b>${formatarMoeda(totalGasto)}</b>
        ${pedidos.length > validos.length ? ` · (${pedidos.length - validos.length} cancelado(s))` : ""}
      </p>`;

    const linhas =
      pedidos.length === 0
        ? '<p class="empty">Esse cliente ainda não fez nenhum pedido.</p>'
        : pedidos
            .map((pedido) => {
              const total = pedido.itens.reduce(
                (s, item) => s + Number(item.preco_unitario) * item.quantidade,
                0
              );
              const qtd = pedido.itens.length;
              return `
                <div class="produto-item">
                  <div class="produto-item__principal">
                    <b>Pedido #${pedido.id}</b>
                    <span class="badge badge--${pedido.status}">${
                      ROTULOS_STATUS[pedido.status] || pedido.status
                    }</span>
                  </div>
                  <div class="produto-item__meta">
                    Entrega em ${formatarDataBr(pedido.data_entrega)} às ${pedido.hora_entrega.slice(0, 5)}
                    · ${qtd} ite${qtd === 1 ? "m" : "ns"} · ${formatarMoeda(total)}
                  </div>
                </div>`;
            })
            .join("");

    historicoEl.innerHTML = `${cabecalho}<div class="produto-list">${linhas}</div>`;
    historicoEl.querySelector("#fechar-historico").addEventListener("click", fecharHistorico);
  }

  function formatarMoeda(valor) {
    return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function formatarDataBr(dataIso) {
    const [ano, mes, dia] = dataIso.split("-");
    return `${dia}/${mes}/${ano}`;
  }
});
