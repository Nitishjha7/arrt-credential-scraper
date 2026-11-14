"""Use a stable person_key for de-duplication; store detail_key as TEXT.

Found during recon: the site's details key is an encrypted token of
~263 characters (too long for VARCHAR(255)), and it can change between
searches, so it can't identify a person. We now de-duplicate on
person_key = sha1(name|city|state|credential) instead.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("credentials", "detail_key")   # also drops its unique index
    op.add_column("credentials", sa.Column("person_key", sa.String(64), nullable=False))
    op.create_unique_constraint("uq_credentials_person_key", "credentials", ["person_key"])
    op.add_column("credentials", sa.Column("detail_key", sa.Text))


def downgrade() -> None:
    op.drop_column("credentials", "detail_key")
    op.drop_constraint("uq_credentials_person_key", "credentials", type_="unique")
    op.drop_column("credentials", "person_key")
    op.add_column("credentials", sa.Column("detail_key", sa.String(255), nullable=False, unique=True))
