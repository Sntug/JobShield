"""Service for calculating administration and platform statistics."""

from collections import defaultdict
from typing import Dict
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.analyses import Analysis
from app.models.reports import PublicWarning, Report
from app.models.users import User
from app.models.verifications import VerifiedEmployer
from app.schemas.statistics import AdminStatsResponse


def get_admin_statistics(db: Session) -> AdminStatsResponse:
    """Tổng hợp thống kê toàn diện cho trang quản trị."""
    total_users = db.query(User).count()
    total_analyses = db.query(Analysis).count()

    total_reports = db.query(Report).count()
    pending_reports = db.query(Report).filter(Report.status == "pending").count()
    under_review_reports = (
        db.query(Report).filter(Report.status == "under_review").count()
    )
    verified_reports = db.query(Report).filter(Report.status == "verified").count()
    rejected_reports = db.query(Report).filter(Report.status == "rejected").count()

    total_verified_employers = db.query(VerifiedEmployer).count()

    total_warnings = db.query(PublicWarning).count()
    active_warnings = (
        db.query(PublicWarning).filter(PublicWarning.status == "published").count()
    )

    # Phân bố rủi ro từ analyses
    risk_query = (
        db.query(Analysis.risk_label_vi, func.count(Analysis.id))
        .group_by(Analysis.risk_label_vi)
        .all()
    )
    risk_distribution: Dict[str, int] = {
        label: count for label, count in risk_query if label
    }

    # Phân bố trạng thái báo cáo
    report_status_query = (
        db.query(Report.status, func.count(Report.id))
        .group_by(Report.status)
        .all()
    )
    report_status_distribution: Dict[str, int] = {
        status: count for status, count in report_status_query if status
    }

    return AdminStatsResponse(
        total_users=total_users,
        total_analyses=total_analyses,
        total_reports=total_reports,
        pending_reports=pending_reports,
        under_review_reports=under_review_reports,
        verified_reports=verified_reports,
        rejected_reports=rejected_reports,
        total_verified_employers=total_verified_employers,
        total_warnings=total_warnings,
        active_warnings=active_warnings,
        risk_distribution=risk_distribution,
        report_status_distribution=report_status_distribution,
    )
