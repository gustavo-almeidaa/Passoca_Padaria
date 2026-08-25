/*
 * Controlador de abas — Incremento 9.
 *
 * Unifica as telas (Clientes, Produtos, Novo Pedido, Pedidos, Usuários) em
 * uma única página: troca a seção visível sem recarregar e avisa o script
 * de cada tela via evento customizado `tela:ativada`, para recarregar
 * dados que podem ter mudado em outra aba (ex.: cliente cadastrado
 * enquanto o atendente já estava com a aba "Novo Pedido" aberta).
 *
 * Incremento 12: nenhuma tela carrega dado nenhum sozinha no
 * DOMContentLoaded mais — todas exigem login agora, então a primeira carga
 * só acontece quando auth.js confirma a sessão e chama
 * `window.ativarTela("clientes")` (ver frontend/js/auth.js).
 */
document.addEventListener("DOMContentLoaded", () => {
  const tabs = document.querySelectorAll("[data-tab-alvo]");
  const secoes = document.querySelectorAll("[data-secao]");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => ativarTela(tab.dataset.tabAlvo));
  });

  function ativarTela(nome) {
    tabs.forEach((t) => t.classList.toggle("active", t.dataset.tabAlvo === nome));
    secoes.forEach((secao) => {
      secao.hidden = secao.dataset.secao !== nome;
    });
    document.dispatchEvent(new CustomEvent("tela:ativada", { detail: { tela: nome } }));
  }

  window.ativarTela = ativarTela;
});
