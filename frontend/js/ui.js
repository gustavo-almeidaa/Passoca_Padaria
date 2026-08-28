/*
 * Helpers de feedback visual reaproveitáveis entre telas.
 *
 * RNF01 (CLAUDE.md, seção 1.6): poucos cliques, feedback imediato de cada
 * ação ("salvou", "deu erro", "processando") — centralizado aqui para as
 * telas futuras (Incrementos 6/7) usarem o mesmo padrão.
 */

const _CLASSES_FEEDBACK = ["feedback--sucesso", "feedback--erro", "feedback--aviso"];

/** Mostra uma mensagem de feedback. `tipo`: "sucesso" | "erro" | "aviso".
 *
 * Só mexe nas classes de estado (`feedback--*`) — preserva qualquer outra
 * classe no elemento (ex.: `ticket__feedback`, `login__feedback`), senão a
 * segunda chamada no mesmo elemento não conseguiria mais achá-lo pelo
 * seletor da tela. */
function mostrarFeedback(elemento, mensagem, tipo) {
  elemento.textContent = mensagem;
  elemento.classList.remove(..._CLASSES_FEEDBACK);
  elemento.classList.add("feedback", `feedback--${tipo}`);
  elemento.hidden = false;
}

function limparFeedback(elemento) {
  elemento.hidden = true;
  elemento.textContent = "";
  elemento.classList.remove(..._CLASSES_FEEDBACK);
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

/*
 * Máscaras de campo — Incremento 15.
 *
 * Formatação só de exibição/digitação (UX); a validação de verdade
 * continua no backend (CLAUDE.md, seção 1.4 — frontend nunca é fonte
 * confiável). São funções puras — quem chama decide quando aplicar
 * (normalmente num listener de "input").
 */

/** (43) 99999-9999 — telefone fixo (10 dígitos) ou celular (11), conforme
 * a quantidade de dígitos já digitada. */
function formatarTelefone(valor) {
  const digitos = (valor || "").replace(/\D/g, "").slice(0, 11);
  if (digitos.length === 0) return "";
  if (digitos.length <= 2) return `(${digitos}`;
  if (digitos.length <= 6) return `(${digitos.slice(0, 2)}) ${digitos.slice(2)}`;
  if (digitos.length <= 10) {
    return `(${digitos.slice(0, 2)}) ${digitos.slice(2, 6)}-${digitos.slice(6)}`;
  }
  return `(${digitos.slice(0, 2)}) ${digitos.slice(2, 7)}-${digitos.slice(7)}`;
}

/** Digita "4590" -> mostra "45,90" (padrão de caixa registradora — os
 * últimos 2 dígitos sempre são os centavos). Limitado a 999,99 (teto do
 * backend) pra não deixar o campo sugerir um valor que será rejeitado. */
function formatarPrecoDigitado(valor) {
  const digitos = (valor || "").replace(/\D/g, "").replace(/^0+(?=\d)/, "").slice(0, 5);
  if (digitos.length === 0) return "";
  const numero = Math.min(Number(digitos) / 100, 999.99);
  return numero.toFixed(2).replace(".", ",");
}

/** "45,90" (formato do formatarPrecoDigitado) -> 45.90 (número, pro payload da API). */
function paraNumeroDecimal(precoFormatado) {
  const normalizado = (precoFormatado || "").replace(/\./g, "").replace(",", ".");
  const numero = Number(normalizado);
  return Number.isNaN(numero) ? 0 : numero;
}
