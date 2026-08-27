"""Endpoints de Produto — RF02 (cadastrar produto disponível para encomenda)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PERFIS_BALCAO, exigir_perfis, get_usuario_atual
from app.core.database import get_db
from app.models.produto import Produto
from app.models.usuario import Usuario
from app.schemas.produto import ProdutoCreate, ProdutoRead
from app.services import auditoria

# Incremento 12: exige login pra qualquer rota de produto. Incremento 18:
# criar/editar entram na trilha de auditoria (A-01), com atenção ao preço.
# Incremento 19 (A-03): criar/editar são operação de balcão — padeiro não
# mexe em produto (só lê). GET continua aberto a qualquer perfil.
router = APIRouter(
    prefix="/produtos", tags=["produtos"], dependencies=[Depends(get_usuario_atual)]
)


@router.post("", response_model=ProdutoRead, status_code=status.HTTP_201_CREATED)
def criar_produto(
    payload: ProdutoCreate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(*PERFIS_BALCAO, acao="cadastrar produtos")
    ),
) -> Produto:
    produto = Produto(**payload.model_dump())
    db.add(produto)
    db.flush()  # atribui produto.id para o evento de auditoria
    auditoria.registrar_evento(
        db,
        usuario=usuario_atual,
        entidade=auditoria.ENTIDADE_PRODUTO,
        entidade_id=produto.id,
        acao="criar",
        posterior=auditoria.snapshot_produto(produto),
    )
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


@router.put("/{produto_id}", response_model=ProdutoRead)
def editar_produto(
    produto_id: int,
    payload: ProdutoCreate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(*PERFIS_BALCAO, acao="editar produtos")
    ),
) -> Produto:
    """Edita um produto já cadastrado (todos os campos — decisão do
    usuário, 2026-08-25). Não afeta pedidos já feitos: `preco_unitario`
    do item é um snapshot independente (ver models/item_pedido.py).
    """
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    anterior = auditoria.snapshot_produto(produto)
    for campo, valor in payload.model_dump().items():
        setattr(produto, campo, valor)

    auditoria.registrar_evento(
        db,
        usuario=usuario_atual,
        entidade=auditoria.ENTIDADE_PRODUTO,
        entidade_id=produto.id,
        acao="editar",
        anterior=anterior,
        posterior=auditoria.snapshot_produto(produto),
    )
    db.commit()
    db.refresh(produto)
    return produto
