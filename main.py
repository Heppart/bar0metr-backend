from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import sqlite3
import math
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- БАЗА ДАННЫХ (SQLite — для старта, потом замените на PostgreSQL) ---
DB_PATH = "bar0metr.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Пользователи
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id TEXT UNIQUE,
        phone TEXT,
        city TEXT,
        is_verified INTEGER DEFAULT 0,
        is_subscribed INTEGER DEFAULT 0,
        subscribe_until TEXT,
        created_at TEXT
    )''')
    # Заведения
    c.execute('''CREATE TABLE IF NOT EXISTS venues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        address TEXT,
        lat REAL,
        lon REAL,
        category TEXT,
        is_active INTEGER DEFAULT 1,
        demo_until TEXT,
        total_views INTEGER DEFAULT 0,
        checkins_count INTEGER DEFAULT 0
    )''')
    # Отметки "Я здесь"
    c.execute('''CREATE TABLE IF NOT EXISTS checkins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        venue_id INTEGER,
        lat REAL,
        lon REAL,
        created_at TEXT
    )''')
    # Желание познакомиться ("Мне ок")
    c.execute('''CREATE TABLE IF NOT EXISTS interests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        venue_id INTEGER,
        is_active INTEGER DEFAULT 1,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# --- МОДЕЛИ ---
class RegisterRequest(BaseModel):
    tg_id: str
    phone: str = None
    city: str = None

class CheckInRequest(BaseModel):
    tg_id: str
    venue_id: int
    lat: float
    lon: float

class InterestRequest(BaseModel):
    tg_id: str
    venue_id: int

# --- ЭНДПОИНТЫ ---

@app.post("/register")
def register(data: RegisterRequest):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    try:
        c.execute(
            "INSERT INTO users (tg_id, phone, city, created_at) VALUES (?, ?, ?, ?)",
            (data.tg_id, data.phone, data.city, now)
        )
        conn.commit()
        return {"status": "ok", "message": "User registered"}
    except sqlite3.IntegrityError:
        # Пользователь уже есть — обновляем телефон если передан
        if data.phone:
            c.execute("UPDATE users SET phone = ? WHERE tg_id = ?", (data.phone, data.tg_id))
            conn.commit()
        return {"status": "ok", "message": "User already exists"}
    finally:
        conn.close()

@app.get("/map")
def get_map(tg_id: str = None, lat: float = None, lon: float = None):
    """Возвращает список заведений с количеством отметок"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Базовый запрос: все активные заведения
    c.execute("""
        SELECT v.id, v.name, v.address, v.lat, v.lon, v.category, v.demo_until,
               COUNT(c.id) as checkins
        FROM venues v
        LEFT JOIN checkins c ON v.id = c.venue_id 
            AND datetime(c.created_at) > datetime('now', '-2 hours')
        WHERE v.is_active = 1
        GROUP BY v.id
    """)
    rows = c.fetchall()
    conn.close()
    
    venues = []
    for row in rows:
        is_demo = row[6] and datetime.fromisoformat(row[6]) > datetime.utcnow()
        venues.append({
            "id": row[0],
            "name": row[1],
            "address": row[2],
            "lat": row[3],
            "lon": row[4],
            "category": row[5],
            "checkins": row[7] or 0,
            "is_demo": bool(is_demo)
        })
    return {"venues": venues}

@app.post("/checkin")
def checkin(data: CheckInRequest):
    """Отметка 'Я здесь' — проверяем, что пользователь в радиусе 100м от заведения"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Проверяем координаты заведения
    c.execute("SELECT lat, lon FROM venues WHERE id = ?", (data.venue_id,))
    venue = c.fetchone()
    if not venue:
        conn.close()
        raise HTTPException(404, "Venue not found")
    
    # Расстояние между точками (формула гаверсинуса — упрощённо)
    distance = math.hypot(data.lat - venue[0], data.lon - venue[1]) * 111000  # ~км в метры
    if distance > 100:
        conn.close()
        raise HTTPException(400, "You are too far from this venue")
    
    # Находим user_id по tg_id
    c.execute("SELECT id FROM users WHERE tg_id = ?", (data.tg_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        raise HTTPException(404, "User not found")
    
    # Добавляем отметку
    now = datetime.utcnow().isoformat()
    c.execute(
        "INSERT INTO checkins (user_id, venue_id, lat, lon, created_at) VALUES (?, ?, ?, ?, ?)",
        (user[0], data.venue_id, data.lat, data.lon, now)
    )
    # Обновляем счётчик заведения
    c.execute("UPDATE venues SET checkins_count = checkins_count + 1 WHERE id = ?", (data.venue_id,))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Checked in"}

@app.post("/interest")
def set_interest(data: InterestRequest):
    """Пользователь нажал 'Мне ок' в заведении"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT id FROM users WHERE tg_id = ?", (data.tg_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        raise HTTPException(404, "User not found")
    
    now = datetime.utcnow().isoformat()
    # Деактивируем старые интересы этого пользователя в этом заведении
    c.execute(
        "UPDATE interests SET is_active = 0 WHERE user_id = ? AND venue_id = ?",
        (user[0], data.venue_id)
    )
    # Создаём новый активный интерес
    c.execute(
        "INSERT INTO interests (user_id, venue_id, is_active, created_at) VALUES (?, ?, 1, ?)",
        (user[0], data.venue_id, now)
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Interest set"}

@app.get("/venue_stats/{venue_id}")
def venue_stats(venue_id: int):
    """Статистика по заведению для КП"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT 
            COUNT(DISTINCT c.user_id) as unique_users,
            COUNT(c.id) as total_checkins,
            COUNT(DISTINCT i.user_id) as interested_users
        FROM venues v
        LEFT JOIN checkins c ON v.id = c.venue_id
        LEFT JOIN interests i ON v.id = i.venue_id AND i.is_active = 1
        WHERE v.id = ?
    """, (venue_id,))
    row = c.fetchone()
    conn.close()
    
    return {
        "unique_users": row[0] or 0,
        "total_checkins": row[1] or 0,
        "interested_users": row[2] or 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)