/* Tela de Cadastro de Cliente — RF01. */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-cliente");
  const feedback = document.getElementById("feedback-cliente");
  const botaoSalvar = document.getElementById("botao-salvar-cliente");
  const inputNome = document.getElementById("c-nome");
  const inputTelefone = document.getElementById("c-telefone");
  const listaClientes = document.getElementById("lista-clientes");

  carregarClientes();

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limparFeedback(feedback);

    const nome = inputNome.value.trim();
    const telefone = inputTelefone.value.trim();
    if (!nome || !telefone) {
      mostrarFeedback(feedback, "Preencha nome e telefone do cliente.", "erro");
      return;
    }

    definirCarregando(botaoSalvar, true);
    try {
      await api.criarCliente({ nome, telefone });
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
      .map(
        (c) =>
          `<span class="chip"><b>${escapeHtml(c.nome)}</b> · ${escapeHtml(c.telefone)}</span>`
      )
      .join("");
  }
});
