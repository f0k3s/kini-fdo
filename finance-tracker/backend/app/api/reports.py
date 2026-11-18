"""Роутер отчётов."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_report_service
from app.schemas import CategoryRead, ReportRead, money_str
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/monthly", response_model=ReportRead)
def monthly_report(
    month: str = Query(description="Месяц в формате YYYY-MM"),
    category: str | None = Query(default=None),
    account_id: str | None = Query(default=None),
    service: ReportService = Depends(get_report_service),
) -> ReportRead:
    report = service.build_monthly_report(
        month, category=category, account_id=account_id
    )
    top = None
    if report.top_category is not None:
        top = CategoryRead(
            name=report.top_category.name,
            amount=money_str(report.top_category.amount),
            share=report.top_category.share,
        )
    return ReportRead(
        month=report.month,
        operations=report.operations,
        income=money_str(report.income),
        expense=money_str(report.expense),
        balance=money_str(report.balance),
        categories={name: money_str(value) for name, value in report.categories.items()},
        top_category=top,
        average_expense=money_str(report.average_expense),
        warnings=report.warnings,
    )
