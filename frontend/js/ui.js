/*
 * Helpers de feedback visual reaproveitáveis entre telas.
 *
 * RNF01 (CLAUDE.md, seção 1.6): poucos cliques, feedback imediato de cada
 * ação ("salvou", "deu erro", "processando") — centralizado aqui para as
 * telas futuras (Incrementos 6/7) usarem o mesmo padrão.
 */

/** Mostra uma mensagem de feedback. `tipo`: "sucesso" | "erro". */
function mostrarFeedback(elemento, mensagem, tipo) {
  elemento.textContent = mensagem;
  elemento.className = `feedback feedback--${tipo}`;
  elemento.hidden = false;
}

function limparFeedback(elemento) {
  elemento.hidden = true;
  elemento.textContent = "";
}

/** Alterna um botão entre estado normal e "carregando" (desabilitado). */
function definirCarregando(botao, carregando, textoCarregando = "Salvando...") {
  if (carregando) {
    botao.dataset.textoOriginal = botao.dataset.textoOriginal || botao.textContent;
    botao.textContent = textoCarregando;
    botao.disabled = true;
  } else {
    botao.textContent = botao.dataset.textoOriginal || botao.textContent;
    botao.disabled = false;
  }
}

/** Escapa texto antes de injetar em innerHTML (evita XSS refletindo dados salvos). */
function escapeHtml(texto) {
  const div = document.createElement("div");
  div.textContent = texto ?? "";
  return div.innerHTML;
}
