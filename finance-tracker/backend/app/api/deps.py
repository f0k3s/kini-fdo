"""Зависимости FastAPI: сервисы и репозиторий берутся из app.state.

Это позволяет в тестах подставить InMemoryRepository и не поднимать базу.
"""

from __future__ import annotations

from fastapi import Request

from app.repositories.base import Repository
from app.services.account_service import AccountService
from app.services.operation_service import OperationService
from app.services.report_service import ReportService


def get_repository(request: Request) -> Repository:
    return request.app.state.repository


def get_account_service(request: Request) -> AccountService:
    return AccountService(get_repository(request))


def get_operation_service(request: Request) -> OperationService:
    return OperationService(get_repository(request))


def get_report_service(request: Request) -> ReportService:
    return ReportService(get_repository(request))
