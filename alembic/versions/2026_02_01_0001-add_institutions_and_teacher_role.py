"""add institutions table, teacher_students table, and TEACHER role

Revision ID: add_institutions
Revises: make_correct_answer_nullable
Create Date: 2026-02-01 00:01:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_institutions'
down_revision = 'make_correct_answer_nullable'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create institutions table
    op.create_table(
        'institutions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('invite_code', sa.String(), nullable=False, unique=True),
        sa.Column('max_students', sa.Integer(), server_default='100'),
        sa.Column('max_teachers', sa.Integer(), server_default='10'),
        sa.Column('subscription_tier', sa.String(), server_default="'free'"),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('admin_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_institutions_id', 'institutions', ['id'])
    op.create_index('ix_institutions_email', 'institutions', ['email'])
    op.create_index('ix_institutions_invite_code', 'institutions', ['invite_code'])

    # Add TEACHER to the userrole enum (uppercase to match existing values)
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'TEACHER'")

    # Add institution_id column to users table
    op.add_column('users', sa.Column('institution_id', sa.Integer(), sa.ForeignKey('institutions.id'), nullable=True))

    # Create teacher_students table
    op.create_table(
        'teacher_students',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('teacher_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('student_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_teacher_students_id', 'teacher_students', ['id'])
    op.create_index('ix_teacher_students_teacher_id', 'teacher_students', ['teacher_id'])
    op.create_index('ix_teacher_students_student_id', 'teacher_students', ['student_id'])


def downgrade() -> None:
    op.drop_table('teacher_students')
    op.drop_column('users', 'institution_id')
    op.drop_table('institutions')
