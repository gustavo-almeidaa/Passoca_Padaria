/*
 * Página de login (Incremento 25) — arquivo próprio, separado do app.
 *
 * Se já existe sessão, manda direto pro app. No submit, autentica e
 * navega pra "/" — a partir daí é o index.html / auth.js que assume.
 */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-login");
  const feedback = document.getElementById("feedback-login");
  const botaoEntrar = document.getElementById("botao-entrar");
  const inputEmail = document.getElementById("lg-email");
  const inputSenha = document.getElementById("lg-senha");

  // Já logado? Não faz sentido ver a tela de login.
  api
    .me()
    .then(() => window.location.replace("/"))
    .catch(() => {
      /* sem sessão — fica na tela de login mesmo */
    });

  form.addEventListener("submit", async (evento) => {
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
      await api.login(email, senha);
      window.location.replace("/");
    } catch (erro) {
      mostrarFeedback(feedback, erro.message, "erro");
      definirCarregando(botaoEntrar, false);
    }
  });
});
