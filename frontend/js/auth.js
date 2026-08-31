/*
 * Sessão do app — Incrementos 12 e 25.
 *
 * Incremento 25: login virou página própria (login.html). Aqui o app só
 * confirma que existe sessão (GET /auth/me); se não existe, redireciona
 * para /login. Sem sessão, o app nunca aparece.
 */
document.addEventListener("DOMContentLoaded", () => {
  const telaCarregando = document.getElementById("tela-carregando");
  const appShell = document.getElementById("app-shell");
  const usuarioInfo = document.getElementById("usuario-info");
  const botaoSair = document.getElementById("botao-sair");

  const ROTULOS_PERFIL = {
    proprietaria: "Proprietária",
    atendente: "Atendente",
    padeiro: "Padeiro(a)",
  };

  verificarSessao();

  async function verificarSessao() {
    try {
      const usuario = await api.me();
      mostrarApp(usuario);
    } catch (_erro) {
      irParaLogin();
    }
  }

  function irParaLogin() {
    window.usuarioAtual = null;
    window.location.replace("/login");
  }

  function mostrarApp(usuario) {
    window.usuarioAtual = usuario;
    aplicarPermissoes(usuario.perfil);

    const perfil = ROTULOS_PERFIL[usuario.perfil] || usuario.perfil;
    usuarioInfo.textContent = `Olá, ${usuario.nome} (${perfil})`;

    telaCarregando.hidden = true;
    appShell.hidden = false;

    if (window.ativarTela) window.ativarTela("clientes");
  }

  /*
   * Gate de permissão no frontend — Incrementos 15/18/20, endurecido no 25.
   * Espelha a matriz do backend (api/deps.py::exigir_perfis, A-03). NÃO é
   * controle de segurança (o backend é) — é remover da tela o que o perfil
   * não pode usar, pra não haver caminho até um botão que daria 403.
   *
   * Incremento 25: em vez de só esconder (`hidden`), **remove do DOM** as
   * abas/seções e formulários que o perfil não acessa. Não sobra tela
   * fantasma pra alcançar por devtools ou por `ativarTela(...)`.
   *
   *  - proprietária: tudo.
   *  - atendente: tudo, menos "Usuários" e "Auditoria".
   *  - padeiro: só leitura + avançar status. Sem "Novo Pedido",
   *    "Usuários", "Auditoria", nem os formulários de cadastro de
   *    cliente/produto (as listas continuam).
   */
  function aplicarPermissoes(perfil) {
    const removidos = [];

    if (perfil !== "proprietaria") {
      removidos.push("usuarios", "auditoria");
    }
    if (perfil === "padeiro") {
      removidos.push("pedido");
    }

    removidos.forEach((nome) => {
      remover(`[data-tab-alvo="${nome}"]`);
      remover(`[data-secao="${nome}"]`);
    });

    if (perfil === "padeiro") {
      remover("#card-cadastro-cliente");
      remover("#card-cadastro-produto");
    }
  }

  function remover(seletor) {
    const el = document.querySelector(seletor);
    if (el) el.remove();
  }

  botaoSair.addEventListener("click", async () => {
    try {
      await api.logout();
    } catch (_erro) {
      // Erro de rede no logout não deve prender o usuário — vai pro login
      // do mesmo jeito.
    }
    irParaLogin();
  });

  // api.js dispara isso quando qualquer chamada volta 401 (sessão expirou
  // no meio do uso).
  document.addEventListener("auth:necessaria", irParaLogin);
});
