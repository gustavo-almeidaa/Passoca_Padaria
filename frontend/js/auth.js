/*
 * Autenticação — Incremento 12.
 *
 * Controla o "gate" da página: enquanto não confirma sessão válida
 * (GET /auth/me), mostra só a tela de login e mantém o resto do app
 * (#app-shell) escondido. Depois de confirmar (login novo ou sessão já
 * existente), revela o app e dispara a primeira ativação de aba — as
 * telas em si não carregam nada sozinhas mais (ver app.js).
 */
document.addEventListener("DOMContentLoaded", () => {
  const telaLogin = document.getElementById("tela-login");
  const appShell = document.getElementById("app-shell");
  const formLogin = document.getElementById("form-login");
  const feedback = document.getElementById("feedback-login");
  const botaoEntrar = document.getElementById("botao-entrar");
  const inputEmail = document.getElementById("lg-email");
  const inputSenha = document.getElementById("lg-senha");
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
      // Sem sessão válida — comportamento normal ao abrir a página sem
      // estar logado, não é um erro pra mostrar feedback nenhum aqui.
      mostrarLogin();
    }
  }

  function mostrarApp(usuario) {
    telaLogin.hidden = true;
    appShell.hidden = false;
    // Outras telas (usuarios.js) usam isso pra saber quem está logado —
    // ex.: não oferecer o botão "Desativar" na própria linha da lista.
    window.usuarioAtual = usuario;
    const perfil = ROTULOS_PERFIL[usuario.perfil] || usuario.perfil;
    usuarioInfo.textContent = `Olá, ${usuario.nome} (${perfil})`;

    // Incremento 15: a aba "Usuários" (e tudo dentro dela — cadastro,
    // trocar senha, lista) é exclusiva da proprietária — decisão do
    // usuário, "pra evitar erro ou troca indesejada". O backend já barra
    // isso com 403 de qualquer forma; esconder o botão aqui é só não
    // oferecer uma opção que ia dar erro na cara de quem não pode usar.
    const abaUsuarios = document.querySelector('[data-tab-alvo="usuarios"]');
    if (abaUsuarios) abaUsuarios.hidden = usuario.perfil !== "proprietaria";

    if (window.ativarTela) window.ativarTela("clientes");
  }

  function mostrarLogin() {
    appShell.hidden = true;
    telaLogin.hidden = false;
    window.usuarioAtual = null;
  }

  formLogin.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limparFeedback(feedback);

    const email = inputEmail.value.trim();
    const senha = inputSenha.value;
    if (!email || !senha) {
      mostrarFeedback(feedback, "Preencha e-mail e senha.", "erro");
      return;
    }

    definirCarregando(botaoEntrar, true, "Entrando...");
    try {
      const usuario = await api.login(email, senha);
      formLogin.reset();
      mostrarApp(usuario);
    } catch (erro) {
      mostrarFeedback(feedback, erro.message, "erro");
    } finally {
      definirCarregando(botaoEntrar, false);
    }
  });

  botaoSair.addEventListener("click", async () => {
    try {
      await api.logout();
    } catch (_erro) {
      // Mesmo se der erro de rede no logout, ainda assim volta pra tela de
      // login — não faz sentido deixar o atendente preso na tela travada.
    }
    mostrarLogin();
  });

  // Disparado pelo api.js quando qualquer chamada volta 401 (sessão
  // expirou no meio do uso, por exemplo). Idempotente com o catch acima —
  // não tem problema rodar mais de uma vez.
  document.addEventListener("auth:necessaria", mostrarLogin);
});
