"""adiciona limites realistas de preco e quantidade

Revision ID: 4869bc43c20b
Revises: 363ca42992ae
Create Date: 2026-08-25 14:53:20.378265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4869bc43c20b'
down_revision: Union[str, Sequence[str], None] = '363ca42992ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Alembic autogenerate não detecta CHECK constraint novo sozinho —
    # escrito à mão (teto realista, decisão do usuário em 2026-08-25).
    op.create_check_constraint(
        "ck_produtos_preco_teto", "produtos", "preco <= 999.99"
    )
    op.create_check_constraint(
        "ck_itens_pedido_quantidade_teto", "itens_pedido", "quantidade <= 999"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_itens_pedido_quantidade_teto", "itens_pedido", type_="check")
    op.drop_constraint("ck_produtos_preco_teto", "produtos", type_="check")
