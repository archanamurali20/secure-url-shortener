# Secure URL Shortener

A URL shortener API built as a vehicle for practising secure backend development, with each security control chosen deliberately.

## Tech Stack
- Python
- FastAPI
- SQLModel/SQLAlchemy
- SQLite
- Pydantic

## Endpoints
| Methods | Path            | Description                                                           | Response                                                                                        |
| ------- | --------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| GET     | `/health`       | Standard health check to see if the service is running and responsive | 200 status: ok                                                                                  |
| POST    | `/links`        | arguments: long_url<br>Creates a code for the given url               | 200-> The assigned code is returned<br><br>422 -> The link is not of type `HttpUrl`    |
| GET     | `/links/{code}` | Arguments: code<br>For the given code the corresponding url is sent   | 200 -> The exact corresponding url link is returned.<br><br>404 -> The given code is not found. |

## How to run it?
1.  Clone the repo
2. Create the venv : `python -m venv venv`
3. Activate the venv - Windows(Powershell)  `venv\Scripts\Activate.ps1`
4. Install the requirements :  `pip install -r requirements.txt`
5. run the app: `uvicorn main:app --reload`
6. Go to http://127.0.0.1:8000/docs

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


## Known Limitations
1. `HttpUrl` validates URL structure, not destination safety - no scheme allowlisting, no blocking of internal addresses, no reputation checking. A production shortener would need all three, since it redirects users to attacker-supplied destinations.

2. SQLite is single-machine; Postgres would be needed for concurrent writes across instances.