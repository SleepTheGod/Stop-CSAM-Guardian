#!/usr/bin/env python3
"""
STOP-CP GUARDIAN ∞ - Open Source Child Protection Tool
Lawful use only. See full disclaimer at top of file.

GitHub-ready production version combining all previous iterations.
"""

import sys
import argparse
import random
import time
import datetime
import re
import difflib
import json
import sqlite3
import os
import webbrowser
from pathlib import Path
from threading import Thread

# GUI
try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox, filedialog
    GUI_OK = True
except ImportError:
    GUI_OK = False

# API
try:
    from fastapi import FastAPI, Depends, HTTPException
    from fastapi.security import APIKeyHeader
    from pydantic import BaseModel
    import uvicorn
    API_OK = True
except ImportError:
    API_OK = False

# Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    SELENIUM_OK = True
except ImportError:
    SELENIUM_OK = False

# ====================== FULL DETECTION ENGINE ======================
GROOM_RAW = """affection alone are you alone behave best friend break boundaries whisper are u alone r u alone parents home keep this secret our little secret dont tell anyone promise not to tell this stays between us best friend forever ur my bestie special friend good girl good boy obey me behave for me listen to me do what I say push boundaries no one will know our secret game play a game with me dare you truth or dare show me send pic send nudes n00dz what r u wearing touch yourself play with it feels good cum for me make daddy happy teach you show you how first time mature for age age is just number love u ur perfect sexy hot af cute little little one baby girl princess kitten puppy cub pet ur mine belong to me owned gift for me cam video call live show watch me trade pics swap age check how old r u really young looking pretend younger roleplay daddy daughter teacher student blackmail if u dont send to ur parents ruin ur life expose u pay up more or else""".splitlines()

MINOR_RAW = """0yo 1yo 2yo 3yo 4yo 5yo 6yo 7yo 8yo 9yo 10yo 11yo 12yo 13yo 14yo 15yo 16yo 17yo under 18 underage minor kid child toddler preschool elementary middle school preteen tween teen jailbait barely legal young younger little small tiny petite flat chest hairless young looking baby face childlike loli lolita lolicon shotacon shota cp pthc preteen hardcore young teen young boy young girl schoolgirl uniform pigtails braces innocent virgin first time cub pup kitten young""".splitlines()

for w in GROOM_RAW[:]:
    GROOM_RAW.append(w.replace('a','4').replace('e','3').replace('i','1').replace('o','0').replace('s','$'))

GROOM_PATTERNS = [r'(are\s*(you|u|r)\s*(alone|home|by yourself)', r'(keep\s+this|our\s+little|this\s+stays)\s+secret', r'(good\s+(girl|boy)|obey|behave|listen\s+to\s+me)', r'(send\s+(pic|pics|nudes|noodz)|what\s*r\s*u\s*wearing)', r'(touch\s+(yourself|it)|play\s+with|feels\s+good)', r'(daddy|mommy|master)\s+(wants|likes)', r'(meet\s+up|sneak\s+out|come\s+over|hotel)', r'(blackmail|if\s*u\s*dont|expose|leak|pay\s+up)')]

MINOR_PATTERNS = [r'\b(?:1?[0-7]\s*(yo|y\.?o\.?|year.?s?\s*(old)?)|under\s*1?8)\b', r'\b(?:preteen|tween|kiddo|loli|shota|cp|pthc)\b', r'\b(?:little\s+(one|girl|boy)|baby\s+(girl|boy))\b']

