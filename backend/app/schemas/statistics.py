"""Pydantic schemas for admin statistics dashboard."""

from typing import Dict
from pydantic import BaseModel


class AdminStatsResponse(BaseModel):
    """Thống kê tổng hợp toàn hệ thống cho quản trị viên."""

    total_users: int
    total_analyses: int
    total_reports: int
    pending_reports: int
    under_review_reports: int
    verified_reports: int
    rejected_reports: int
    total_verified_employers: int
    total_warnings: int
    active_warnings: int
    risk_distribution: Dict[str, int]
    report_status_distribution: Dict[str, int]
