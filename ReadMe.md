# Secure URL Shortener

A URL shortener API built as a vehicle for practising secure backend development, with each security control chosen deliberately.

## Tech Stack
- Python
- FastAPI
- SQLModel/SQLAlchemy
- SQLite
- Pydantic

## Endpoints
| Methods | Path             | Description                              | Response                                                                               |
| ------- | ---------------- | ---------------------------------------- | -------------------------------------------------------------------------------------- |
| GET     | `/health`        | Checks service is running and responsive | 200 with status ok                                                                     |
| POST    | `/links`         | Creates a code for the given url         | 200 with assigned code <br>401 unauthenticated <br>422 on validation error                                        |
| GET     | `/links/{code}`  | Gets the link for the code               | 200 with the corresponding link<br>404 on code not found.                                 |
| POST    | `/auth/register` | Creates a user account                   | 201/200 with name and email,<br>409 on duplicate email, <br>422 on validation failure  |
| POST    | `/auth/login`    | Exchanges credentials for a JWT          | 200 with access token, <br>401 on bad credentials, <br>429 when rate limited           |
| GET     | `/all-links`     | Lists the authenticated user's links     | 200 with list of codes and URLs,<br>401 without a valid token                          |
| DELETE  | `/links/{code}`  | Deletes a link you own                   | 204 on success, <br>401 unauthenticated, <br>403 if not yours, <br>404 if no such code |

## How to run it?
1.  Clone the repo
2. Create the venv : `python -m venv venv`
3. Activate the venv - Windows(Powershell)  `venv\Scripts\Activate.ps1`
4. Install the requirements :  `pip install -r requirements.txt`
5. Copy .env.example to .env and generate the `SECRET_KEY`
6. run the app: `uvicorn main:app --reload`
7. Go to http://127.0.0.1:8000/docs

## Security Decisions

1. Input validation — Pydantic validates at the trust boundary; malformed input never reaches the handler.
2. SQL injection prevention — all queries ORM-generated and parameterized; the database parses structure before seeing values, so input can't become syntax.
3. Code uniqueness — a database-level unique constraint rather than application logic, because check-then-write isn't atomic and can't guarantee uniqueness under concurrent requests.
4. Unguessable codes — `secrets` rather than `random`, 7 alphanumeric characters (~3.5 trillion combinations) so codes can't be enumerated.
5. Password Storage
    - Argon2 specifically, over bcrypt or SHA-256 — it's OWASP's current first recommendation and resists GPU-based cracking
    - Per-user salts, so identical passwords produce different hashes and precomputed rainbow tables are useless.
    - Deliberately slow parameters — the cost per hash is negligible for one login but makes brute-forcing impractical.
6. The password hash is excluded from API responses by the response model
7. Authentication
    - Signing key read from environment variables, never committed; .env gitignored with a .env.example documenting required config
    - Token expiry (30 min) bounds the damage window if a token leaks
    - algorithms pinned explicitly on decode, preventing algorithm-substitution attacks such as alg: none
    - Generic 401 for both wrong password and unknown email, so responses don't reveal which emails are registered
    - Dummy hash verified on the unknown-email path so response timing doesn't leak registration status either
    - Unexpired, validly-signed tokens still rejected if the user no longer exists
8. Authorization
    - GET /all-links scopes by owner_id in the query itself, so a user's results can only ever contain their own rows
    - delete checks ownership against the authenticated user's id before acting
    - 404 and 403 are distinct: a missing code returns 404, an existing code owned by someone else returns 403. 
9. Rate limiting
    - Login capped at 5/minute per IP to make password brute-forcing impractical
    - Link creation capped to limit abuse


## Known Limitations
1. `HttpUrl` validates URL structure, not destination safety - no scheme allowlisting, no blocking of internal addresses, no reputation checking. A production shortener would need all three, since it redirects users to attacker-supplied destinations.
2. SQLite is single-machine; Postgres would be needed for concurrent writes across instances.
3. Short codes are bearer capabilities: anyone who obtains one can resolve the link. That's necessary for a shortener to function, but it means codes leaked via screenshots, browser history, or referrer headers grant access. Per-link passwords or expiry would be needed for genuinely private links.
4. Rate limiting is per-IP and in-memory, so it resets on restart and doesn't hold across multiple instances. A shared store like Redis would be needed in production.
5. Behind a proxy or load balancer, the observed client IP is the proxy's unless X-Forwarded-For is handled — relevant once deployed