"""R4 reports, moderation actions, public warnings, and risk indicator rules.

Revision ID: e8f9a0b1c2d3
Revises: d7a8b9c0e1f2
"""
from datetime import datetime, timezone
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa


revision: str = 'e8f9a0b1c2d3'
down_revision: Union[str, None] = 'd7a8b9c0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

R4_TABLES = (
    'risk_indicators',
    'recruitment_reports',
    'report_evidence',
    'moderation_actions',
    'public_warnings',
)


def upgrade() -> None:
    now = datetime.now(timezone.utc)

    # 1. risk_indicators
    risk_indicators_table = op.create_table(
        'risk_indicators',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('explanation_vi', sa.Text(), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_risk_indicators_code'), 'risk_indicators', ['code'], unique=True)

    # Seed 8 canonical risk indicator rules
    default_rules = [
        {
            'id': uuid.uuid4(),
            'code': 'RULE_UPFRONT_FEE',
            'name': 'Phí tuyển dụng trước',
            'description': 'Yêu cầu ứng viên đóng tiền phí xét tuyển, đồng phục, hồ sơ trước khi làm việc.',
            'explanation_vi': 'Doanh nghiệp chân chính không thu phí tuyển dụng từ ứng viên.',
            'weight': 35,
            'enabled': True,
            'is_demo': False,
            'updated_at': now,
        },
        {
            'id': uuid.uuid4(),
            'code': 'RULE_DEPOSIT_BEFORE_INTERVIEW',
            'name': 'Đặt cọc trước phỏng vấn',
            'description': 'Buộc ứng viên chuyển tiền đặt cọc giữ chỗ phỏng vấn hoặc nhận thiết bị.',
            'explanation_vi': 'Đặt cọc trước phỏng vấn là dấu hiệu lừa đảo phổ biến.',
            'weight': 35,
            'enabled': True,
            'is_demo': False,
            'updated_at': now,
        },
        {
            'id': uuid.uuid4(),
            'code': 'RULE_PERSONAL_TRANSFER',
            'name': 'Yêu cầu chuyển tiền tài khoản cá nhân',
            'description': 'Cung cấp số tài khoản ngân hàng cá nhân và yêu cầu chuyển tiền gấp.',
            'explanation_vi': 'Giao dịch qua tài khoản cá nhân thay vì pháp nhân doanh nghiệp.',
            'weight': 30,
            'enabled': True,
            'is_demo': False,
            'updated_at': now,
        },
        {
            'id': uuid.uuid4(),
            'code': 'RULE_SUSPICIOUS_CHANNEL',
            'name': 'Kênh liên hệ đáng ngờ',
            'description': 'Yêu cầu liên hệ qua Telegram, Zalo ẩn danh, không có email tên miền công ty.',
            'explanation_vi': 'Kênh liên hệ ẩn danh khiến khó truy cứu trách nhiệm khi xảy ra sự cố.',
            'weight': 20,
            'enabled': True,
            'is_demo': False,
            'updated_at': now,
        },
        {
            'id': uuid.uuid4(),
            'code': 'RULE_UNREALISTIC_INCOME',
            'name': 'Hứa thu nhập phi thực tế',
            'description': 'Quảng cáo việc nhẹ lương cao, làm tại nhà 30-50 triệu/tháng không yêu cầu kỹ năng.',
            'explanation_vi': 'Mức thù lao không tương xứng với tính chất công việc là bẫy tài chính.',
            'weight': 25,
            'enabled': True,
            'is_demo': False,
            'updated_at': now,
        },
        {
            'id': uuid.uuid4(),
            'code': 'RULE_TASK_TOPUP',
            'name': 'Nhiệm vụ có nạp tiền / giật đơn',
            'description': 'Yêu cầu nạp tiền làm nhiệm vụ, xem video tăng tương tác, mua đơn hàng ảo nhận hoa hồng.',
            'explanation_vi': 'Mô hình giật đơn nạp tiền chuyển tiền là thủ đoạn chiếm đoạt tài sản.',
            'weight': 40,
            'enabled': True,
            'is_demo': False,
            'updated_at': now,
        },
        {
            'id': uuid.uuid4(),
            'code': 'RULE_SENSITIVE_DATA',
            'name': 'Yêu cầu dữ liệu nhạy cảm bất thường',
            'description': 'Đòi hỏi ảnh hai mặt CCCD, số OTP, mã thẻ ngân hàng ngay vòng đầu.',
            'explanation_vi': 'Thu thập trái phép thông tin định danh cá nhân nhằm mở tài khoản ngân hàng ảo.',
            'weight': 25,
            'enabled': True,
            'is_demo': False,
            'updated_at': now,
        },
        {
            'id': uuid.uuid4(),
            'code': 'RULE_IMPERSONATION',
            'name': 'Chỉ dấu mạo danh thương hiệu',
            'description': 'Sử dụng trái phép logo, tên doanh nghiệp lớn nhưng email/tên miền giả mạo.',
            'explanation_vi': 'Mạo danh tổ chức uy tín để tạo lòng tin giả mạo cho ứng viên.',
            'weight': 30,
            'enabled': True,
            'is_demo': False,
            'updated_at': now,
        },
    ]
    op.bulk_insert(risk_indicators_table, default_rules)

    # 2. recruitment_reports
    op.create_table(
        'recruitment_reports',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('analysis_id', sa.Uuid(), sa.ForeignKey('analyses.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reporter_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reason', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('private_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('anonymized_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(trim(reason)) > 0", name='ck_report_reason'),
        sa.CheckConstraint("length(trim(description)) > 0", name='ck_report_description'),
        sa.CheckConstraint("status IN ('pending', 'under_review', 'verified', 'rejected')", name='ck_report_status'),
        sa.CheckConstraint("version >= 1", name='ck_report_version'),
    )
    op.create_index(op.f('ix_recruitment_reports_analysis_id'), 'recruitment_reports', ['analysis_id'], unique=False)
    op.create_index(op.f('ix_recruitment_reports_reporter_id'), 'recruitment_reports', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_recruitment_reports_status'), 'recruitment_reports', ['status'], unique=False)

    # 3. report_evidence
    op.create_table(
        'report_evidence',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('report_id', sa.Uuid(), sa.ForeignKey('recruitment_reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evidence_type', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('storage_key', sa.String(255), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("evidence_type IN ('text', 'url', 'image')", name='ck_evidence_type'),
    )
    op.create_index(op.f('ix_report_evidence_report_id'), 'report_evidence', ['report_id'], unique=False)

    # 4. moderation_actions
    op.create_table(
        'moderation_actions',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('report_id', sa.Uuid(), sa.ForeignKey('recruitment_reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('moderator_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('action_type', sa.String(30), nullable=False),
        sa.Column('from_status', sa.String(30), nullable=False),
        sa.Column('to_status', sa.String(30), nullable=False),
        sa.Column('report_version_after', sa.Integer(), nullable=False),
        sa.Column('reviewed_evidence_ids', sa.JSON(), nullable=True),
        sa.Column('decision_summary', sa.Text(), nullable=False),
        sa.Column('private_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action_type IN ('review', 'request_evidence', 'verify', 'reject')", name='ck_moderation_action_type'),
    )
    op.create_index(op.f('ix_moderation_actions_report_id'), 'moderation_actions', ['report_id'], unique=False)
    op.create_index(op.f('ix_moderation_actions_moderator_id'), 'moderation_actions', ['moderator_id'], unique=False)

    # 5. public_warnings
    op.create_table(
        'public_warnings',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('report_id', sa.Uuid(), sa.ForeignKey('recruitment_reports.id', ondelete='SET NULL'), nullable=True),
        sa.Column('decision_id', sa.Uuid(), sa.ForeignKey('moderation_actions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('previous_warning_id', sa.Uuid(), sa.ForeignKey('public_warnings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('revision', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(20), nullable=False, server_default='published'),
        sa.Column('title_vi', sa.String(255), nullable=False),
        sa.Column('public_summary_vi', sa.Text(), nullable=False),
        sa.Column('public_sources_snapshot', sa.JSON(), nullable=False),
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_by', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('withdrawn_by', sa.Uuid(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('withdrawal_actor_type', sa.String(20), nullable=True),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('withdrawal_reason_vi', sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('published', 'superseded', 'withdrawn')", name='ck_warning_status'),
        sa.CheckConstraint("revision >= 1", name='ck_warning_revision'),
    )
    op.create_index(op.f('ix_public_warnings_report_id'), 'public_warnings', ['report_id'], unique=False)
    op.create_index(op.f('ix_public_warnings_status'), 'public_warnings', ['status'], unique=False)
    op.create_index(op.f('ix_public_warnings_previous_warning_id'), 'public_warnings', ['previous_warning_id'], unique=True)

    # RLS & Data API privacy protection
    for table in R4_TABLES:
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        op.execute(f"""
            DO $privacy$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL PRIVILEGES ON TABLE {table} FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL PRIVILEGES ON TABLE {table} FROM authenticated;
                END IF;
            END
            $privacy$;
        """)


def downgrade() -> None:
    for table in reversed(R4_TABLES):
        op.drop_table(table)
