# NoteFlow — Multi-user Full-Stack Notes App

NoteFlow is a responsive note-taking web application built with Python, Flask, SQLite, SQLAlchemy, HTML, CSS and JavaScript. Users can register, sign in, and manage a private collection of notes.

## Features

- User registration and login
- Secure password hashing (passwords are never stored as plain text)
- Session-based authentication
- Per-user note ownership and access checks
- Create, view, edit and delete notes
- Pin/unpin important notes
- Search notes by title or content
- Responsive UI
- JSON REST API with CSRF protection
- SQLite persistence

## Technology

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python, Flask |
| Authentication | Flask-Login |
| Database / ORM | SQLite, Flask-SQLAlchemy |
| Form and CSRF protection | Flask-WTF |
| API communication | Fetch API, JSON, HTTP |

## Run locally (Windows PowerShell)

1. Install Python 3.10 or newer.
2. Open this folder in VS Code.
3. Create a virtual environment:

   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

4. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

5. Set a strong secret key before running outside local development:

   ```powershell
   $env:SECRET_KEY = "replace-this-with-a-long-random-secret"
   ```

6. Start the app:

   ```powershell
   python app.py
   ```

7. Visit `http://127.0.0.1:5000`, create an account, and add notes.

## Database

The app creates `instance/noteflow_accounts.db` automatically. It contains `user` and `note` tables. Each note has a `user_id` foreign key linking it to its owner.

The upgraded app uses a **new database filename** so that the earlier single-user `instance/noteflow.db` file remains untouched. Existing notes from the earlier version are not automatically imported into user accounts.

## Request and data flow

1. A visitor registers or signs in.
2. Flask verifies the password hash and creates an authenticated session.
3. The browser sends note requests as JSON using `fetch()`.
4. Flask checks the session and CSRF token.
5. The backend reads or writes only rows belonging to `current_user.id`.
6. SQLite stores the records; Flask returns JSON to the browser.

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/notes` | List the signed-in user's notes |
| GET | `/api/notes?q=term` | Search the signed-in user's notes |
| POST | `/api/notes` | Create a note for the signed-in user |
| PUT | `/api/notes/<id>` | Update an owned note |
| PATCH | `/api/notes/<id>/pin` | Toggle pin on an owned note |
| DELETE | `/api/notes/<id>` | Delete an owned note |
| GET | `/api/health` | Health check |

All note endpoints require authentication. The backend filters records by the current user's ID and verifies ownership for update, pin and delete operations.

## Security and production notes

- Passwords are hashed using Werkzeug's password hashing helpers.
- CSRF protection is enabled for form submissions and JSON API requests.
- Note endpoints require login and enforce record ownership.
- For production, set a strong random `SECRET_KEY`, disable Flask debug mode, use HTTPS, configure secure cookies, use a production WSGI server, and consider PostgreSQL plus database migrations.
- This learning project is not a substitute for a professional security audit.
