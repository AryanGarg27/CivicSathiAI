# Privacy and access

- Public visitors can browse the service directory. Reporting, photo analysis, application intake, tracking and account pages require an account.
- Passwords are stored as scrypt hashes; sessions are random bearer tokens stored only as SHA-256 digests, with an HTTP-only SameSite cookie and a 14-day expiry.
- Case and photo APIs enforce ownership. Staff roles must be assigned from `STAFF_EMAILS` before registration. Keep that allowlist private.
- Uploading a photo to the AI feature transmits its normalized pixels and any supplied description to Google. EXIF metadata is stripped. Do not include sensitive or identifying images in a hackathon demo.
- SQLite stores profile email/name, complaint location/summary, photos, AI observations, limited service-request contact details and status history. Health appointment notes may contain sensitive information; keep them brief and do not enter a medical history. Social-welfare demo forms intentionally do not request Aadhaar or bank identifiers. The database is not encrypted by this prototype. Store it on a persistent mounted volume and back it up.
- Public registration has a basic per-IP request limit, but it does not include email verification, password reset, account deletion, reverse-proxy rate limits or email abuse controls. Do not use for real residents without adding these.
- Tracking is account-based; signed-in users only see their own cases and service requests. No appointment is booked and no official application, payment, enforcement action or municipal complaint submission occurs.
- The nearby-centre page uses browser geolocation only after a user clicks the location button. Coordinates are placed in a Maps search link; CivicSathi does not send or retain them. If the user opens that link, Maps receives the location.
- Open-ended AI intake sends the typed or dictated request to the configured AI provider for classification. The app stores it only after the user reviews and confirms the draft.
- Use test accounts and synthetic complaint data for judging. The demo is not emergency dispatch.
