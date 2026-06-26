import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

import sqlite3
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

DB_PATH = Path(__file__).resolve().parent / "notes.db"
logger = logging.getLogger(__name__)


class NoteCreate(BaseModel):
    title: str
    body: str
    tags: Optional[List[str]] = None


class NoteResponse(BaseModel):
    id: int
    title: str
    body: str
    tags: List[str]
    created_at: str


def normalize_tags(tags: Optional[List[str]]) -> List[str]:
    return tags or []


def tags_to_db_value(tags: Optional[List[str]]) -> str:
    return json.dumps(normalize_tags(tags))


def tags_from_db_value(value: Optional[str]) -> List[str]:
    if not value:
        return []

    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        return []
    except json.JSONDecodeError:
        logger.warning("Invalid tags stored for note: %s", value)
        return [item.strip() for item in value.split(",") if item.strip()]


def row_to_note(row: sqlite3.Row) -> dict:
    note = dict(row)
    note["tags"] = tags_from_db_value(note.get("tags"))
    return note


def get_db_connection() -> sqlite3.Connection:
    return sqlite3.connect(str(DB_PATH), timeout=30.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL DEFAULT (DATE('now', 'localtime'))
                )
                """
            )
            conn.commit()
    except sqlite3.Error as exc:
        logger.exception("Database initialization failed")
        raise RuntimeError("Unable to initialize database") from exc
    except Exception as exc:
        logger.exception("Unexpected startup failure")
        raise RuntimeError("Startup failed") from exc

    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


def handle_db_error(exc: Exception, message: str):
    logger.exception(message)
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error") from exc


@app.post("/notes", response_model=NoteResponse)
async def create_note(note: NoteCreate):
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO notes (title, body, tags) VALUES (?, ?, ?)",
                (note.title, note.body, tags_to_db_value(note.tags)),
            )
            conn.commit()

            new_id = cursor.lastrowid
            cursor.execute("SELECT * FROM notes WHERE id = ?", (new_id,))
            row = cursor.fetchone()

        if row is None:
            logger.error("Created note not found after insert: %s", new_id)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve created note")

        return row_to_note(row)
    except sqlite3.Error as exc:
        handle_db_error(exc, "Database error while creating note")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error while creating note")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from exc


@app.get("/notes", response_model=List[NoteResponse])
async def get_notes(tag: Optional[str] = None):
    output: List[dict] = []
    query = "SELECT * FROM notes"
    params: List[str] = []

    if tag and tag.strip():
        query += " WHERE tags LIKE ?"
        params.append(f'%"{tag}"%')

    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

        for row in rows:
            output.append(row_to_note(row))

        return output
    except sqlite3.Error as exc:
        handle_db_error(exc, "Database error while listing notes")
    except Exception as exc:
        logger.exception("Unexpected error while listing notes")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from exc


@app.get("/notes/{id}", response_model=NoteResponse)
async def get_note(id: int):
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (id,))
            row = cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

        return row_to_note(row)
    except sqlite3.Error as exc:
        handle_db_error(exc, f"Database error while fetching note {id}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error while fetching note %s", id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from exc


@app.put("/notes/{id}", response_model=NoteResponse)
async def update_note(id: int, note: NoteCreate):
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE notes SET title = ?, body = ?, tags = ? WHERE id = ?",
                (note.title, note.body, tags_to_db_value(note.tags), id),
            )
            conn.commit()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (id,))
            row = cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

        return row_to_note(row)
    except sqlite3.Error as exc:
        handle_db_error(exc, f"Database error while updating note {id}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error while updating note %s", id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from exc


@app.delete("/notes/{id}", response_model=NoteResponse)
async def delete_note(id: int):
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (id,))
            row = cursor.fetchone()

            if row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

            note = row_to_note(row)
            cursor.execute("DELETE FROM notes WHERE id = ?", (id,))
            conn.commit()

        return note
    except sqlite3.Error as exc:
        handle_db_error(exc, f"Database error while deleting note {id}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error while deleting note %s", id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from exc