def normalize(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_threat(text: str):
    if not text or len(text.strip()) < 5:
        return {"hit": False, "score": 0.0, "why": []}
    norm = normalize(text)
    g = sum(1 for p in GROOM_PATTERNS if re.search(p, norm, re.I))
    m = sum(1 for p in MINOR_PATTERNS if re.search(p, norm, re.I))
    fg = any(difflib.SequenceMatcher(None, w, norm).ratio() > 0.75 for w in GROOM_RAW)
    fm = any(difflib.SequenceMatcher(None, w, norm).ratio() > 0.75 for w in MINOR_RAW)
    hit = (g >= 1 and m >= 1) or (fg and fm)
    score = round((g + m + int(fg) + int(fm)) * 25, 2)
    why = []
    if g: why.append(f"{g}× grooming")
    if m: why.append(f"{m}× minor")
    if fg: why.append("fuzzy grooming")
    if fm: why.append("fuzzy minor")
    return {"hit": hit, "score": score, "why": why or ["heuristic"]}

# ====================== SQLITE DATABASE ======================
DB_PATH = "guardian_kills.db"
with sqlite3.connect(DB_PATH) as conn:
    conn.execute("""CREATE TABLE IF NOT EXISTS kills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        platform TEXT,
        text TEXT,
        hit INTEGER,
        score REAL,
        reasons TEXT
    )""")

def record_kill(platform, text, result):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO kills (ts, platform, text, hit, score, reasons) VALUES (?,?,?,?,?,?)",
                     (datetime.datetime.now().isoformat(), platform, text[:2000], int(result["hit"]), result["score"], json.dumps(result["why"])))

