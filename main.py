from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import sqlite3

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key='verysecretkey')
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_PATH = "/data/staff.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                points REAL NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        ''')
        conn.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", ('admin', 'admin123'))
init_db()

def get_user(request: Request):
    return request.session.get("user")

def fetch_staff():
    with sqlite3.connect(DB_PATH) as conn:
        data = conn.execute("SELECT * FROM staff ORDER BY points DESC").fetchall()
    return [{
        "id": row[0],
        "name": row[1],
        "points": row[2],
        "place": i + 1
    } for i, row in enumerate(data)]

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_user(request)
    ranked = fetch_staff()
    return templates.TemplateResponse("index.html", {"request": request, "user": user, "staff": ranked})

@app.get("/data")
async def get_data():
    return JSONResponse(fetch_staff())

@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    with sqlite3.connect(DB_PATH) as conn:
        result = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
    if result:
        request.session["user"] = username
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин или пароль"})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)

@app.post("/add")
async def add_staff(request: Request, name: str = Form(...), points: float = Form(...)):
    if get_user(request) != "admin":
        raise HTTPException(status_code=403)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO staff (name, points) VALUES (?, ?)", (name, points))
    return JSONResponse({"status": "ok"})

@app.post("/delete")
async def delete_staff(request: Request, staff_id: int = Form(...)):
    if get_user(request) != "admin":
        raise HTTPException(status_code=403)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM staff WHERE id=?", (staff_id,))
    return JSONResponse({"status": "ok"})
