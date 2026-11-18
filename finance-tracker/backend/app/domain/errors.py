"""Исключения предметной области.

Роутеры переводят их в HTTP-коды, сервисы о HTTP ничего не знают.
"""

from __future__ import annotations


class DomainError(Exception):
    """Базовое исключение всех ошибок предметной области."""


class ValidationError(DomainError):
    """Нарушено правило валидации данных."""


class NotFoundError(DomainError):
    """Запрошенный объект не найден."""


class ConflictError(DomainError):
    """Операция конфликтует с текущим состоянием данных."""


class InsufficientFunds(DomainError):
    """На счёте недостаточно средств для расхода."""
