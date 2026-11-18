from __future__ import annotations

import argparse

from password_reset_service import ResetRequest, service_from_environment


def main() -> None:
    parser = argparse.ArgumentParser(description="Request a patient-safe password reset")
    parser.add_argument("email")
    parser.add_argument("--name")
    args = parser.parse_args()
    result = service_from_environment().request_reset(ResetRequest(args.email, args.name))
    print(result.message)
    if result.notification_message_id:
        print(f"Notification message id: {result.notification_message_id}")


if __name__ == "__main__":
    main()
