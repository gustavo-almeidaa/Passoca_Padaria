/* Tela de Cadastro/Edição de Produto — RF02 + edição (Incremento 15). */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-produto");
  const feedback = document.getElementById("feedback-produto");
  const botaoSalvar = document.getElementById("botao-salvar-produto");
  const botaoCancelarEdicao = document.getElementById("botao-cancelar-edicao-produto");
  const tituloForm = document.getElementById("titulo-form-produto");
  const inputId = document.getElementById("p-id");
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

  let produtosCache = [];

  // Incremento 15: máscara "45,90" conforme digita (limitada ao teto de
  // R$ 999,99 do backend — ver formatarPrecoDigitado em ui.js).
  inputPreco.addEventListener("input", () => {
    inputPreco.value = formatarPrecoDigitado(inputPreco.value);
  });

  // Incremento 9: a tela agora é uma seção da página única — recarrega a
  // lista sempre que o atendente volta pra essa aba. Incremento 12: sem
  // carga eager aqui, ver nota equivalente em cadastro-cliente.js.
  document.addEventListener("tela:ativada", (evento) => {
    if (evento.detail.tela === "produtos") carregarProdutos();
  });

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
    const preco = paraNumeroDecimal(precoTexto);
    if (preco < 0) {
      mostrarFeedback(feedback, "Informe um preço válido (maior ou igual a zero).", "erro");
      return;
    }

    const dados = {
      nome,
      categoria,
      unidade,
      preco,
      personalizavel: inputPersonalizavel.checked,
    };

    const idEmEdicao = inputId.value;

    definirCarregando(botaoSalvar, true);
    try {
      if (idEmEdicao) {
        await api.editarProduto(idEmEdicao, { ...dados, ativo: true });
        mostrarFeedback(feedback, "Produto atualizado com sucesso.", "sucesso");
      } else {
        await api.criarProduto(dados);
        mostrarFeedback(feedback, "Produto salvo com sucesso.", "sucesso");
      }
      sairDoModoEdicao();
      inputNome.focus();
      await carregarProdutos();
    } catch (erro) {
      mostrarFeedback(feedback, erro.message, "erro");
    } finally {
      definirCarregando(botaoSalvar, false);
    }
  });

  botaoCancelarEdicao.addEventListener("click", () => {
    sairDoModoEdicao();
    limparFeedback(feedback);
  });

  function entrarEmModoEdicao(produto) {
    inputId.value = produto.id;
    inputNome.value = produto.nome;
    selectCategoria.value = produto.categoria;
    selectUnidade.value = produto.unidade;
    inputPreco.value = Number(produto.preco).toFixed(2).replace(".", ",");
    inputPersonalizavel.checked = produto.personalizavel;

    tituloForm.textContent = `Editando: ${produto.nome}`;
    botaoSalvar.textContent = "Salvar Alterações";
    botaoSalvar.dataset.textoOriginal = "Salvar Alterações";
    botaoCancelarEdicao.hidden = false;
    inputNome.focus();
  }

  function sairDoModoEdicao() {
    form.reset();
    inputId.value = "";
    tituloForm.textContent = "Cadastro de Produto";
    botaoSalvar.textContent = "Salvar Produto";
    botaoSalvar.dataset.textoOriginal = "Salvar Produto";
    botaoCancelarEdicao.hidden = true;
  }

  async function carregarProdutos() {
    listaProdutos.innerHTML = '<p class="empty">Carregando…</p>';
    try {
      produtosCache = await api.listarProdutos();
      renderProdutos(produtosCache);
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
        const inativo = !p.ativo ? '<span class="selo selo--inativo">Inativo</span>' : "";
        return `
          <div class="produto-item">
            <div class="produto-item__principal">
              <b>${escapeHtml(p.nome)}</b>
              <span class="produto-item__preco">${preco}</span>
            </div>
            <div class="produto-item__meta">
              ${categoria} · ${unidade}${selo}${inativo}
              <button type="button" class="link-button link-button--dark" data-editar-produto="${p.id}">Editar</button>
            </div>
          </div>`;
      })
      .join("");

    listaProdutos.querySelectorAll("[data-editar-produto]").forEach((botao) => {
      botao.addEventListener("click", () => {
        const produto = produtosCache.find((p) => p.id === Number(botao.dataset.editarProduto));
        if (produto) entrarEmModoEdicao(produto);
      });
    });
  }
});
