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
      // Incremento 12: sessão de login é cookie — precisa ir em toda
      // chamada, inclusive same-origin (é o default na maioria dos
      // navegadores, mas deixamos explícito).
      credentials: "same-origin",
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
    if (resposta.status === 401) {
      // Sessão ausente/expirada — avisa a tela de login pra assumir,
      // independente de qual chamada disparou isso (CLAUDE.md, seção 1.6:
      // feedback imediato de cada ação, sem deixar o atendente preso numa
      // tela travada esperando uma requisição que nunca vai funcionar).
      document.dispatchEvent(new CustomEvent("auth:necessaria"));
    }
    throw new ApiError(extrairMensagemErro(corpo), resposta.status);
  }

  return corpo;
}

const api = {
  listarClientes: () => apiFetch("/clientes"),
  criarCliente: (dados) =>
    apiFetch("/clientes", { method: "POST", body: JSON.stringify(dados) }),
  listarProdutos: (opcoes = {}) => {
    const params = new URLSearchParams();
    if (opcoes.ativo !== undefined) params.set("ativo", opcoes.ativo);
    const query = params.toString();
    return apiFetch(`/produtos${query ? `?${query}` : ""}`);
  },
  criarProduto: (dados) =>
    apiFetch("/produtos", { method: "POST", body: JSON.stringify(dados) }),
  editarProduto: (id, dados) =>
    apiFetch(`/produtos/${id}`, { method: "PUT", body: JSON.stringify(dados) }),
  criarPedido: (dados) =>
    apiFetch("/pedidos", { method: "POST", body: JSON.stringify(dados) }),
  listarPedidos: (opcoes = {}) => {
    const params = new URLSearchParams();
    if (opcoes.data_inicio) params.set("data_inicio", opcoes.data_inicio);
    if (opcoes.data_fim) params.set("data_fim", opcoes.data_fim);
    return apiFetch(`/pedidos?${params.toString()}`);
  },
  confirmarSinal: (id) => apiFetch(`/pedidos/${id}/confirmar-sinal`, { method: "POST" }),
  avancarPedido: (id) => apiFetch(`/pedidos/${id}/avancar`, { method: "POST" }),
  cancelarPedido: (id) => apiFetch(`/pedidos/${id}/cancelar`, { method: "POST" }),
  login: (email, senha) =>
    apiFetch("/auth/login", { method: "POST", body: JSON.stringify({ email, senha }) }),
  logout: () => apiFetch("/auth/logout", { method: "POST" }),
  me: () => apiFetch("/auth/me"),
  listarUsuarios: () => apiFetch("/auth/usuarios"),
  criarUsuario: (dados) =>
    apiFetch("/auth/usuarios", { method: "POST", body: JSON.stringify(dados) }),
  desativarUsuario: (id) => apiFetch(`/auth/usuarios/${id}`, { method: "DELETE" }),
  trocarSenha: (senhaAtual, senhaNova) =>
    apiFetch("/auth/trocar-senha", {
      method: "POST",
      body: JSON.stringify({ senha_atual: senhaAtual, senha_nova: senhaNova }),
    }),
};
