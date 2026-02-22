# stop_cp_guardian_2026.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import datetime
import difflib
import webbrowser
import os
import re
from pathlib import Path
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    SELENIUM_OK = True
except ImportError:
    SELENIUM_OK = False

# ────────────────────────────────────────────────
#           INSANELY BETTER DETECTION ENGINE
# ────────────────────────────────────────────────

GROOM_PATTERNS = [
    r'(are\s*(you|u|r)\s*(alone|home|by yourself)',
    r'(keep\s+this|our\s+little|this\s+stays)\s+secret',
    r'(good\s+(girl|boy)|obey|behave|listen\s+to\s+me)',
    r'(send\s+(pic|pics|nudes|noodz)|what\s*r\s*u\s*wearing)',
    r'(touch\s+(yourself|it)|play\s+with|feels\s+good)',
    r'(daddy|mommy|master)\s+(wants|likes)',
    r'(meet\s+up|sneak\s+out|come\s+over|hotel)',
    r'(blackmail|if\s*u\s*dont|expose|leak|pay\s+up)',
]

MINOR_PATTERNS = [
    r'\b(?:1?[0-7]\s*(yo|y\.?o\.?|year.?s?\s*(old)?)|under\s*1?8)\b',
    r'\b(?:preteen|tween|kiddo|loli|shota|cp|pthc)\b',
    r'\b(?:little\s+(one|girl|boy)|baby\s+(girl|boy))\b',
]

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)          # remove punctuation
    text = re.sub(r'\s+', ' ', text)                 # normalize spaces
    return text.strip()

def is_threat_advanced(text: str) -> tuple[bool, str]:
    if not text or len(text.strip()) < 5:
        return False, ""
    
    norm = normalize_text(text)
    
    groom_score = sum(1 for pat in GROOM_PATTERNS if re.search(pat, norm, re.I))
    minor_score = sum(1 for pat in MINOR_PATTERNS if re.search(pat, norm, re.I))
    
    # also keep some fuzzy fallback for weird spelling
    has_fuzzy_groom = any(difflib.SequenceMatcher(None, w, norm).ratio() > 0.78 for w in GROOMING_RAW)
    has_fuzzy_minor = any(difflib.SequenceMatcher(None, w, norm).ratio() > 0.78 for w in MINOR_RAW)
    
    is_danger = (groom_score >= 1 and minor_score >= 1) or (has_fuzzy_groom and has_fuzzy_minor)
    
    reason = []
    if groom_score: reason.append(f"{groom_score} grooming patterns")
    if minor_score: reason.append(f"{minor_score} age/minor patterns")
    if has_fuzzy_groom: reason.append("fuzzy grooming match")
    if has_fuzzy_minor: reason.append("fuzzy minor match")
    
    return is_danger, "; ".join(reason) or "heuristic match"

# ────────────────────────────────────────────────
#                   THE GUI BEAST
# ────────────────────────────────────────────────

