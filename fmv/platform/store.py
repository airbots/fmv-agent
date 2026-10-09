import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

def now(): return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.path=str(path)
        with self.connect() as c:
            c.executescript('CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, ticker TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL, error TEXT);\nCREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, ts TEXT NOT NULL, step TEXT NOT NULL, message TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS artifacts(id INTEGER PRIMARY KEY AUTOINCREMENT,task_id TEXT NOT NULL,path TEXT NOT NULL,sha256 TEXT NOT NULL);')
    def connect(self):
        c=sqlite3.connect(self.path,timeout=20)
        c.row_factory=sqlite3.Row
        return c
    def submit(self,id,ticker,payload):
        with self.connect() as c:
            c.execute('INSERT INTO tasks(id,ticker,payload,status,updated_at) VALUES (?,?,?,?,?)',(id,ticker,json.dumps(payload),'PENDING',now()))
    def claim(self):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute("SELECT * FROM tasks WHERE status='PENDING' ORDER BY updated_at LIMIT 1").fetchone()
            if row:
                c.execute("UPDATE tasks SET status='RUNNING', attempts=attempts+1, updated_at=? WHERE id=?",(now(),row['id']))
                return dict(row)
            return None
    def update(self,id,status,error=None):
        with self.connect() as c: c.execute('UPDATE tasks SET status=?,error=?,updated_at=? WHERE id=?',(status,error,now(),id))
    def event(self,id,step,message):
        with self.connect() as c: c.execute('INSERT INTO events(task_id,ts,step,message) VALUES (?,?,?,?)',(id,now(),step,message))
    def add_artifact(self,id,path,digest):
        with self.connect() as c: c.execute('INSERT INTO artifacts(task_id,path,sha256) VALUES (?,?,?)',(id,path,digest))
    def tasks(self):
        with self.connect() as c: return [dict(x) for x in c.execute('SELECT id,ticker,status,updated_at,error FROM tasks ORDER BY updated_at DESC')]
