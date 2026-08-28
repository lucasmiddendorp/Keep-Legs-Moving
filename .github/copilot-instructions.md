# Cycling Analytics — Copilot Instructions

## Project

This is a Streamlit cycling analytics application using:

- Python
- Streamlit
- PostgreSQL
- psycopg2
- Strava API / stravalib
- pandas
- NumPy

The application provides:
- Strava authentication
- User authentication
- Athlete settings
- Activity synchronization
- Training load metrics
- Course pacing
- Training plans
- Workout builder
- Athlete availability

## Database

PostgreSQL is the source of truth for persistent user data.

Use PostgreSQL for:
- users
- user_settings
- training_goals
- strava_accounts
- availability
- OAuth state

Do NOT reintroduce YAML or JSON as a database for user information.

Streamlit secrets are used for:
- PostgreSQL connection URL
- Strava client ID
- Strava client secret
- other secrets

Never hardcode credentials or API secrets.

## Code style

Keep existing code style unless there is a good reason to change it.

IMPORTANT:
- Do not add unnecessary blank lines.
- Do not insert multiple consecutive empty lines.
- Do not reformat unrelated code.
- Do not change indentation unless required.
- Keep functions compact and readable.
- Prefer small targeted changes.
- Do not rewrite an entire file when only one function needs changing.
- Preserve existing variable names unless changing them is necessary.
- Do not add comments that merely restate obvious code.

Use normal PEP 8 formatting, but prioritize consistency with the existing project.

## Editing behavior

Before changing code:
1. Inspect the relevant files.
2. Understand existing imports and dependencies.
3. Identify how the relevant functions are currently used.
4. Make the smallest change that solves the problem.

Do not:
- create duplicate functions
- create alternative implementations without being asked
- introduce new libraries without asking
- migrate architecture unnecessarily
- modify unrelated files
- remove working functionality

If a function already exists, modify it instead of creating another function with a similar purpose.

## Streamlit

Use Streamlit session state only for temporary UI state.

Persistent user data belongs in PostgreSQL.

Avoid unnecessary st.rerun() calls.

Keep authentication and page routing centralized.

## Strava

Use the existing Strava modules.

Keep OAuth logic separate from:
- database logic
- UI logic
- activity synchronization

Access tokens and refresh tokens must never be printed or exposed.

OAuth state must be persistent across the external Strava redirect.

## PostgreSQL

Use parameterized SQL.

Always close database connections.

Use transactions for writes.

Do not silently swallow database errors.

Prefer existing helpers in helpers/database.py rather than creating new database connection logic.

## Debugging

When fixing an error:
- identify the root cause first
- make the smallest fix
- explain the cause briefly
- do not refactor unrelated code

If the error is caused by missing configuration, identify the exact configuration that is missing.

## Output

When asked to modify code:
- make the change directly
- show only the relevant changed code unless the full file is explicitly requested
- Explain changes with short bullet points, not whole paragraphs
- do not explain obvious Python syntax
- do not repeat the user's code unnecessarily