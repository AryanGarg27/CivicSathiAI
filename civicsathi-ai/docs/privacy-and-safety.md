# Privacy and access

- Public visitors can browse the service directory. Reporting, photo analysis, tracking and account pages require an account.
- Passwords are stored as scrypt hashes; sessions are random bearer tokens stored only as SHA-256 digests, with an HTTP-only SameSite cookie and a 14-day expiry.
- Case and photo APIs enforce ownership. Staff roles must be assigned from `STAFF_EMAILS` before registration. Keep that allowlist private.
- Uploading a photo to the AI feature transmits its normalized pixels and any supplied description to Google. EXIF metadata is stripped. Do not include sensitive or identifying images in a hackathon demo.
- SQLite stores profile email/name, complaint location/summary, photos, AI observations and status history. It is not encrypted by this prototype. Store it on a persistent mounted volume and back it up.
- Public registration has a basic per-IP request limit, but it does not include email verification, password reset, account deletion, reverse-proxy rate limits or email abuse controls. Do not use for real residents without adding these.
- Tracking is account-based; signed-in users only see their own cases. No official application, payment, enforcement action or municipal complaint submission occurs.
- Use test accounts and synthetic complaint data for judging. The demo is not emergency dispatch.
