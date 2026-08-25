/*
 * Controlador de abas — Incremento 9.
 *
 * Unifica as 4 telas (Clientes, Produtos, Novo Pedido, Pedidos) em uma
 * única página: troca a seção visível sem recarregar e avisa o script de
 * cada tela via evento customizado `tela:ativada`, para recarregar dados
 * que podem ter mudado em outra aba (ex.: cliente cadastrado enquanto o
 * atendente já estava com a aba "Novo Pedido" aberta).
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
  // A aba inicial (Clientes) já nasce visível no HTML — cada script de tela
  // faz sua própria carga inicial no DOMContentLoaded, sem precisar de um
  // "ativarTela" disparado daqui.
});
