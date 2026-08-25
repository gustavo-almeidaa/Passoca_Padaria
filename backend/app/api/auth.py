"""Endpoints de autenticação — Incremento 12.

Login/logout via sessão (cookie assinado — ver SessionMiddleware em
app/main.py), não token. `/auth/me` existe pro frontend descobrir se já
tem sessão válida ao carregar a página, sem precisar tentar uma rota de
negócio só pra checar.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual
from app.core.database import get_db
from app.core.security import hash_senha, verificar_senha
from app.models.usuario import Usuario
from app.schemas.usuario import TrocarSenhaRequest, UsuarioCreate, UsuarioLogin, UsuarioRead

router = APIRouter(prefix="/auth", tags=["auth"])

MENSAGEM_CREDENCIAIS_INVALIDAS = "E-mail ou senha incorretos."


@router.post("/login", response_model=UsuarioRead)
def login(payload: UsuarioLogin, request: Request, db: Session = Depends(get_db)) -> Usuario:
    usuario = db.query(Usuario).filter(Usuario.email == payload.email).first()
    # Mesma mensagem genérica pra e-mail inexistente e senha errada — não dar
    # pista de qual dos dois está errado (evita enumerar e-mails válidos).
    if usuario is None or not usuario.ativo or not verificar_senha(
        payload.senha, usuario.senha_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=MENSAGEM_CREDENCIAIS_INVALIDAS,
        )

    request.session.clear()
    request.session["usuario_id"] = usuario.id
    return usuario


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(request: Request) -> None:
    request.session.clear()


@router.get("/me", response_model=UsuarioRead)
def me(usuario_atual: Usuario = Depends(get_usuario_atual)) -> Usuario:
    return usuario_atual


@router.post("/trocar-senha", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def trocar_senha(
    payload: TrocarSenhaRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_usuario_atual),
) -> None:
    if not verificar_senha(payload.senha_atual, usuario_atual.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Senha atual incorreta.",
        )

    usuario_atual.senha_hash = hash_senha(payload.senha_nova)
    db.commit()


@router.get("/usuarios", response_model=list[UsuarioRead])
def listar_usuarios(
    db: Session = Depends(get_db),
    _usuario_atual: Usuario = Depends(get_usuario_atual),
) -> list[Usuario]:
    return db.query(Usuario).order_by(Usuario.nome).all()


@router.post(
    "/usuarios", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED
)
def criar_usuario(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
    # Exige login pra criar outro usuário (não é uma rota pública de
    # cadastro) — qualquer usuário autenticado pode criar outro por
    # enquanto, já que permissão diferenciada por perfil não existe ainda
    # neste incremento (ver CLAUDE.md, seção 11).
    _usuario_atual: Usuario = Depends(get_usuario_atual),
) -> Usuario:
    if db.query(Usuario).filter(Usuario.email == payload.email).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com esse e-mail.",
        )

    usuario = Usuario(
        nome=payload.nome,
        email=payload.email,
        senha_hash=hash_senha(payload.senha),
        perfil=payload.perfil,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario
