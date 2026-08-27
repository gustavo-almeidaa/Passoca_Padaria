"""adiciona tabela eventos_auditoria (trilha de auditoria A-01)

Revision ID: c6827515137c
Revises: b22b656b2d3f
Create Date: 2026-08-27 14:33:22.561469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6827515137c'
down_revision: Union[str, Sequence[str], None] = 'b22b656b2d3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Escrita à mão, mesmo estilo das outras migrations (feitas p/ Postgres;
    # os testes montam o schema de Base.metadata). Incremento 18 / A-01.
    op.create_table(
        "eventos_auditoria",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("usuario_email", sa.String(length=255), nullable=False),
        sa.Column("usuario_perfil", sa.String(length=20), nullable=False),
        sa.Column("entidade", sa.String(length=20), nullable=False),
        sa.Column("entidade_id", sa.Integer(), nullable=False),
        sa.Column("acao", sa.String(length=30), nullable=False),
        sa.Column("estado_anterior", sa.JSON(), nullable=True),
        sa.Column("estado_posterior", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_eventos_auditoria_criado_em",
        "eventos_auditoria",
        ["criado_em"],
        unique=False,
    )
    op.create_index(
        "ix_eventos_auditoria_entidade",
        "eventos_auditoria",
        ["entidade", "entidade_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_eventos_auditoria_entidade", table_name="eventos_auditoria")
    op.drop_index("ix_eventos_auditoria_criado_em", table_name="eventos_auditoria")
    op.drop_table("eventos_auditoria")
