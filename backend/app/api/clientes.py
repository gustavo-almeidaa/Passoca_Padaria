"""Endpoints de Cliente — RF01 (cadastrar cliente) e histórico por cliente
(Incremento 24)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.api.deps import PERFIS_BALCAO, exigir_perfis, get_usuario_atual
from app.core.database import get_db
from app.models.cliente import Cliente
from app.models.pedido import Pedido
from app.schemas.cliente import ClienteCreate, ClienteRead
from app.schemas.pedido import PedidoRead

# Incremento 12: exige login em qualquer rota de cliente. Incremento 19
# (A-03): cadastrar cliente é operação de balcão — padeiro não faz (só
# lê). As rotas GET continuam abertas a qualquer perfil autenticado.
router = APIRouter(
    prefix="/clientes", tags=["clientes"], dependencies=[Depends(get_usuario_atual)]
)


@router.post(
    "",
    response_model=ClienteRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_perfis(*PERFIS_BALCAO, acao="cadastrar clientes"))],
)
def criar_cliente(payload: ClienteCreate, db: Session = Depends(get_db)) -> Cliente:
    cliente = Cliente(
        nome=payload.nome, telefone=payload.telefone, endereco=payload.endereco
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.get("", response_model=list[ClienteRead])
def listar_clientes(db: Session = Depends(get_db)) -> list[Cliente]:
    return db.query(Cliente).order_by(Cliente.nome).all()


@router.get("/{cliente_id}", response_model=ClienteRead)
def obter_cliente(cliente_id: int, db: Session = Depends(get_db)) -> Cliente:
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return cliente


@router.get("/{cliente_id}/pedidos", response_model=list[PedidoRead])
def historico_de_pedidos(cliente_id: int, db: Session = Depends(get_db)) -> list[Pedido]:
    """Todos os pedidos de um cliente (qualquer status, inclusive
    cancelados — é histórico), do mais recente pro mais antigo por data de
    entrega. Incremento 24. Leitura, aberta a qualquer perfil autenticado.
    """
    if db.get(Cliente, cliente_id) is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    return (
        db.query(Pedido)
        .options(selectinload(Pedido.itens))
        .filter(Pedido.cliente_id == cliente_id)
        .order_by(Pedido.data_entrega.desc(), Pedido.id.desc())
        .all()
    )
