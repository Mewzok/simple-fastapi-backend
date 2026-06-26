from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
import sqlite3

DB_PATH = "notes.db"

class NoteCreate(BaseModel):
    title: str
    body: str
    tags: Optional[List[str]] = []

class NoteResponse(BaseModel):
    id: int
    title: str
    body: str
    tags: List[str]
    created_at: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    tags TEXT,
                    created_at TEXT NOT NULL DEFAULT (DATE('now', 'localtime'))
                )
                """
            )

    except sqlite3.OperationalError as exc:
        print(f"SQLite operational error: {exc}")
    except sqlite3.Error as exc:
        print(f"SQLite error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")

    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Hello World"}