"""Endpoints de Cliente — RF01 (cadastrar cliente)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual
from app.core.database import get_db
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate, ClienteRead

# Incremento 12: exige login pra qualquer rota de cliente — sem restrição
# por perfil ainda (CLAUDE.md, seção 11).
router = APIRouter(
    prefix="/clientes", tags=["clientes"], dependencies=[Depends(get_usuario_atual)]
)


@router.post("", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
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
