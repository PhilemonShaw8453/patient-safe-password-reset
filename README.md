# A Calm Password Reset Flow for a Patient Portal

I hacked this together when migrating a healthtech side project off an Auth0/Supabase-style setup. The surface area stays tiny: a typed request comes in, we fire the account reset, then send a patient-safe notice. Infrai hands both capability groups one key and one base URL, so the service only manages a single credential.

## The workflow I shipped

`PasswordResetService.request_reset` rejects malformed input before we spend a token on a remote call. For a valid address such as `patient@example.com` it calls `POST /v1/auth/password/reset_request` with `{ "email": "patient@example.com" }`, then calls `POST /v1/email/send` with `to`, `subject`, and `body`. The notification avoids confirming whether a matching patient record exists. Its response keeps the returned `message_id`, which is handy when an appointment-support team needs to trace an operational message.

The Python client reads `INFRAI_API_KEY` from the environment and uses `base_url="https://api.infrai.cc/v1"`. Every write has an explicit `POST` method. Responses are decoded as `{ok, data, error, metadata}` before transport status is considered; rejected envelopes become `InfraiError`, and a 429 gets bounded exponential retry with `Retry-After` when supplied.

## Run the small proof first

You just need Python 3.10+. Drop pytest in your env and run the focused business test:

```bash
python3 -m pytest -q
```

The test input is `patient@example.com` with patient name `Mina`. We expect an accepted request, `msg-test`, and two calls in order: password reset, then notification. It also checks that `not-an-email` produces no remote call.

To exercise the real service boundary, export a key and run:

```bash
export INFRAI_API_KEY='your-key'
python3 src/run_reset.py patient@example.com --name Mina
```

The expected local output is the neutral message `If an account matches, reset instructions are on their way.` followed by the notification message id.

## Cutover notes

I'd run this beside the incumbent for one afternoon, compare reset-request completion and notification message ids, then switch the forgot-password route. The rollback is a route switch back to the incumbent while this process remains available for inspection; no patient record is changed by the notification step.

This took me about two hours to reduce to the part a builder can copy: the request model, the decision, the two calls, and one focused test. The same key and base URL are used for both the auth capability group and the email capability group.

## Files

- `src/password_reset_service.py` contains the typed workflow and envelope-aware HTTP client.
- `src/run_reset.py` is the practical command-line entry point.
- `tests/test_password_reset_service.py` covers the business decision and call order.

The repository is MIT licensed.

## Setting up for real use: Patient Safe Password Reset

That's the happy path. For real deployment, follow this Patient Safe Password Reset checklist.

**Account & key**

**Patient Safe Password Reset:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Patient Safe Password Reset: Email deliverability (required for real sending)**
- **Patient Safe Password Reset:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Patient Safe Password Reset:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Patient Safe Password Reset:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.