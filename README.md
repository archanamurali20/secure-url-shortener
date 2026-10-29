# Secure URL Shortener

A URL shortener API built as a vehicle for practising secure backend development, with each security control chosen deliberately.

## Live demo

https://secure-url-shortener-qyvm.onrender.com/docs

Note: The first request may take up to a minute as the app and the database wakes on demand.

## Tech Stack
- Python
- FastAPI
- SQLModel/SQLAlchemy
- Postgres
- Pydantic
- PyJWT
- pwdlib
- slowapi
- pytest

## Endpoints
| Methods | Path             | Description                              | Response                                                                               |
| ------- | ---------------- | ---------------------------------------- | -------------------------------------------------------------------------------------- |
| GET     | `/health`        | Checks service is running and responsive | 200 with status ok                                                                     |
| POST    | `/links`         | Creates a code and short url for the given long url         | 200 with assigned code and short url <br>401 unauthenticated <br>422 on validation error <br> 429 when rate limited                                       |
| GET     | `/links/{code}`  | Gets the link for the code               | 302 with the redirection to the corresponding link<br>404 on code not found <br> 429 when rate limited                                |
| POST    | `/auth/register` | Creates a user account                   | 200 with name and email,<br>409 on duplicate email, <br>422 on validation failure <br> 429 when rate limited  |
| POST    | `/auth/login`    | Exchanges credentials for a JWT          | 200 with access token, <br>401 on bad credentials, <br> 429 when rate limited          |
| GET     | `/links`     | Lists the authenticated user's links     | 200 with list of codes and URLs,<br>401 without a valid token <br> 429 when rate limited                          |
| DELETE  | `/links/{code}`  | Deletes a link you own                   | 204 on success, <br>401 unauthenticated, <br>403 if not yours, <br>404 if no such code <br> 429 when rate limited |

## How to run it?
1.  Clone the repo
2. Create the venv : `python -m venv venv`
3. Activate the venv - Windows(Powershell)  `venv\Scripts\Activate.ps1`
4. Install the dependencies:
   - To run the app and the tests: pip install -r requirements-dev.txt
   - To run the app only: pip install -r requirements.txt
5. To create the database replace the password value - `docker run --name pg -e POSTGRES_PASSWORD=yourpassword -e POSTGRES_DB=urlshortener -p 5432:5432 -d postgres`
6. For the test database `docker exec -it pg psql -U postgres -c "CREATE DATABASE urlshortener_test;"`
7. Copy `.env.example` to `.env` and generate the `SECRET_KEY`, `DATABASE_URL` , `BASE_URL` and the `TEST_DATABASE_URL`

8. run the app: `uvicorn main:app --reload`
9. Go to `http://127.0.0.1:8000/docs`

## Security Decisions

1. Input validation — Pydantic validates at the trust boundary; malformed input never reaches the handler.
2. SQL injection prevention — All queries are ORM-generated and parameterized, so the command and the values travel separately and the database parses structure before seeing input. A value like '; DROP TABLE urltable;-- is searched for, never executed.
3. Code uniqueness 
    - Unguessable codes — `secrets` rather than `random`, 7 alphanumeric characters (~3.5 trillion combinations) so codes can't be enumerated.
    - Uniqueness is enforced by a database constraint, not an application check: check-then-write isn't atomic, so concurrent requests can both pass the check
    - The insert is attempted directly and retried with a fresh code on IntegrityError, capped at five attempts so a constraint violation unrelated to collision can't retry forever.
4. Password Storage
    - Argon2 for hashing - OWASP's current recommendation, and resistant to GPU-based cracking
    - Per-user salts, so identical passwords produce different hashes and precomputed rainbow tables are useless.
    - Deliberately slow parameters — the cost per hash is negligible for one login but makes brute-forcing impractical.
    - The password hash is excluded from API responses by the response model.
    - Length bounded at both ends, 8 to 128 (OWASP). This is enforced when a password is set and deliberately not at login, so raising the policy later can never lock out an existing account.
5. Authentication
    - Signing key read from environment variables, never committed; `.env` gitignored with a `.env.example` documenting required config.
    - Token expiry (30 min) bounds the damage window if a token leaks. Decode requires exp and sub, so a token issued without an expiry is rejected rather than valid forever.
    - `algorithms` pinned explicitly on decode, preventing algorithm-substitution attacks such as `alg: none`.
    - Generic 401 for both wrong password and unknown email, so responses don't reveal which emails are registered.
    - The unknown-email path also verifies against a dummy hash, so both paths pay the same Argon2 cost. Without it, a fast rejection would mark the email as unregistered regardless of the matching response body.
    - Unexpired, validly-signed tokens still rejected if the user no longer exists.
6. Authorization
    - `GET /links` scopes by `owner_id` in the query itself, so a user's results can only ever contain their own rows.
    - `DELETE /links/{code}` checks ownership against the authenticated user's id before acting
    - 404 and 403 are distinct: a missing code returns 404, an existing code owned by someone else returns 403. 
7. Rate limiting
    - Limits are per endpoint rather than global, so the cap matches the surface being protected.
    - Login is tightest at 5/minute — it is the credential-guessing surface, and throttling attempts is what makes Argon2's cost per hash actually bind on an attacker. The slow hash and the rate limit are one defence, not two.
    - Registration is capped at 5/hour to limit automated account creation.
    - Link creation and deletion are capped to limit abuse; read endpoints are capped more loosely since they are the normal usage path.
    - Exceeding a limit returns 429 rather than failing silently, so clients can back off.
    - `/health` is deliberately unlimited so uptime checks are never throttled.
8. `BASE_URL` is taken from the config file rather than the `Host` header, preventing host header injection.
9. Submitted URLs are rejected if the host is a loopback, private, link-local, reserved, multicast or unspecified address,  limiting the open-redirect surface. The check is parse-only, the server never fetches the URL to verify it, which would introduce an SSRF surface and only guarantee reachability at the moment of validation. 
10. The short code path parameter is constrained to its exact shape at the route, so a malformed code is rejected before it reaches a query. 
11. Request body size — middleware rejects bodies over 64KB on Content-Length, before
    routing and before the body is read into the application. 

## Testing

28 tests, 95% coverage on application modules. Run with `pytest -v`.

- Tests run against a separate PostgreSQL database with tables created and dropped per test, and the session dependency overridden so application code is exercised unmodified. Rate limiting is disabled via an autouse fixture.
- Coverage targets the security decisions above - duplicate-email rejection, hash never returned in a response, cross-user delete returning 403 with the link surviving, owner-scoped listing, and rejection of loopback, private and link-local hosts.
- The enumeration test compares the wrong-password and unknown-email responses to each other rather than to a fixed string, so it verifies indistinguishability rather than wording.


## Known Limitations
1. Private and reserved IP literals are blocked, but hostnames aren't resolved. A domain pointing at a private address passes, as do integer-encoded IPs.
2. Short codes are bearer capabilities. Redirection is unauthenticated by design. This is why ownership failures return 403 rather than 404 as code existence is already public.
3. Rate limiting is per-IP and in-memory, so it resets on restart and doesn't span instances. Behind a proxy the observed IP is the proxy's; using X-Forwarded-For requires knowing which proxies to trust, since clients can set it themselves.
4. Open redirect - feature of url shortener. Can be mitigated by reputation checking, abuse reporting, blocklists etc.
5. The 64KB body limit only checks `Content-Length`, so chunked requests bypass it and are processed in full. Fix: count bytes as the body streams in.