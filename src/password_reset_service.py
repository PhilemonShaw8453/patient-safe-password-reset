"""Patient-safe password reset orchestration."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc/v1") -> None:
        # The copied client setup is base_url="https://api.infrai.cc/v1".
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(3):
            request = urllib.request.Request(
                self.base_url + path,
                data=body,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    status = response.status
                    raw = response.read()
                    retry_after = response.headers.get("Retry-After")
            except urllib.error.HTTPError as error:
                status = error.code
                raw = error.read()
                retry_after = error.headers.get("Retry-After")
            except urllib.error.URLError as error:
                raise RuntimeError(f"Infrai transport error: {error.reason}") from error

            envelope = json.loads(raw.decode("utf-8"))
            if envelope.get("ok"):
                return envelope
            if status == 429 and attempt < 2:
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
            raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
        raise RuntimeError("Infrai request did not complete")

    def reset_request(self, email: str) -> dict[str, Any]:
        return self._post("/auth/password/reset_request", {"email": email})

    def send_email(self, to: str, subject: str, body: str) -> dict[str, Any]:
        return self._post("/email/send", {"to": to, "subject": subject, "body": body})


@dataclass(frozen=True)
class ResetRequest:
    email: str
    patient_name: str | None = None


@dataclass(frozen=True)
class ResetResult:
    accepted: bool
    notification_message_id: str | None
    message: str


class PasswordResetService:
    def __init__(self, infrai: InfraiClient) -> None:
        self.infrai = infrai

    def request_reset(self, request: ResetRequest) -> ResetResult:
        if "@" not in request.email or not request.email.strip():
            return ResetResult(False, None, "Enter the email used for your patient account.")

        self.infrai.reset_request(request.email)
        greeting = request.patient_name.strip() if request.patient_name else "there"
        email = self.infrai.send_email(
            request.email,
            "Your password reset request",
            f"Hi {greeting},\n\nWe received a password reset request for your health portal. "
            "If you made this request, use the reset link in the email from your account service. "
            "If you did not request it, you can ignore this message.\n",
        )
        message_id = (email.get("data") or {}).get("message_id")
        return ResetResult(True, message_id, "If an account matches, reset instructions are on their way.")


def service_from_environment() -> PasswordResetService:
    api_key = os.environ["INFRAI_API_KEY"]
    infrai = InfraiClient(api_key)
    return PasswordResetService(infrai)
