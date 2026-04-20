import os
from typing import Any

import requests
from dotenv import load_dotenv


class ZernioError(Exception):
    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class ZernioClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 30.0):
        load_dotenv()
        self.api_key = api_key or os.getenv("ZERNIO_API_KEY")
        self.base_url = (base_url or os.getenv("ZERNIO_BASE_URL") or "https://zernio.com/api/v1").rstrip("/")
        self.timeout = timeout

        if not self.api_key:
            raise ZernioError("ZERNIO_API_KEY is not set. Copy .env.example to .env and fill it in.")
        if not self.api_key.startswith("sk_"):
            raise ZernioError("API key looks wrong — Zernio keys start with 'sk_'.")

        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "zernio-client/0.2 (music-marketing)",
        })

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise ZernioError(f"Network error calling {method} {path}: {exc}") from exc

        if resp.status_code == 401:
            raise ZernioError("Auth failed (401). Check ZERNIO_API_KEY.", 401, resp.text)
        if resp.status_code == 403:
            raise ZernioError("Forbidden (403). API key scope may be too narrow.", 403, resp.text)
        if resp.status_code == 429:
            raise ZernioError("Rate limited (429). Accelerate = 600 req/min.", 429, resp.text)
        if resp.status_code >= 400:
            try:
                payload = resp.json()
            except ValueError:
                payload = resp.text
            raise ZernioError(f"{method} {path} failed ({resp.status_code})", resp.status_code, payload)

        if not resp.content:
            return None
        try:
            return resp.json()
        except ValueError:
            return resp.text

    # ---- Accounts ----

    def list_accounts(self) -> Any:
        return self._request("GET", "/accounts")

    def accounts_health(self) -> Any:
        return self._request("GET", "/accounts/health")

    def tiktok_creator_info(self, account_id: str) -> Any:
        return self._request("GET", f"/accounts/{account_id}/tiktok-creator-info")

    # ---- Posts ----

    def list_posts(self, **params: Any) -> Any:
        return self._request("GET", "/posts", params=params or None)

    def get_post(self, post_id: str) -> Any:
        return self._request("GET", f"/posts/{post_id}")

    def create_post(self, payload: dict) -> Any:
        return self._request("POST", "/posts", json=payload)

    def update_post(self, post_id: str, payload: dict) -> Any:
        return self._request("PATCH", f"/posts/{post_id}", json=payload)

    def delete_post(self, post_id: str) -> Any:
        return self._request("DELETE", f"/posts/{post_id}")

    def retry_post(self, post_id: str) -> Any:
        return self._request("POST", f"/posts/{post_id}/retry")

    def bulk_upload_posts(self, payload: dict) -> Any:
        return self._request("POST", "/posts/bulk-upload", json=payload)

    # ---- Media ----

    def get_presigned_media_url(self, filename: str, content_type: str) -> Any:
        return self._request(
            "GET",
            "/media/presigned-url",
            params={"filename": filename, "contentType": content_type},
        )

    # ---- Webhooks ----

    def create_webhook(self, url: str, events: list[str], secret: str | None = None) -> Any:
        payload: dict[str, Any] = {"url": url, "events": events}
        if secret:
            payload["secret"] = secret
        return self._request("POST", "/webhooks", json=payload)

    # ---- OAuth ----

    def initiate_oauth(self, platform: str, headless: bool = False) -> Any:
        params = {"headless": "true"} if headless else None
        return self._request("GET", f"/connect/{platform}", params=params)
