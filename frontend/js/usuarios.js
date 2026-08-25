/*
 * Tela de Usuários — Incremento 12.
 *
 * Permite criar login pra atendente/padeiro além da proprietária (criada
 * automaticamente no bootstrap — ver backend/app/main.py). Qualquer
 * usuário autenticado pode criar outro por enquanto: permissão
 * diferenciada por perfil não existe ainda (CLAUDE.md, seção 11).
 */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-usuario");
  const feedback = document.getElementById("feedback-usuario");
  const botaoSalvar = document.getElementById("botao-salvar-usuario");
  const inputNome = document.getElementById("u-nome");
  const inputEmail = document.getElementById("u-email");
  const inputSenha = document.getElementById("u-senha");
  const selectPerfil = document.getElementById("u-perfil");
  const listaUsuarios = document.getElementById("lista-usuarios");

  const ROTULOS_PERFIL = {
    proprietaria: "Proprietária",
    atendente: "Atendente",
    padeiro: "Padeiro(a)",
  };

  document.addEventListener("tela:ativada", (evento) => {
    if (evento.detail.tela === "usuarios") carregarUsuarios();
  });

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limparFeedback(feedback);

    const nome = inputNome.value.trim();
    const email = inputEmail.value.trim();
    const senha = inputSenha.value;
    const perfil = selectPerfil.value;

    if (!nome || !email || !senha || !perfil) {
      mostrarFeedback(feedback, "Preencha todos os campos.", "erro");
      return;
    }
    if (senha.length < 8) {
      mostrarFeedback(feedback, "A senha precisa ter pelo menos 8 caracteres.", "erro");
      return;
    }

    definirCarregando(botaoSalvar, true);
    try {
      await api.criarUsuario({ nome, email, senha, perfil });
      form.reset();
      mostrarFeedback(feedback, "Usuário criado com sucesso.", "sucesso");
      inputNome.focus();
      await carregarUsuarios();
    } catch (erro) {
      mostrarFeedback(feedback, erro.message, "erro");
    } finally {
      definirCarregando(botaoSalvar, false);
    }
  });

  async function carregarUsuarios() {
    listaUsuarios.innerHTML = '<p class="empty">Carregando…</p>';
    try {
      const usuarios = await api.listarUsuarios();
      renderUsuarios(usuarios);
    } catch (erro) {
      listaUsuarios.innerHTML = "";
      mostrarFeedback(feedback, erro.message, "erro");
    }
  }

  function renderUsuarios(usuarios) {
    if (usuarios.length === 0) {
      listaUsuarios.innerHTML = '<p class="empty">Nenhum usuário cadastrado ainda.</p>';
      return;
    }
    listaUsuarios.innerHTML = usuarios
      .map((u) => {
        const perfil = ROTULOS_PERFIL[u.perfil] || escapeHtml(u.perfil);
        const inativo = !u.ativo ? '<span class="selo selo--inativo">Inativo</span>' : "";
        return `
          <div class="produto-item">
            <div class="produto-item__principal">
              <b>${escapeHtml(u.nome)}</b>
              <span class="produto-item__preco">${perfil}</span>
            </div>
            <div class="produto-item__meta">${escapeHtml(u.email)}${inativo}</div>
          </div>`;
      })
      .join("");
  }
});
