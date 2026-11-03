import sqlite3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi_mcp import FastApiMCP

DB_PATH = "todos.db"

app = FastAPI(title="Todo List API")


# ---------- Models ----------

class TodoCreate(BaseModel):
    content: str
    completed: bool = False


class TodoUpdate(BaseModel):
    content: str | None = None
    completed: bool | None = None


class Todo(BaseModel):
    id: int
    content: str
    completed: bool


# ---------- Database helpers ----------

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0
            )
            """
        )


def row_to_todo(row: sqlite3.Row) -> Todo:
    # SQLite has no real boolean type, so we store 0/1 and convert here
    return Todo(id=row["id"], content=row["content"], completed=bool(row["completed"]))


# Create the table when the app starts
init_db()


# ---------- Routes ----------

@app.get("/")
def root():
    return {"message": "Todo API is running. Visit /docs to try it out."}


@app.get("/todos", response_model=list[Todo], operation_id="get_todos")
def list_todos():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM todos").fetchall()
    return [row_to_todo(row) for row in rows]


@app.get("/todos/{todo_id}", response_model=Todo, operation_id="get_todos_by_id")
def get_todo(todo_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return row_to_todo(row)


@app.post("/todos", response_model=Todo, status_code=201, operation_id="add_todos")
def create_todo(todo: TodoCreate):
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO todos (content, completed) VALUES (?, ?)",
            (todo.content, int(todo.completed)),
        )
        new_id = cursor.lastrowid
    return Todo(id=new_id, content=todo.content, completed=todo.completed)


@app.put("/todos/{todo_id}", response_model=Todo, operation_id="update_todos")
def update_todo(todo_id: int, todo: TodoUpdate):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Todo not found")

        existing = row_to_todo(row)
        new_content = todo.content if todo.content is not None else existing.content
        new_completed = todo.completed if todo.completed is not None else existing.completed

        conn.execute(
            "UPDATE todos SET content = ?, completed = ? WHERE id = ?",
            (new_content, int(new_completed), todo_id),
        )
    return Todo(id=todo_id, content=new_content, completed=new_completed)


@app.delete("/todos/{todo_id}", status_code=204, operation_id="delete_todos")
def delete_todo(todo_id: int):
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Todo not found")

mcp = FastApiMCP(
    app,
    include_operations=["get_todos", "get_todos_by_id", "add_todos", "update_todos", "delete_todos"],
)
mcp.mount_http()


##if __name__ == "__main__":
    ##import uvicorn
   ##uvicorn.run(app, host="127.0.0.1", port=8000)