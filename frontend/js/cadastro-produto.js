/* Tela de Cadastro de Produto — RF02. */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-produto");
  const feedback = document.getElementById("feedback-produto");
  const botaoSalvar = document.getElementById("botao-salvar-produto");
  const inputNome = document.getElementById("p-nome");
  const selectCategoria = document.getElementById("p-categoria");
  const selectUnidade = document.getElementById("p-unidade");
  const inputPreco = document.getElementById("p-preco");
  const inputPersonalizavel = document.getElementById("p-personalizavel");
  const listaProdutos = document.getElementById("lista-produtos");

  const ROTULOS_CATEGORIA = {
    pao: "Pão",
    bolo: "Bolo",
    salgado: "Salgado",
    doce: "Doce",
    outro: "Outro",
  };
  const ROTULOS_UNIDADE = {
    unidade: "Unidade",
    kg: "Kg",
    duzia: "Dúzia",
    cento: "Cento",
  };

  carregarProdutos();

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limparFeedback(feedback);

    const nome = inputNome.value.trim();
    const categoria = selectCategoria.value;
    const unidade = selectUnidade.value;
    const precoTexto = inputPreco.value.trim();

    if (!nome || !categoria || !unidade || !precoTexto) {
      mostrarFeedback(feedback, "Preencha nome, categoria, unidade e preço do produto.", "erro");
      return;
    }
    const preco = Number(precoTexto);
    if (Number.isNaN(preco) || preco < 0) {
      mostrarFeedback(feedback, "Informe um preço válido (maior ou igual a zero).", "erro");
      return;
    }

    definirCarregando(botaoSalvar, true);
    try {
      await api.criarProduto({
        nome,
        categoria,
        unidade,
        preco,
        personalizavel: inputPersonalizavel.checked,
      });
      form.reset();
      mostrarFeedback(feedback, "Produto salvo com sucesso.", "sucesso");
      inputNome.focus();
      await carregarProdutos();
    } catch (erro) {
      mostrarFeedback(feedback, erro.message, "erro");
    } finally {
      definirCarregando(botaoSalvar, false);
    }
  });

  async function carregarProdutos() {
    listaProdutos.innerHTML = '<p class="empty">Carregando…</p>';
    try {
      const produtos = await api.listarProdutos();
      renderProdutos(produtos);
    } catch (erro) {
      listaProdutos.innerHTML = "";
      mostrarFeedback(feedback, erro.message, "erro");
    }
  }

  function renderProdutos(produtos) {
    if (produtos.length === 0) {
      listaProdutos.innerHTML = '<p class="empty">Nenhum produto cadastrado ainda.</p>';
      return;
    }
    listaProdutos.innerHTML = produtos
      .map((p) => {
        const preco = Number(p.preco).toLocaleString("pt-BR", {
          style: "currency",
          currency: "BRL",
        });
        const categoria = ROTULOS_CATEGORIA[p.categoria] || escapeHtml(p.categoria);
        const unidade = ROTULOS_UNIDADE[p.unidade] || escapeHtml(p.unidade);
        const selo = p.personalizavel
          ? '<span class="selo">Personalizável</span>'
          : "";
        return `
          <div class="produto-item">
            <div class="produto-item__principal">
              <b>${escapeHtml(p.nome)}</b>
              <span class="produto-item__preco">${preco}</span>
            </div>
            <div class="produto-item__meta">${categoria} · ${unidade}${selo}</div>
          </div>`;
      })
      .join("");
  }
});
