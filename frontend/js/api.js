/*
 * Cliente HTTP mínimo para a API da Padaria do Passoca.
 *
 * Sem framework e sem dependências externas (CLAUDE.md, seção 11 — stack de
 * frontend já decidida: HTML/JS simples). O frontend é servido pela própria
 * API (ver backend/app/main.py), então não há CORS a configurar nem URL
 * base para apontar — mesma origem sempre.
 */

class ApiError extends Error {
  constructor(mensagem, status) {
    super(mensagem);
    this.status = status;
  }
}

/**
 * Extrai uma mensagem em PT-BR pronta para o usuário a partir do corpo de
 * erro da API. Cobre os dois formatos possíveis:
 *  - regra de negócio / not-found: {"detail": "mensagem já pronta"}
 *  - validação de schema (Pydantic): {"detail": [{"msg": "...", ...}, ...]}
 */
function extrairMensagemErro(corpo) {
  const detail = corpo && corpo.detail;
  if (!detail) {
    return "Ocorreu um erro inesperado. Tente novamente.";
  }
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const bruta = detail[0].msg || "";
    const limpa = bruta.replace(/^Value error,\s*/i, "").trim();
    return limpa || "Verifique os dados informados.";
  }
  return "Ocorreu um erro inesperado. Tente novamente.";
}

/**
 * Chama a API e devolve o JSON de resposta. Em caso de erro (HTTP 4xx/5xx
 * ou falha de conexão), lança ApiError já com mensagem pronta para exibir.
 */
async function apiFetch(caminho, opcoes = {}) {
  let resposta;
  try {
    resposta = await fetch(caminho, {
      headers: { "Content-Type": "application/json" },
      ...opcoes,
    });
  } catch (_erroDeRede) {
    throw new ApiError(
      "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.",
      0
    );
  }

  let corpo = null;
  if (resposta.status !== 204) {
    try {
      corpo = await resposta.json();
    } catch (_semCorpo) {
      // Resposta sem corpo JSON — segue com corpo nulo.
    }
  }

  if (!resposta.ok) {
    throw new ApiError(extrairMensagemErro(corpo), resposta.status);
  }

  return corpo;
}

const api = {
  listarClientes: () => apiFetch("/clientes"),
  criarCliente: (dados) =>
    apiFetch("/clientes", { method: "POST", body: JSON.stringify(dados) }),
};
