
"""Generic revision template for Alembic.

This template is used by alembic to create new migration files.
It defines `revision`, `down_revision`, `branch_labels` and `depends_on` and
includes `upgrade()` and `downgrade()` functions.
"""
<%from alembic import op%>
<%import sqlalchemy as sa%>
revision = '${up_revision}'
down_revision = ${repr(down_revision) if down_revision else None}
branch_labels = ${repr(branch_labels) if branch_labels else None}
depends_on = ${repr(depends_on) if depends_on else None}


def upgrade() -> None:
	${upgrades if upgrades else 'pass'}


def downgrade() -> None:
	${downgrades if downgrades else 'pass'}
