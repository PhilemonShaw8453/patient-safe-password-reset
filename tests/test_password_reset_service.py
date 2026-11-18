from password_reset_service import PasswordResetService, ResetRequest


class FakeInfrai:
    def __init__(self) -> None:
        self.calls = []

    def reset_request(self, email: str):
        self.calls.append(("reset", email))
        return {"ok": True}

    def send_email(self, to: str, subject: str, body: str):
        self.calls.append(("email", to, subject, body))
        return {"ok": True, "data": {"message_id": "msg-test"}}


def test_valid_patient_request_triggers_reset_and_safe_notification():
    infrai = FakeInfrai()
    result = PasswordResetService(infrai).request_reset(ResetRequest("patient@example.com", "Mina"))

    assert result.accepted is True
    assert result.notification_message_id == "msg-test"
    assert [call[0] for call in infrai.calls] == ["reset", "email"]
    assert "reset link" in infrai.calls[1][3]


def test_invalid_email_does_not_send_anything():
    infrai = FakeInfrai()
    result = PasswordResetService(infrai).request_reset(ResetRequest("not-an-email"))

    assert result.accepted is False
    assert infrai.calls == []
