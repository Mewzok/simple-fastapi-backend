# Notes API

A simple FastAPI application for creating, reading, updating, and deleting notes backed by SQLite.

## Description

This project provides a REST API for managing notes with the following fields:

* `title` — note title
* `body` — note content
* `tags` — optional list of strings
* `created_at` — date and time when the note was created

The app stores notes in a local SQLite database file named `notes.db`.

## Requirements

* Python 3.10 or newer
* `fastapi`
* `uvicorn`

## Installing

1. Open a terminal in the project folder.
2. (Optional) Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

## Running the API

From the project directory, run:

```powershell
uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000` in your browser.

## API Endpoints

* `GET /` — health check
* `POST /notes` — create a new note
* `GET /notes` — list all notes, optional `tag` filter
* `GET /notes/{id}` — retrieve a note by ID
* `PUT /notes/{id}` — update a note by ID
* `DELETE /notes/{id}` — delete a note by ID

### Example payload for creating or updating a note

```json
{
  "title": "Shopping list",
  "body": "Buy milk, eggs, and bread",
  "tags": ["personal", "shopping"]
}
```

### Example response

```json
{
  "id": 1,
  "title": "Shopping list",
  "body": "Buy milk, eggs, and bread",
  "tags": ["personal", "shopping"],
  "created_at": "2026-06-26 03:52:20"
}
```

## Notes

* The database is created automatically when the app starts.
* Tags are stored in SQLite as JSON and returned as an array.
* `created_at` is set automatically by the database when the note is created.

## License

This project is licensed under the [MIT License](LICENSE).