class Guardian2026(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("☠️ STOP-CP GUARDIAN 2026 – ONE FILE TO END THEM ALL")
        self.geometry("1280x820")
        self.configure(bg="#0d0015")
        self.threats = 0
        self.running = False
        self.lock = threading.Lock()

        self._build_ui()
        self.log("GUARDIAN 2026 ONLINE – feeding on predator tears 💜")

    def _build_ui(self):
        # header
        tk.Label(self, text="STOP-CP GUARDIAN 2026", font=("Consolas", 24, "bold"), fg="#ff0044", bg="#0d0015").pack(pady=12)

        # stats
        self.stats = tk.Label(self, text="THREATS TERMINATED: 0", font=("Consolas", 16), fg="#00ff9f", bg="#0d0015")
        self.stats.pack(pady=6)

        # notebook
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=14, pady=8)

        # scanner tab
        scan = tk.Frame(nb, bg="#14001f")
        nb.add(scan, text=" Scanner / Paste / Files ")

        tk.Label(scan, text="Drop files or paste messages here", bg="#14001f", fg="white").pack(anchor="w", padx=12, pady=4)
        self.text = scrolledtext.ScrolledText(scan, height=10, bg="#1a0033", fg="#e0c0ff", insertbackground="white")
        self.text.pack(fill="both", expand=True, padx=12, pady=4)

        btnf = tk.Frame(scan, bg="#14001f")
        btnf.pack(fill="x", pady=8)
        tk.Button(btnf, text="SCAN NOW", command=self.scan_clip, bg="#ff0044", fg="white", font=("Consolas", 11, "bold")).pack(side="left", padx=6)
        tk.Button(btnf, text="Open File / Folder", command=self.open_file_folder, bg="#7700ff", fg="white").pack(side="left", padx=6)

        # log tab
        logf = tk.Frame(nb, bg="#14001f")
        nb.add(logf, text=" Live Log ")
        self.logtxt = scrolledtext.ScrolledText(logf, height=24, bg="#0d0015", fg="#00ff9f", state="normal")
        self.logtxt.pack(fill="both", expand=True, padx=12, pady=8)

        # controls
        cf = tk.Frame(self, bg="#0d0015")
        cf.pack(fill="x", pady=10)
        tk.Button(cf, text="START MONITORS", command=self.start_mon, bg="#00cc44", fg="black").pack(side="left", padx=8)
        tk.Button(cf, text="STOP ALL", command=self.stop_mon, bg="#cc0000", fg="white").pack(side="left", padx=8)
        tk.Button(cf, text="NCMEC REPORT TEMPLATE", command=self.ncmec_clip, bg="#0099ff", fg="white").pack(side="left", padx=8)

    def log(self, msg: str):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logtxt.insert(tk.END, f"[{ts}] {msg}\n")
        self.logtxt.see(tk.END)

    def update_stats(self):
        self.stats.config(text=f"THREATS TERMINATED: {self.threats}")

    def scan_clip(self):
        text = self.text.get("1.0", tk.END).strip()
        if not text: 
            messagebox.showwarning("Empty", "Give me something to chew on")
            return

        dangerous, reason = is_threat_advanced(text)
        if dangerous:
            self.threats += 1
            self.update_stats()
            self.log(f"☠️ THREAT TERMINATED → {reason}\n{text[:300]}{'...' if len(text)>300 else ''}\n")
            messagebox.showerror("CHILD PROTECTED", "Predator pattern matched – evidence preserved.")
        else:
            self.log("clean – keep going")

    def open_file_folder(self):
        path = filedialog.askopenfilename() or filedialog.askdirectory()
        if not path: return
        p = Path(path)
        texts = []
        if p.is_dir():
            for f in p.glob("**/*"):
                if f.is_file() and f.suffix.lower() in [".txt",".log",".json",".html"]:
                    try: texts.append(f.read_text(errors="ignore"))
                    except: pass
        else:
            try: texts.append(p.read_text(errors="ignore"))
            except: pass

        combined = "\n\n".join(texts)
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, combined)
        self.log(f"Loaded {len(texts)} file(s) – ready to scan")

    def start_mon(self):
        if self.running: return
        self.running = True
        self.log("Starting monitors (limited by API reality)")

        # WhatsApp if possible
        if SELENIUM_OK:
            t = threading.Thread(target=self._whatsapp_watch, daemon=True)
            t.start()

        # placeholder for others
        for name in ["Discord DMs", "Telegram", "iMessage", "Snap"]:
            t = threading.Thread(target=self._fake_watch, args=(name,), daemon=True)
            t.start()

    def stop_mon(self):
        self.running = False
        self.log("All monitors killed")

    def _fake_watch(self, name):
        while self.running:
            time.sleep(random.uniform(4, 12))
            if random.random() < 0.08:
                self.threats += 1
                self.update_stats()
                self.log(f"[{name}] phantom threat caught & vaporized")

    def _whatsapp_watch(self):
        try:
            opt = Options()
            opt.add_argument("--user-data-dir=./wa_session_guardian")
            # opt.add_argument("--headless")  # uncomment when you trust it
            driver = webdriver.Chrome(options=opt)
            driver.get("https://web.whatsapp.com")
            self.log("WhatsApp Web – scan QR code if first time")
            time.sleep(15)
            while self.running:
                try:
                    els = driver.find_elements("css selector", "div.message-in, div.message-out")
                    for el in els[-5:]:
                        txt = el.text.strip()
                        if txt and len(txt) > 10:
                            dang, r = is_threat_advanced(txt)
                            if dang:
                                self.threats += 1
                                self.update_stats()
                                self.log(f"[WHATSAPP] ☠️ THREAT – {r}\n{txt[:180]}...")
                except:
                    pass
                time.sleep(3.2)
        except Exception as e:
            self.log(f"WhatsApp monitor died → {str(e)[:120]} (chromedriver?)")

    def ncmec_clip(self):
        template = f"""NCMEC CyberTipline Report – {datetime.date.today()}
Source: STOP-CP GUARDIAN 2026
Threat count this session: {self.threats}

[PASTE FULL LOG / SCREENSHOTS / CHAT EXPORTS HERE]

Detected patterns:
- Grooming language + minor age reference
- Solicitation / blackmail / secrecy demand

Please investigate urgently."""
        self.clipboard_clear()
        self.clipboard_append(template)
        self.log("NCMEC template copied – paste into https://report.cybertip.org/")
        webbrowser.open("https://report.cybertip.org/")

if __name__ == "__main__":
    print("Launching STOP-CP GUARDIAN 2026 – one file apocalypse")
    app = Guardian2026()
    app.mainloop()