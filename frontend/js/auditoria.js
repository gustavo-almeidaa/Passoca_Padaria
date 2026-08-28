/*
 * Tela de Auditoria — Incremento 20 (frontend do achado A-01).
 *
 * Só a proprietária chega aqui: a aba fica escondida pros outros perfis
 * (frontend/js/auth.js) e o backend também barra `GET /auditoria` com 403
 * (Incremento 18). É leitura pura da trilha gravada por
 * app/services/auditoria.py.
 *
 * Os horários vêm sem fuso do backend (datetime naive) — são exibidos como
 * "horário do servidor", sem conversão. A ordem relativa é o que importa
 * pra investigar.
 */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-auditoria");
  const selectEntidade = document.getElementById("a-entidade");
  const inputInicio = document.getElementById("a-data-inicio");
  const inputFim = document.getElementById("a-data-fim");
  const botaoBuscar = document.getElementById("botao-buscar-auditoria");
  const feedback = document.getElementById("feedback-auditoria");
  const lista = document.getElementById("lista-auditoria");

  const LIMITE = 100;

  const ROTULO_ACAO = {
    criar: "criou",
    editar: "editou",
    cancelar: "cancelou",
    avancar_status: "avançou o status",
    confirmar_sinal: "confirmou o sinal",
    desativar: "desativou",
    trocar_senha: "trocou a senha",
  };
  const ROTULO_ENTIDADE = {
    pedido: "pedido",
    produto: "produto",
    usuario: "usuário",
  };
  const ROTULO_PERFIL = {
    proprietaria: "proprietária",
    atendente: "atendente",
    padeiro: "padeiro(a)",
  };

  document.addEventListener("tela:ativada", (evento) => {
    if (evento.detail.tela === "auditoria") buscar();
  });

  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    buscar();
  });

  async function buscar() {
    limparFeedback(feedback);
    definirCarregando(botaoBuscar, true, "Buscando...");
    lista.innerHTML = '<p class="empty">Carregando…</p>';
    try {
      const eventos = await api.listarAuditoria({
        entidade: selectEntidade.value || undefined,
        data_inicio: inputInicio.value || undefined,
        data_fim: inputFim.value || undefined,
        limite: LIMITE,
      });
      render(eventos);
    } catch (erro) {
      lista.innerHTML = "";
      mostrarFeedback(feedback, erro.message, "erro");
    } finally {
      definirCarregando(botaoBuscar, false);
    }
  }

  function render(eventos) {
    if (eventos.length === 0) {
      lista.innerHTML = '<p class="empty">Nenhum evento nesse filtro.</p>';
      return;
    }
    const aviso =
      eventos.length >= LIMITE
        ? `<p class="sub">Mostrando os ${LIMITE} eventos mais recentes — refine o filtro pra ver outros.</p>`
        : "";
    lista.innerHTML = aviso + eventos.map(montarLinha).join("");
  }

  function montarLinha(ev) {
    const quando = formatarDataHora(ev.criado_em);
    const perfil = ROTULO_PERFIL[ev.usuario_perfil] || escapeHtml(ev.usuario_perfil);
    const quem = `${escapeHtml(ev.usuario_email)} (${perfil})`;
    const acao = ROTULO_ACAO[ev.acao] || escapeHtml(ev.acao);
    const entidade = ROTULO_ENTIDADE[ev.entidade] || escapeHtml(ev.entidade);
    const mudanca = montarMudanca(ev.estado_anterior, ev.estado_posterior);

    return `
      <div class="produto-item">
        <div class="produto-item__principal">
          <b>${quem}</b>
          <span class="produto-item__preco">${quando}</span>
        </div>
        <div class="produto-item__meta">${acao} · ${entidade} #${ev.entidade_id}</div>
        ${mudanca ? `<div class="auditoria__mudanca">${mudanca}</div>` : ""}
      </div>`;
  }

  function montarMudanca(antes, depois) {
    if (!depois) return "";
    if (!antes) {
      // Criação: lista os campos preenchidos, escondendo os "vazios"
      // (false/nulo) que só fariam ruído.
      return Object.entries(depois)
        .filter(([, valor]) => valor !== false && valor !== null && valor !== undefined)
        .map(([campo, valor]) => `${escapeHtml(campo)}: <b>${formatarValor(valor)}</b>`)
        .join(" · ");
    }
    // Edição: só os campos que mudaram.
    const alteracoes = Object.keys(depois)
      .filter((campo) => JSON.stringify(antes[campo]) !== JSON.stringify(depois[campo]))
      .map(
        (campo) =>
          `${escapeHtml(campo)}: ${formatarValor(antes[campo])} → <b>${formatarValor(depois[campo])}</b>`
      );
    return alteracoes.join(" · ");
  }

  function formatarValor(valor) {
    if (valor === null || valor === undefined) return "—";
    if (Array.isArray(valor)) {
      return `${valor.length} ${valor.length === 1 ? "item" : "itens"}`;
    }
    if (typeof valor === "object") return escapeHtml(JSON.stringify(valor));
    return escapeHtml(String(valor));
  }

  function formatarDataHora(iso) {
    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) return escapeHtml(String(iso));
    return data.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  }
});
