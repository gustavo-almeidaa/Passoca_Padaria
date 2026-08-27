"""Service de Pedido — RF03/RF04/RF06/RF07, aplicando RN01-RN04 no backend.

Regra de negócio crítica (CLAUDE.md, seção 1.4: "RN01-RN04 são validadas no
backend, sempre") vive aqui, fora do endpoint FastAPI, para poder ser testada
isoladamente sem precisar subir a camada HTTP.

Exceções específicas por tipo de falha (em vez de uma genérica) permitem que
a camada de API escolha o status HTTP e a mensagem certos para cada caso —
ver `app/api/pedidos.py`.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.item_pedido import ItemPedido
from app.models.pedido import TRANSICOES_VALIDAS, Pedido, StatusPedido
from app.models.produto import Produto
from app.models.usuario import Usuario
from app.schemas.pedido import PedidoCreate
from app.services import auditoria

# RN01 — antecedência mínima entre a criação do pedido e a data/hora de entrega.
ANTECEDENCIA_MINIMA = timedelta(hours=24)

# Teto realista (decisão do usuário, 2026-08-25) — evita agendar um pedido
# décadas no futuro por erro de digitação (ex.: ano trocado sem querer).
ANTECEDENCIA_MAXIMA = timedelta(days=90)

# RN03 — janela mínima antes da entrega em que o cancelamento ainda é aceito.
JANELA_CANCELAMENTO = timedelta(hours=12)

# Estados a partir dos quais RF06/RN03 permite cancelar (RN04: cancelado só é
# alcançável a partir de recebido ou em_producao).
STATUS_CANCELAVEIS = {StatusPedido.RECEBIDO, StatusPedido.EM_PRODUCAO}


class ClienteNaoEncontrado(Exception):
    """Pedido referencia um cliente que não existe no cadastro."""


class ProdutoInvalido(Exception):
    """Item do pedido referencia um produto inexistente ou indisponível."""

    def __init__(self, produto_id: int, motivo: str):
        self.produto_id = produto_id
        super().__init__(motivo)


class AntecedenciaMinimaNaoRespeitada(Exception):
    """RN01: entrega marcada com menos de 24h de antecedência."""


class AntecedenciaMaximaExcedida(Exception):
    """Entrega marcada com mais de 90 dias de antecedência (teto realista)."""


class PedidoNaoEncontrado(Exception):
    """Ação referencia um pedido que não existe."""


class SinalNaoConfirmado(Exception):
    """RN02: pedido com item personalizável tentando sair de `recebido` sem sinal."""


class TransicaoInvalida(Exception):
    """RN04: ação de avançar/cancelar não permitida no status atual do pedido."""


class ForaDaJanelaDeCancelamento(Exception):
    """RN03: cancelamento pedido a menos de 12h da entrega."""


class IntervaloDeDatasInvalido(Exception):
    """RF07: `data_fim` anterior a `data_inicio` na listagem por período."""


def criar_pedido(
    db: Session,
    payload: PedidoCreate,
    *,
    usuario: Usuario,
    agora: datetime | None = None,
) -> Pedido:
    """Cria um pedido (RF03) com data/hora de entrega (RF04), aplicando RN01.

    `agora` é injetável para permitir testes determinísticos da janela de
    24h (RN01) sem depender do relógio real da máquina que roda o teste.

    `usuario` é quem está registrando o pedido — vai para a trilha de
    auditoria (Incremento 18), no mesmo commit.
    """
    agora = agora or datetime.now()

    cliente = db.get(Cliente, payload.cliente_id)
    if cliente is None:
        raise ClienteNaoEncontrado(f"Cliente {payload.cliente_id} não encontrado.")

    momento_entrega = datetime.combine(payload.data_entrega, payload.hora_entrega)
    if momento_entrega - agora < ANTECEDENCIA_MINIMA:
        raise AntecedenciaMinimaNaoRespeitada(
            "Escolha uma data e horário de entrega com pelo menos 24h de "
            "antecedência a partir de agora."
        )
    if momento_entrega - agora > ANTECEDENCIA_MAXIMA:
        raise AntecedenciaMaximaExcedida(
            "Escolha uma data de entrega em até 90 dias a partir de hoje."
        )

    itens: list[ItemPedido] = []
    for item_in in payload.itens:
        produto = db.get(Produto, item_in.produto_id)
        if produto is None:
            raise ProdutoInvalido(
                item_in.produto_id,
                f"Produto {item_in.produto_id} não encontrado.",
            )
        if not produto.ativo:
            raise ProdutoInvalido(
                item_in.produto_id,
                f'Produto "{produto.nome}" não está mais disponível para encomenda.',
            )
        itens.append(
            ItemPedido(
                produto_id=produto.id,
                quantidade=item_in.quantidade,
                # Snapshot do preço atual — não deve mudar se o cardápio
                # for reajustado depois (ver app/models/item_pedido.py).
                preco_unitario=produto.preco,
            )
        )

    pedido = Pedido(
        cliente_id=cliente.id,
        data_entrega=payload.data_entrega,
        hora_entrega=payload.hora_entrega,
        itens=itens,
    )
    db.add(pedido)
    db.flush()  # atribui pedido.id, necessário para o evento de auditoria

    auditoria.registrar_evento(
        db,
        usuario=usuario,
        entidade=auditoria.ENTIDADE_PEDIDO,
        entidade_id=pedido.id,
        acao="criar",
        posterior={
            **auditoria.snapshot_pedido(pedido),
            "cliente_id": pedido.cliente_id,
            "data_entrega": pedido.data_entrega.isoformat(),
            "hora_entrega": pedido.hora_entrega.isoformat(),
            "itens": [
                {
                    "produto_id": item.produto_id,
                    "quantidade": item.quantidade,
                    "preco_unitario": str(item.preco_unitario),
                }
                for item in pedido.itens
            ],
        },
    )

    db.commit()
    db.refresh(pedido)
    return pedido


def _obter_pedido_ou_404(db: Session, pedido_id: int) -> Pedido:
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise PedidoNaoEncontrado(f"Pedido {pedido_id} não encontrado.")
    return pedido


def _tem_item_personalizavel(pedido: Pedido) -> bool:
    return any(item.produto.personalizavel for item in pedido.itens)


def _proximo_status_producao(atual: StatusPedido) -> StatusPedido | None:
    """Próximo passo da linha de produção (RN04), ignorando o desvio para
    `cancelado` — que é uma ação separada, ver `cancelar_pedido`.

    Deriva de `TRANSICOES_VALIDAS` (app/models/pedido.py) em vez de manter um
    mapeamento duplicado, para nunca ficar fora de sincronia com a máquina de
    estados que é a fonte da verdade.
    """
    destinos = TRANSICOES_VALIDAS.get(atual, set()) - {StatusPedido.CANCELADO}
    if not destinos:
        return None
    return next(iter(destinos))


def confirmar_sinal(db: Session, pedido_id: int, *, usuario: Usuario) -> Pedido:
    """Confirma o sinal de um pedido (RN02), liberando a saída de `recebido`
    quando há item personalizável.
    """
    pedido = _obter_pedido_ou_404(db, pedido_id)
    anterior = auditoria.snapshot_pedido(pedido)

    pedido.sinal_confirmado = True

    auditoria.registrar_evento(
        db,
        usuario=usuario,
        entidade=auditoria.ENTIDADE_PEDIDO,
        entidade_id=pedido.id,
        acao="confirmar_sinal",
        anterior=anterior,
        posterior=auditoria.snapshot_pedido(pedido),
    )
    db.commit()
    db.refresh(pedido)
    return pedido


def avancar_status(db: Session, pedido_id: int, *, usuario: Usuario) -> Pedido:
    """Avança o pedido para a próxima etapa da produção (UC04), aplicando
    RN04 (máquina de estados) e RN02 (sinal obrigatório para sair de
    `recebido` com item personalizável).
    """
    pedido = _obter_pedido_ou_404(db, pedido_id)
    anterior = auditoria.snapshot_pedido(pedido)

    proximo = _proximo_status_producao(pedido.status)
    if proximo is None:
        raise TransicaoInvalida(
            f'Pedido está em "{pedido.status.value}" e não tem próxima etapa '
            "de produção."
        )

    if (
        pedido.status == StatusPedido.RECEBIDO
        and proximo == StatusPedido.EM_PRODUCAO
        and _tem_item_personalizavel(pedido)
        and not pedido.sinal_confirmado
    ):
        raise SinalNaoConfirmado(
            "Este pedido tem item personalizado e precisa de sinal confirmado "
            "antes de iniciar a produção."
        )

    pedido.status = proximo

    auditoria.registrar_evento(
        db,
        usuario=usuario,
        entidade=auditoria.ENTIDADE_PEDIDO,
        entidade_id=pedido.id,
        acao="avancar_status",
        anterior=anterior,
        posterior=auditoria.snapshot_pedido(pedido),
    )
    db.commit()
    db.refresh(pedido)
    return pedido


def cancelar_pedido(
    db: Session, pedido_id: int, *, usuario: Usuario, agora: datetime | None = None
) -> Pedido:
    """Cancela um pedido (RF06), aplicando RN04 (só a partir de `recebido`
    ou `em_producao`) e RN03 (só até 12h antes da entrega).

    `agora` é injetável para testes determinísticos da janela de
    cancelamento, no mesmo padrão usado em `criar_pedido` para RN01.
    """
    agora = agora or datetime.now()
    pedido = _obter_pedido_ou_404(db, pedido_id)
    anterior = auditoria.snapshot_pedido(pedido)

    if pedido.status not in STATUS_CANCELAVEIS:
        raise TransicaoInvalida(
            f'Pedido em "{pedido.status.value}" não pode mais ser cancelado.'
        )

    momento_entrega = datetime.combine(pedido.data_entrega, pedido.hora_entrega)
    if momento_entrega - agora < JANELA_CANCELAMENTO:
        raise ForaDaJanelaDeCancelamento(
            "Esse pedido não pode mais ser cancelado — faltam menos de 12h "
            "para a entrega."
        )

    pedido.status = StatusPedido.CANCELADO

    auditoria.registrar_evento(
        db,
        usuario=usuario,
        entidade=auditoria.ENTIDADE_PEDIDO,
        entidade_id=pedido.id,
        acao="cancelar",
        anterior=anterior,
        posterior=auditoria.snapshot_pedido(pedido),
    )
    db.commit()
    db.refresh(pedido)
    return pedido


def listar_pedidos(
    db: Session, data_inicio: date, data_fim: date | None = None
) -> list[Pedido]:
    """Lista pedidos com entrega no período informado (RF07).

    `data_fim` é opcional — quando omitida, assume o mesmo valor de
    `data_inicio` (cobre o caso "listar por dia").
    """
    data_fim = data_fim or data_inicio
    if data_fim < data_inicio:
        raise IntervaloDeDatasInvalido(
            "A data final do período não pode ser anterior à data inicial."
        )

    return (
        db.query(Pedido)
        .filter(Pedido.data_entrega >= data_inicio, Pedido.data_entrega <= data_fim)
        .order_by(Pedido.data_entrega, Pedido.hora_entrega)
        .all()
    )