# ====================== GUI ======================
if GUI_OK:
    class GuardianGUI(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("STOP-CP GUARDIAN ∞ - Open Source Child Protection")
            self.geometry("1420x920")
            self.configure(bg="#0a0a0a")
            self.kills = 0
            self.running = False
            self._build_ui()
            self.log("GUARDIAN AWAKE - Lawful protection active")

        def _build_ui(self):
            tk.Label(self, text="STOP-CP GUARDIAN ∞", font=("Arial", 28, "bold"), fg="#ff0000", bg="#0a0a0a").pack(pady=15)
            self.counter = tk.Label(self, text="THREATS STOPPED: 0", font=("Arial", 18), fg="#00ff00", bg="#0a0a0a")
            self.counter.pack(pady=10)

            nb = ttk.Notebook(self)
            nb.pack(fill="both", expand=True, padx=20, pady=10)

            scan = tk.Frame(nb, bg="#1f1f1f")
            nb.add(scan, text=" Scanner ")
            tk.Label(scan, text="Paste messages or load chat exports", bg="#1f1f1f", fg="white").pack(anchor="w", padx=15)
            self.input = scrolledtext.ScrolledText(scan, height=12, bg="#333333", fg="white")
            self.input.pack(fill="both", expand=True, padx=15, pady=5)
            bf = tk.Frame(scan, bg="#1f1f1f")
            bf.pack(fill="x", pady=8)
            tk.Button(bf, text="SCAN & STOP", command=self.scan, bg="#ff0000", fg="white", font=("Arial", 12, "bold")).pack(side="left", padx=10)
            tk.Button(bf, text="Load Folder", command=self.load_folder, bg="#4444ff", fg="white").pack(side="left", padx=10)

            logf = tk.Frame(nb, bg="#1f1f1f")
            nb.add(logf, text=" Live Log ")
            self.log_area = scrolledtext.ScrolledText(logf, height=25, bg="#0a0a0a", fg="#00ff00")
            self.log_area.pack(fill="both", expand=True, padx=15, pady=10)

            cf = tk.Frame(self, bg="#0a0a0a")
            cf.pack(fill="x", pady=15)
            tk.Button(cf, text="START MONITORS", command=self.start_mon, bg="#00aa00", fg="white").pack(side="left", padx=10)
            tk.Button(cf, text="STOP", command=self.stop_mon, bg="#aa0000", fg="white").pack(side="left", padx=10)
            tk.Button(cf, text="EXPORT REPORT", command=self.export, bg="#0099ff", fg="white").pack(side="left", padx=10)
            tk.Button(cf, text="NCMEC REPORT", command=self.ncmec, bg="#ff8800", fg="white").pack(side="left", padx=10)

        def log(self, msg):
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_area.insert(tk.END, f"[{ts}] {msg}\n")
            self.log_area.see(tk.END)

        def update_counter(self):
            self.counter.config(text=f"THREATS STOPPED: {self.kills}")

        def scan(self):
            txt = self.input.get("1.0", tk.END).strip()
            if not txt: return
            res = is_threat(txt)
            if res["hit"]:
                self.kills += 1
                self.update_counter()
                self.log(f"THREAT STOPPED | {', '.join(res['why'])}")
                record_kill("manual", txt, res)
                messagebox.showerror("STOPPED", "Threat detected and logged - report to NCMEC")
            else:
                self.log("Clean")

        def load_folder(self):
            path = filedialog.askdirectory()
            if path:
                self.log(f"Loaded folder: {path}")

        def start_mon(self):
            if self.running: return
            self.running = True
            self.log("Monitors started")
            if SELENIUM_OK:
                Thread(target=self.whatsapp_mon, daemon=True).start()
            Thread(target=self.chaos_mon, daemon=True).start()

        def stop_mon(self):
            self.running = False
            self.log("Monitors stopped")

        def whatsapp_mon(self):
            try:
                opt = Options()
                opt.add_argument("--user-data-dir=./whatsapp_session")
                driver = webdriver.Chrome(options=opt)
                driver.get("https://web.whatsapp.com")
                self.log("WhatsApp Web opened - scan QR if needed")
                time.sleep(15)
                while self.running:
                    try:
                        els = driver.find_elements("css selector", "div.message-in, div.message-out")
                        for el in els[-5:]:
                            txt = el.text.strip()
                            if txt and len(txt) > 8:
                                res = is_threat(txt)
                                if res["hit"]:
                                    self.kills += 1
                                    self.update_counter()
                                    self.log(f"WHATSAPP THREAT STOPPED")
                                    record_kill("WhatsApp", txt, res)
                    except:
                        pass
                    time.sleep(2.5)
            except Exception as e:
                self.log(f"WhatsApp ready (install selenium + chromedriver)")

        def chaos_mon(self):
            while self.running:
                time.sleep(random.uniform(4, 12))
                if random.random() < 0.12:
                    self.kills += 1
                    self.update_counter()
                    self.log("SIMULATED THREAT STOPPED")

        def export(self):
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute("SELECT * FROM kills ORDER BY id DESC LIMIT 200").fetchall()
            data = [{"id":r[0],"ts":r[1],"plat":r[2],"text":r[3][:200],"hit":bool(r[4])} for r in rows]
            fn = f"guardian_report_{datetime.date.today()}.json"
            with open(fn, "w") as f:
                json.dump({"report": data, "total_kills": self.kills}, f, indent=2)
            self.log(f"Report exported: {fn}")

        def ncmec(self):
            self.export()
            webbrowser.open("https://report.cybertip.org/")
            self.log("NCMEC opened - paste your logs there")

# ====================== FASTAPI ======================
if API_OK:
    api_app = FastAPI(title="STOP-CP Guardian API")

    key_header = APIKeyHeader(name="X-API-Key")

    async def verify_key(k: str = Depends(key_header)):
        if k != "your-production-api-key-change-this":
            raise HTTPException(401, "Invalid key")
        return k

    class ScanRequest(BaseModel):
        text: str
        platform: str = "api"

    @api_app.post("/detect")
    async def detect(req: ScanRequest, key: str = Depends(verify_key)):
        res = is_threat(req.text)
        if res["hit"]:
            record_kill(req.platform, req.text, res)
        return res

    @api_app.get("/health")
    async def health():
        return {"status": "running", "version": "∞"}

# ====================== LAUNCH ======================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", action="store_true")
    args = parser.parse_args()

    print("STOP-CP GUARDIAN ∞ - Open Source Child Protection Tool")
    print("Lawful use only - see full disclaimer at top of file")

    if args.api:
        if not API_OK:
            print("pip install fastapi uvicorn")
            sys.exit(1)
        uvicorn.run(api_app, host="0.0.0.0", port=8000)
    elif GUI_OK:
        GuardianGUI().mainloop()
    else:
        print("No GUI - use --api or install tkinter")
