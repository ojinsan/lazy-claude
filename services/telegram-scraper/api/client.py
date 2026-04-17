"""Backend API client for submitting insights."""
from __future__ import annotations

import httpx
from pathlib import Path

from ..config import Settings
from ..core.message import Snapshot
from ..utils.time import format_iso


class BackendAPIClient:
    """Client for communicating with the backend API."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._http_client: httpx.AsyncClient | None = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            headers = {}
            if self.settings.api_token:
                headers["Authorization"] = f"Bearer {self.settings.api_token}"
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.api_timeout),
                headers=headers,
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def submit_snapshot(self, snapshot: Snapshot) -> dict:
        """
        Submit a 30-minute snapshot to the backend.

        The backend AI will process the content and split into chunks.
        Each chunk will be stored as a separate insight per ticker.
        """
        if self.settings.dry_run:
            if self.settings.print_messages:
                print(f"\n[DRY RUN] Would submit snapshot:")
                print(f"  Chat: {snapshot.chat_name}")
                print(f"  Window: {snapshot.window_start} - {snapshot.window_end}")
                print(f"  Messages: {len(snapshot.messages)}")
                print(f"  Reply context: {len(snapshot.reply_context)}")
                print(f"  Content:\n{snapshot.to_content()[:500]}...")
            return {"stored": 0, "message": "dry run"}

        payload = {
            "insights": [
                {
                    "time": format_iso(snapshot.window_end),
                    "content": snapshot.to_content(),
                    "participant_type": "admin",
                    "address_text": snapshot.to_address_text(),
                    "source": snapshot.chat_name,  # Telegram group name
                }
            ]
        }

        if self.settings.print_messages:
            print(f"\n[POST] Submitting snapshot for {snapshot.chat_name}")
            print(f"  Window: {snapshot.window_start} - {snapshot.window_end}")
            print(f"  Messages: {len(snapshot.messages)}")

        response = await self.http_client.post(
            self.settings.insight_api_url,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def upload_media(self, file_path: Path) -> str | None:
        """
        Upload a media file to the backend.

        Returns the URL of the uploaded file, or None on failure.
        """
        if not file_path.exists():
            return None

        if self.settings.dry_run:
            return f"[dry_run]{file_path.name}"

        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f)}
                response = await self.http_client.post(
                    self.settings.upload_url,
                    files=files,
                )
                response.raise_for_status()
                result = response.json()
                return result.get("url")
        except Exception as e:
            print(f"Failed to upload media {file_path}: {e}")
            return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
