from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
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

def listToString(tags):
    return ",".join(tags)

def stringToList(str):
    return str.split(",") if str else []

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

            conn.commit()

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

@app.post("/notes", response_model=NoteResponse)
async def createNote(note: NoteCreate):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("INSERT INTO notes (title, body, tags) VALUES (?, ?, ?)",
                           (note.title, note.body, listToString(note.tags)))
            
            conn.commit()

            # get id of newly created row
            new_id = cursor.lastrowid
            
            # retrieve new row
            cursor.execute("SELECT * FROM notes WHERE id = ?",
                        (new_id,))
            row = cursor.fetchone()

        # turn sqlite row into python dictionary
        ordered_data = dict(row)

        # convert tag string into list
        ordered_data["tags"] = stringToList(ordered_data["tags"])

        return ordered_data
    
    except sqlite3.OperationalError as exc:
        print(f"SQLite operational error: {exc}")
    except sqlite3.Error as exc:
        print(f"SQLite error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")

@app.get("/notes", response_model=List[NoteResponse])
async def getNotes(id: int):
    output = []

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # retrieve all notes
            cursor.execute("SELECT * FROM notes")
            rows = cursor.fetchall()

            for row in rows:
                row_dict = dict(row)
                row_dict["tags"] = stringToList(row_dict["tags"])
                output.append(row_dict)

        return output
    
    except sqlite3.OperationalError as exc:
        print(f"SQLite operational error: {exc}")
    except sqlite3.Error as exc:
        print(f"SQLite error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")

@app.get("/notes/{id}", response_model=NoteResponse)
async def getNote(id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM notes WHERE id = ?",
                           (id,))
            row = cursor.fetchone()

            # throw 404 error if id does not exist
            if row is None:
                raise HTTPException(status_code=404, detail="Note not found")

            row_dict = dict(row)
            row_dict["tags"] = stringToList(row_dict["tags"])
            
        return row_dict
    
    except HTTPException as exc:
        raise exc
    except sqlite3.OperationalError as exc:
        print(f"SQLite operational error: {exc}")
    except sqlite3.Error as exc:
        print(f"SQLite error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")