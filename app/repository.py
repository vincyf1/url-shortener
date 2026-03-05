"""Repository contracts and domain dataclasses for URL shortener storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class URLRecord:
    id: int
    short_code: str
    original_url: str
    created_at: str
    click_count: int
    title: Optional[str]
    active: int

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "short_code": self.short_code,
            "original_url": self.original_url,
            "created_at": self.created_at,
            "click_count": self.click_count,
            "title": self.title,
            "active": self.active,
        }


@dataclass(frozen=True)
class AppSetting:
    key: str
    value: str


DEFAULT_SETTINGS = {
    "server_port": "8080",
    "base_url": "http://localhost:8080",
    "server_enabled": "1",
}


class URLRepository(ABC):
    """Storage interface used by domain/services and UI."""

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def add_url(self, short_code: str, original_url: str, title: Optional[str] = None) -> dict: ...

    @abstractmethod
    def get_url_by_code(self, short_code: str) -> Optional[dict]: ...

    @abstractmethod
    def get_all_urls(self, include_inactive: bool = False) -> list[dict]: ...

    @abstractmethod
    def search_urls(self, query: str) -> list[dict]: ...

    @abstractmethod
    def increment_click_count(self, short_code: str) -> None: ...

    @abstractmethod
    def delete_url(self, short_code: str) -> bool: ...

    @abstractmethod
    def hard_delete_url(self, short_code: str) -> bool: ...

    @abstractmethod
    def update_url(self, short_code: str, original_url: Optional[str] = None, title: Optional[str] = None) -> Optional[dict]: ...

    @abstractmethod
    def code_exists(self, short_code: str) -> bool: ...

    @abstractmethod
    def get_url_count(self) -> int: ...

    @abstractmethod
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]: ...

    @abstractmethod
    def set_setting(self, key: str, value: str) -> None: ...

    @abstractmethod
    def get_all_settings(self) -> dict[str, str]: ...
