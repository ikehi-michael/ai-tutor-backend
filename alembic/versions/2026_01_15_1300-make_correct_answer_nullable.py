"""make_correct_answer_nullable

Revision ID: make_correct_answer_nullable
Revises: add_past_questions
Create Date: 2026-01-15 13:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'make_correct_answer_nullable'
down_revision = 'add_past_questions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make correct_answer nullable
    op.alter_column('past_questions', 'correct_answer',
                    existing_type=sa.String(),
                    nullable=True)


def downgrade() -> None:
    # Revert to NOT NULL (but this might fail if there are null values)
    op.alter_column('past_questions', 'correct_answer',
                    existing_type=sa.String(),
                    nullable=False)
