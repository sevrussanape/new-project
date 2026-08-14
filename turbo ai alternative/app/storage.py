from __future__ import annotations
import sqlite3, json
from pathlib import Path
DB=Path(__file__).resolve().parents[1]/'data'/'studyai.db'
DB.parent.mkdir(parents=True,exist_ok=True)

def conn():
    c=sqlite3.connect(DB); c.execute('CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)'); c.execute('CREATE TABLE IF NOT EXISTS sources(id INTEGER PRIMARY KEY AUTOINCREMENT,course_id INTEGER,name TEXT,type TEXT,text TEXT)'); c.execute('CREATE TABLE IF NOT EXISTS activity(id INTEGER PRIMARY KEY AUTOINCREMENT,course_id INTEGER,kind TEXT,payload TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)'); c.commit(); return c

def create_course(name):
    c=conn(); cur=c.execute('INSERT INTO courses(name) VALUES(?)',(name,)); c.commit(); i=cur.lastrowid; c.close(); return i

def courses():
    c=conn(); rows=c.execute('SELECT id,name,created FROM courses ORDER BY id DESC').fetchall(); c.close(); return rows

def add_source(course_id,name,kind,text):
    c=conn(); c.execute('INSERT INTO sources(course_id,name,type,text) VALUES(?,?,?,?)',(course_id,name,kind,text)); c.commit(); c.close()

def sources(course_id):
    c=conn(); rows=c.execute('SELECT id,name,type,text FROM sources WHERE course_id=?',(course_id,)).fetchall(); c.close(); return rows

def save_activity(course_id,kind,payload):
    c=conn(); c.execute('INSERT INTO activity(course_id,kind,payload) VALUES(?,?,?)',(course_id,kind,json.dumps(payload))); c.commit(); c.close()

def activity(course_id):
    c=conn(); rows=c.execute('SELECT kind,payload,created FROM activity WHERE course_id=? ORDER BY id DESC',(course_id,)).fetchall(); c.close(); return rows
