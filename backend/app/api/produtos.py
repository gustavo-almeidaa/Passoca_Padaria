"""Endpoints de Produto — RF02 (cadastrar produto disponível para encomenda)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual
from app.core.database import get_db
from app.models.produto import Produto
from app.schemas.produto import ProdutoCreate, ProdutoRead

# Incremento 12: exige login pra qualquer rota de produto — sem restrição
# por perfil ainda (CLAUDE.md, seção 11).
router = APIRouter(
    prefix="/produtos", tags=["produtos"], dependencies=[Depends(get_usuario_atual)]
)


@router.post("", response_model=ProdutoRead, status_code=status.HTTP_201_CREATED)
def criar_produto(payload: ProdutoCreate, db: Session = Depends(get_db)) -> Produto:
    produto = Produto(**payload.model_dump())
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto


@router.get("", response_model=list[ProdutoRead])
def listar_produtos(
    ativo: Optional[bool] = Query(
        default=None, description="Filtra por produtos ativos (true) ou inativos (false)."
    ),
    db: Session = Depends(get_db),
) -> list[Produto]:
    query = db.query(Produto)
    if ativo is not None:
        query = query.filter(Produto.ativo == ativo)
    return query.order_by(Produto.nome).all()


@router.get("/{produto_id}", response_model=ProdutoRead)
def obter_produto(produto_id: int, db: Session = Depends(get_db)) -> Produto:
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return produto
