/*
 * Controlador de abas — Incremento 9.
 *
 * Troca a seção visível sem recarregar e avisa o script de cada tela via
 * evento `tela:ativada`, para recarregar dados que podem ter mudado em
 * outra aba.
 *
 * Incremento 12: as telas não carregam nada sozinhas — a primeira carga só
 * acontece quando auth.js confirma a sessão e chama `ativarTela(...)`.
 *
 * Incremento 25: `ativarTela` re-consulta o DOM a cada chamada e recusa
 * navegar para uma aba que não existe — auth.js remove do DOM as abas que
 * o perfil não pode acessar, então pedir por uma delas cai na primeira
 * aba disponível, não numa tela vazia.
 */
document.addEventListener("DOMContentLoaded", () => {
  function ativarTela(nome) {
    const tabs = [...document.querySelectorAll("[data-tab-alvo]")];
    const secoes = [...document.querySelectorAll("[data-secao]")];
    if (tabs.length === 0) return;

    const existe = tabs.some((t) => t.dataset.tabAlvo === nome);
    const alvo = existe ? nome : tabs[0].dataset.tabAlvo;

    tabs.forEach((t) => t.classList.toggle("active", t.dataset.tabAlvo === alvo));
    secoes.forEach((secao) => {
      secao.hidden = secao.dataset.secao !== alvo;
    });
    document.dispatchEvent(
      new CustomEvent("tela:ativada", { detail: { tela: alvo } })
    );
  }

  document.querySelectorAll("[data-tab-alvo]").forEach((tab) => {
    tab.addEventListener("click", () => ativarTela(tab.dataset.tabAlvo));
  });

  window.ativarTela = ativarTela;
});
