"""adiciona tabela tentativas_login (rate limit no login)

Revision ID: b22b656b2d3f
Revises: 4869bc43c20b
Create Date: 2026-08-27 13:49:34.734760

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b22b656b2d3f'
down_revision: Union[str, Sequence[str], None] = '4869bc43c20b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Escrito à mão (mesmo estilo das outras migrations do projeto, que são
    # feitas pra PostgreSQL — o `now()` do server_default não roda em
    # SQLite; os testes montam o schema a partir de Base.metadata, não
    # daqui). Incremento 17 / auditoria A-02.
    op.create_table(
        "tentativas_login",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("sucesso", sa.Boolean(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tentativas_login_ip_criado_em",
        "tentativas_login",
        ["ip", "criado_em"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_tentativas_login_ip_criado_em", table_name="tentativas_login"
    )
    op.drop_table("tentativas_login")
