"""Testes do helper da trilha de auditoria — Incremento 18 (A-01)."""
from decimal import Decimal

from app.models import CategoriaProduto, Produto, UnidadeProduto
from app.models.evento_auditoria import EventoAuditoria
from app.models.pedido import Pedido, StatusPedido
from app.models.usuario import PerfilUsuario, Usuario
from app.services import auditoria


def _usuario(db_session):
    u = Usuario(
        nome="Dona", email="dona@x.com", senha_hash="x",
        perfil=PerfilUsuario.PROPRIETARIA,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def test_registrar_evento_adiciona_mas_nao_commita(db_session):
    usuario = _usuario(db_session)

    auditoria.registrar_evento(
        db_session,
        usuario=usuario,
        entidade=auditoria.ENTIDADE_PRODUTO,
        entidade_id=1,
        acao="criar",
        posterior={"preco": "10.00"},
    )

    # Ainda não commitado: some se a sessão der rollback.
    db_session.rollback()
    assert db_session.query(EventoAuditoria).count() == 0


def test_registrar_evento_grava_snapshot_do_usuario(db_session):
    usuario = _usuario(db_session)

    auditoria.registrar_evento(
        db_session,
        usuario=usuario,
        entidade=auditoria.ENTIDADE_USUARIO,
        entidade_id=usuario.id,
        acao="criar",
    )
    db_session.commit()

    evento = db_session.query(EventoAuditoria).one()
    assert evento.usuario_id == usuario.id
    assert evento.usuario_email == "dona@x.com"
    assert evento.usuario_perfil == "proprietaria"


def test_snapshot_produto_serializa_decimal_e_enum(db_session):
    produto = Produto(
        nome="Bolo",
        categoria=CategoriaProduto.BOLO,
        unidade=UnidadeProduto.UNIDADE,
        preco=Decimal("12.50"),
        personalizavel=True,
        ativo=True,
    )

    snap = auditoria.snapshot_produto(produto)

    assert snap["preco"] == "12.50"  # string, não Decimal
    assert snap["categoria"] == "bolo"
    assert snap["unidade"] == "unidade"
    assert snap["personalizavel"] is True


def test_snapshot_pedido_pega_status_e_sinal():
    pedido = Pedido(status=StatusPedido.EM_PRODUCAO, sinal_confirmado=True)

    snap = auditoria.snapshot_pedido(pedido)

    assert snap == {"status": "em_producao", "sinal_confirmado": True}
