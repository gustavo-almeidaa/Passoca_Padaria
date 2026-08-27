"""Endpoints de autenticação — Incremento 12.

Login/logout via sessão (cookie assinado — ver SessionMiddleware em
app/main.py), não token. `/auth/me` existe pro frontend descobrir se já
tem sessão válida ao carregar a página, sem precisar tentar uma rota de
negócio só pra checar.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_proprietaria, get_usuario_atual, obter_ip_cliente
from app.core.database import get_db
from app.core.security import hash_senha, verificar_senha
from app.models.usuario import PerfilUsuario, Usuario
from app.schemas.usuario import TrocarSenhaRequest, UsuarioCreate, UsuarioLogin, UsuarioRead
from app.services import rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])

MENSAGEM_CREDENCIAIS_INVALIDAS = "E-mail ou senha incorretos."
MENSAGEM_MUITAS_TENTATIVAS = (
    "Muitas tentativas de login sem sucesso deste dispositivo. Espere alguns "
    "minutos e tente de novo."
)


@router.post("/login", response_model=UsuarioRead)
def login(payload: UsuarioLogin, request: Request, db: Session = Depends(get_db)) -> Usuario:
    # Limite de tentativas por IP (Incremento 17, auditoria A-02). Só o IP é
    # penalizado — a conta nunca trava (ver app/services/rate_limit.py).
    ip = obter_ip_cliente(request)
    avaliacao = rate_limit.avaliar_ip(db, ip)
    if avaliacao.bloqueado:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=MENSAGEM_MUITAS_TENTATIVAS,
            headers={"Retry-After": str(avaliacao.retry_after_segundos)},
        )
    if avaliacao.atraso_segundos:
        time.sleep(avaliacao.atraso_segundos)

    usuario = db.query(Usuario).filter(Usuario.email == payload.email).first()
    autenticado = (
        usuario is not None
        and usuario.ativo
        and verificar_senha(payload.senha, usuario.senha_hash)
    )
    rate_limit.registrar_tentativa(
        db, email=payload.email, ip=ip, sucesso=autenticado
    )

    # Mesma mensagem genérica pra e-mail inexistente e senha errada — não dar
    # pista de qual dos dois está errado (evita enumerar e-mails válidos).
    if not autenticado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=MENSAGEM_CREDENCIAIS_INVALIDAS,
        )

    db.refresh(usuario)  # registrar_tentativa commitou e expirou o objeto
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
    # Incremento 15: decisão do usuário — a aba "Usuários" inteira (com
    # tudo dentro, inclusive trocar a própria senha) fica exclusiva da
    # proprietária, "pra evitar erro ou troca indesejada". Consequência
    # aceita: atendente/padeiro não têm autoatendimento de senha — só a
    # proprietária troca (a própria ou, indiretamente, recriando a conta
    # de quem esqueceu, já que não existe reset alheio ainda).
    usuario_atual: Usuario = Depends(exigir_proprietaria),
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
    _usuario_atual: Usuario = Depends(exigir_proprietaria),
) -> list[Usuario]:
    return db.query(Usuario).order_by(Usuario.nome).all()


@router.post(
    "/usuarios", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED
)
def criar_usuario(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
    # Incremento 15: só a proprietária cria usuário (decisão do usuário).
    _usuario_atual: Usuario = Depends(exigir_proprietaria),
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


@router.delete(
    "/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def desativar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_proprietaria),
) -> None:
    """"Excluir" usuário (pedido do usuário) implementado como desativar
    (ativo=False), não apagar a linha — mais seguro e reversível, e o
    campo `ativo` já existe e já é respeitado no login (get_usuario_atual
    rejeita usuário inativo). Decisão tomada ao implementar, documentada
    no relatório do incremento — se precisar de exclusão definitiva de
    verdade, é um pedido separado.
    """
    if usuario_id == usuario_atual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode desativar a própria conta.",
        )

    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if usuario.perfil == PerfilUsuario.PROPRIETARIA:
        outras_proprietarias_ativas = (
            db.query(Usuario)
            .filter(
                Usuario.perfil == PerfilUsuario.PROPRIETARIA,
                Usuario.ativo.is_(True),
                Usuario.id != usuario_id,
            )
            .count()
        )
        if outras_proprietarias_ativas == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível desativar a única proprietária ativa.",
            )

    usuario.ativo = False
    db.commit()
