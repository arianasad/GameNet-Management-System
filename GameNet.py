import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time
import json
import os
import csv
from datetime import datetime, date

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "gamenet_data.json")

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def today_str():
    return date.today().isoformat()

def format_toman(n: int) -> str:
    return f"{n:,}"

def seconds_to_hms(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def safe_int(s, default=0):
    try:
        s = str(s).strip().replace(",", "")
        return int(float(s))
    except:
        return default

class GameNetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("گیم‌نت | تایمر و حسابداری (Level 3)")
        self.geometry("1000x590")
        self.minsize(920, 520)

        # ---- theme colors ----
        self.COL_BG = "#0B1220"
        self.COL_CARD = "#121B2E"
        self.COL_TEXT = "#E6EEF9"
        self.COL_MUTED = "#A9B7D0"

        self.configure(bg=self.COL_BG)

        # ---- data ----
        self.data = self.load_data()

        # running timers: sid -> {"start_ts": float}
        self.running = {}

        # customer per station
        self.customer_by_station = self.data.get("customer_by_station", {})

        self._build_style()
        self._build_ui()
        self.refresh_tree()
        self._tick()

    # ---------- ttk style ----------
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except:
            pass

        style.configure(".", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"),
                        background=self.COL_BG, foreground=self.COL_TEXT)
        style.configure("SubTitle.TLabel", font=("Segoe UI", 10, "bold"),
                        background=self.COL_BG, foreground=self.COL_MUTED)

        style.configure("Card.TFrame", background=self.COL_CARD)
        style.configure("Card.TLabel", background=self.COL_CARD, foreground=self.COL_TEXT)
        style.configure("CardMuted.TLabel", background=self.COL_CARD, foreground=self.COL_MUTED, font=("Segoe UI", 10))
        style.configure("Value.TLabel", background=self.COL_CARD, foreground=self.COL_TEXT, font=("Segoe UI", 14, "bold"))

        # ✅ Buttons smaller
        style.configure("TButton", padding=(6, 4))
        style.configure("Small.TButton", padding=(6, 4))

        # Treeview
        style.configure("Treeview",
                        background="#0F172A",
                        fieldbackground="#0F172A",
                        foreground=self.COL_TEXT,
                        rowheight=30,
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background="#111C33",
                        foreground=self.COL_TEXT,
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview",
                  background=[("selected", "#1F3B78")],
                  foreground=[("selected", "white")])

    # ---------- persistence ----------
    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # ensure new keys exist
                data.setdefault("customer_by_station", {})
                # ✅ price profiles: type -> players -> rate
                data.setdefault("price_profiles", {
                    "PS5": {"1": 90000, "2": 120000, "3": 150000, "4": 180000},
                    "PS4": {"1": 70000, "2": 90000, "3": 110000, "4": 130000},
                })
                return data
            except:
                pass

        return {
            "rates": {"PS5": 90000, "PS4": 70000},  # kept for backward-compat
            "price_profiles": {
                "PS5": {"1": 90000, "2": 120000, "3": 150000, "4": 180000},
                "PS4": {"1": 70000, "2": 90000, "3": 110000, "4": 130000},
            },
            "stations": [
                {"id": "S1", "name": "دستگاه 1", "type": "PS5", "elapsed_base": 0, "active_players": 1, "active_rate": 0},
                {"id": "S2", "name": "دستگاه 2", "type": "PS4", "elapsed_base": 0, "active_players": 1, "active_rate": 0},
            ],
            "sessions": [],
            "customer_by_station": {}
        }

    def save_data(self):
        self.data["customer_by_station"] = self.customer_by_station
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("خطا", f"ذخیره اطلاعات انجام نشد:\n{e}")

    # ---------- UI ----------
    def _build_ui(self):
        # header
        header = tk.Frame(self, bg=self.COL_BG)
        header.pack(fill="x", padx=16, pady=(14, 10))

        tk.Label(header, text="🎮 پنل مدیریت گیم‌نت", bg=self.COL_BG, fg=self.COL_TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(header, text="Level 3 • انتخاب نفرات/نرخ قبل از شروع",
                 bg=self.COL_BG, fg=self.COL_MUTED, font=("Segoe UI", 10)).pack(side="left", padx=14)

        root = tk.Frame(self, bg=self.COL_BG)
        root.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        left = tk.Frame(root, bg=self.COL_BG)
        right = tk.Frame(root, bg=self.COL_BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 14))
        right.pack(side="right", fill="y")

        # left card
        stations_card = ttk.Frame(left, style="Card.TFrame", padding=12)
        stations_card.pack(fill="both", expand=True)

        ttk.Label(stations_card, text="دستگاه‌ها (دابل کلیک = انتخاب نفرات و شروع)", style="Card.TLabel",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")

        cols = ("name", "type", "players", "rate", "elapsed", "price", "status")
        self.tree = ttk.Treeview(stations_card, columns=cols, show="headings", height=14)
        for c, t in [
            ("name","نام دستگاه"),
            ("type","نوع"),
            ("players","نفرات"),
            ("rate","نرخ ساعتی"),
            ("elapsed","زمان"),
            ("price","مبلغ"),
            ("status","وضعیت")
        ]:
            self.tree.heading(c, text=t)

        self.tree.column("name", width=240, anchor="w")
        self.tree.column("type", width=70, anchor="center")
        self.tree.column("players", width=70, anchor="center")
        self.tree.column("rate", width=110, anchor="center")
        self.tree.column("elapsed", width=110, anchor="center")
        self.tree.column("price", width=120, anchor="center")
        self.tree.column("status", width=100, anchor="center")

        self.tree.pack(fill="both", expand=True, pady=(10, 10))
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.on_select_station())
        # ✅ double click to start flow
        self.tree.bind("<Double-1>", lambda e: self.start_flow_selected())

        self.tree.tag_configure("running", background="#102A1B")
        self.tree.tag_configure("stopped", background="#0F172A")

        btn_row = tk.Frame(stations_card, bg=self.COL_CARD)
        btn_row.pack(fill="x")

        ttk.Button(btn_row, text="➕ افزودن دستگاه", style="Small.TButton", command=self.open_add_station).pack(side="left")
        ttk.Button(btn_row, text="🗑 حذف دستگاه", style="Small.TButton", command=self.delete_station).pack(side="left", padx=8)
        ttk.Button(btn_row, text="⚙ تنظیم قیمت‌ها (۱ تا ۴ نفره)", style="Small.TButton", command=self.open_profiles).pack(side="left")

        # right: control card
        control_card = ttk.Frame(right, style="Card.TFrame", padding=12)
        control_card.pack(fill="x")

        ttk.Label(control_card, text="کنترل دستگاه", style="Card.TLabel",
                  font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.sel_name = tk.StringVar(value="—")
        self.sel_type = tk.StringVar(value="—")
        self.sel_players = tk.StringVar(value="—")
        self.sel_rate = tk.StringVar(value="—")
        self.sel_elapsed = tk.StringVar(value="00:00:00")
        self.sel_price = tk.StringVar(value="0 تومان")

        def row(lbl, var, r, big=False):
            ttk.Label(control_card, text=lbl, style="CardMuted.TLabel").grid(row=r, column=0, sticky="w", pady=(6,0))
            style = "Value.TLabel" if big else "Card.TLabel"
            ttk.Label(control_card, textvariable=var, style=style).grid(row=r, column=1, sticky="w", pady=(6,0))

        row("دستگاه:", self.sel_name, 1)
        row("نوع:", self.sel_type, 2)
        row("نفرات:", self.sel_players, 3)
        row("نرخ:", self.sel_rate, 4)
        row("زمان:", self.sel_elapsed, 5, big=True)
        row("مبلغ:", self.sel_price, 6, big=True)

        ttk.Label(control_card, text="نام مشتری (برای همین دستگاه):", style="CardMuted.TLabel")\
            .grid(row=7, column=0, sticky="w", pady=(12,0))

        self.customer_var = tk.StringVar(value="")
        entry = ttk.Entry(control_card, textvariable=self.customer_var, width=22)
        entry.grid(row=7, column=1, sticky="w", pady=(12,0))
        self.customer_var.trace_add("write", lambda *args: self._update_customer_for_selected())

        # ✅ smaller buttons (no fill-x giant)
        btns = tk.Frame(control_card, bg=self.COL_CARD)
        btns.grid(row=8, column=0, columnspan=2, sticky="w", pady=(14, 0))

        self.btn_start = ttk.Button(btns, text="▶ شروع", width=14, style="Small.TButton", command=self.start_flow_selected)
        self.btn_stop = ttk.Button(btns, text="⏸ توقف", width=14, style="Small.TButton", command=self.stop_selected)
        self.btn_checkout = ttk.Button(btns, text="✅ تسویه", width=14, style="Small.TButton", command=self.checkout_selected)

        self.btn_start.grid(row=0, column=0, padx=(0, 8))
        self.btn_stop.grid(row=0, column=1, padx=(0, 8))
        self.btn_checkout.grid(row=0, column=2)

        # report card
        report_card = ttk.Frame(right, style="Card.TFrame", padding=12)
        report_card.pack(fill="x", pady=(14, 0))

        ttk.Label(report_card, text="گزارش امروز", style="Card.TLabel",
                  font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.today_count_var = tk.StringVar(value="0")
        self.today_sum_var = tk.StringVar(value="0 تومان")

        ttk.Label(report_card, text="تعداد تسویه:", style="CardMuted.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(report_card, textvariable=self.today_count_var, style="Card.TLabel").grid(row=1, column=1, sticky="w")

        ttk.Label(report_card, text="جمع درآمد:", style="CardMuted.TLabel").grid(row=2, column=0, sticky="w", pady=(6,0))
        ttk.Label(report_card, textvariable=self.today_sum_var, style="Card.TLabel").grid(row=2, column=1, sticky="w", pady=(6,0))

        ttk.Button(report_card, text="📤 خروجی CSV", width=18, style="Small.TButton", command=self.export_csv)\
            .grid(row=3, column=0, sticky="w", pady=(14, 6))
        ttk.Button(report_card, text="🧾 تسویه‌های امروز", width=18, style="Small.TButton", command=self.show_today_sessions)\
            .grid(row=3, column=1, sticky="w", pady=(14, 6))

        self.on_select_station()
        self.update_report()

    # ---------- customer per station ----------
    def _update_customer_for_selected(self):
        sid = self.selected_station_id()
        if not sid:
            return
        self.customer_by_station[sid] = self.customer_var.get()
        self.save_data()

    def _load_customer_into_entry(self, sid: str):
        self.customer_var.set(self.customer_by_station.get(sid, ""))

    # ---------- station helpers ----------
    def get_station(self, station_id):
        for st in self.data["stations"]:
            if st["id"] == station_id:
                return st
        return None

    def selected_station_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return sel[0]

    # ---------- rate / players ----------
    def get_active_rate(self, st):
        # if active_rate set and > 0 use it; else fallback profile(1p) or rates
        ar = int(st.get("active_rate", 0) or 0)
        if ar > 0:
            return ar
        typ = st["type"]
        prof = self.data.get("price_profiles", {}).get(typ, {})
        r1 = prof.get("1")
        if r1 is not None:
            return int(r1)
        return int(self.data.get("rates", {}).get(typ, 0))

    def get_players(self, st):
        try:
            return int(st.get("active_players", 1) or 1)
        except:
            return 1

    # ---------- time & price ----------
    def get_elapsed_seconds(self, sid):
        st = self.get_station(sid)
        base = int(st.get("elapsed_base", 0))
        if sid in self.running:
            start_ts = self.running[sid]["start_ts"]
            extra = int(time.time() - start_ts)
            return base + max(0, extra)
        return base

    def calc_price(self, rate_per_hour, elapsed_seconds):
        hours = elapsed_seconds / 3600.0
        return int(round(hours * rate_per_hour))

    # ---------- tree refresh ----------
    def refresh_tree(self):
        sel = self.selected_station_id()
        for item in self.tree.get_children():
            self.tree.delete(item)

        for st in self.data["stations"]:
            sid = st["id"]
            name = st["name"]
            typ = st["type"]
            players = self.get_players(st)

            rate = self.get_active_rate(st)
            elapsed = self.get_elapsed_seconds(sid)
            price = self.calc_price(rate, elapsed)
            status = "درحال بازی" if sid in self.running else "متوقف"
            tag = "running" if sid in self.running else "stopped"

            self.tree.insert(
                "", "end", iid=sid,
                values=(name, typ, f"{players} نفره", format_toman(rate), seconds_to_hms(elapsed), format_toman(price), status),
                tags=(tag,)
            )

        if sel and sel in self.tree.get_children():
            self.tree.selection_set(sel)
            self.tree.focus(sel)

        self.on_select_station()

    def on_select_station(self):
        sid = self.selected_station_id()
        if not sid:
            self.sel_name.set("—")
            self.sel_type.set("—")
            self.sel_players.set("—")
            self.sel_rate.set("—")
            self.sel_elapsed.set("00:00:00")
            self.sel_price.set("0 تومان")
            self.customer_var.set("")
            self.btn_start.state(["disabled"])
            self.btn_stop.state(["disabled"])
            self.btn_checkout.state(["disabled"])
            return

        st = self.get_station(sid)
        typ = st["type"]
        players = self.get_players(st)
        rate = self.get_active_rate(st)
        elapsed = self.get_elapsed_seconds(sid)
        price = self.calc_price(rate, elapsed)

        self.sel_name.set(st["name"])
        self.sel_type.set(typ)
        self.sel_players.set(f"{players} نفره")
        self.sel_rate.set(f"{format_toman(rate)} تومان / ساعت")
        self.sel_elapsed.set(seconds_to_hms(elapsed))
        self.sel_price.set(f"{format_toman(price)} تومان")

        self._load_customer_into_entry(sid)

        self.btn_checkout.state(["!disabled"])
        if sid in self.running:
            self.btn_start.state(["disabled"])
            self.btn_stop.state(["!disabled"])
        else:
            self.btn_start.state(["!disabled"])
            self.btn_stop.state(["disabled"])

    # ---------- start flow (choose players/rate then start) ----------
    def start_flow_selected(self):
        sid = self.selected_station_id()
        if not sid:
            return
        st = self.get_station(sid)

        if sid in self.running:
            return  # already running

        # اگر تایمر قبلاً زمان داشته و stop شده: با همون نرخ ادامه بده (بدون پرسیدن)
        # ولی اگر می‌خوای همیشه قبل شروع بپرسه، این if رو بردار.
        if int(st.get("elapsed_base", 0)) > 0 and self.get_active_rate(st) > 0:
            self.running[sid] = {"start_ts": time.time()}
            self.refresh_tree()
            return

        self.open_players_dialog(st)

    def open_players_dialog(self, st):
        typ = st["type"]
        prof = self.data.get("price_profiles", {}).get(typ, {})
        # default selection
        current_players = str(self.get_players(st))
        if current_players not in ("1", "2", "3", "4"):
            current_players = "1"

        win = tk.Toplevel(self)
        win.title(f"انتخاب نفرات و قیمت - {st['name']}")
        win.geometry("420x320")
        win.configure(bg=self.COL_BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        card = ttk.Frame(win, style="Card.TFrame", padding=14)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        ttk.Label(card, text=f"{st['name']}  |  {typ}", style="Card.TLabel",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")

        ttk.Label(card, text="یکی از حالت‌ها رو انتخاب کن. بعدش شروع میشه 👇",
                  style="CardMuted.TLabel").pack(anchor="w", pady=(6, 10))

        choice = tk.StringVar(value=current_players)
        custom_on = tk.BooleanVar(value=False)
        custom_rate_var = tk.StringVar(value="")

        def radio_text(p):
            r = prof.get(str(p))
            if r is None:
                r = 0
            return f"{p} نفره  —  {format_toman(int(r))} تومان/ساعت"

        radios = ttk.Frame(card, style="Card.TFrame")
        radios.pack(fill="x")

        for p in [1, 2, 3, 4]:
            ttk.Radiobutton(radios, text=radio_text(p), value=str(p), variable=choice)\
                .pack(anchor="w", pady=2)

        sep = ttk.Separator(card)
        sep.pack(fill="x", pady=10)

        row = ttk.Frame(card, style="Card.TFrame")
        row.pack(fill="x")

        ttk.Checkbutton(row, text="نرخ دستی", variable=custom_on).pack(side="left")
        ttk.Entry(row, textvariable=custom_rate_var, width=16).pack(side="left", padx=8)
        ttk.Label(row, text="تومان/ساعت", style="CardMuted.TLabel").pack(side="left")

        def start():
            # decide rate
            if custom_on.get():
                r = safe_int(custom_rate_var.get(), 0)
                if r <= 0:
                    messagebox.showerror("خطا", "نرخ دستی معتبر نیست.")
                    return
                rate = r
                players = safe_int(choice.get(), 1)
            else:
                players = safe_int(choice.get(), 1)
                rate = safe_int(prof.get(str(players), 0), 0)
                if rate <= 0:
                    messagebox.showerror("خطا", "برای این حالت قیمت تعریف نشده. از تنظیمات قیمت‌ها درستش کن یا نرخ دستی بزن.")
                    return

            # save to station
            st["active_players"] = int(players)
            st["active_rate"] = int(rate)
            self.save_data()

            # start timer
            sid = st["id"]
            self.running[sid] = {"start_ts": time.time()}
            win.destroy()
            self.refresh_tree()

        btns = ttk.Frame(card, style="Card.TFrame")
        btns.pack(fill="x", pady=(14, 0))

        ttk.Button(btns, text="شروع", width=12, style="Small.TButton", command=start).pack(side="left")
        ttk.Button(btns, text="انصراف", width=12, style="Small.TButton", command=win.destroy).pack(side="left", padx=8)

    # ---------- controls ----------
    def stop_selected(self):
        sid = self.selected_station_id()
        if not sid or sid not in self.running:
            return
        st = self.get_station(sid)
        elapsed_now = self.get_elapsed_seconds(sid)
        st["elapsed_base"] = int(elapsed_now)
        self.running.pop(sid, None)
        self.save_data()
        self.refresh_tree()

    def checkout_selected(self):
        sid = self.selected_station_id()
        if not sid:
            return
        st = self.get_station(sid)

        elapsed = self.get_elapsed_seconds(sid)
        if elapsed <= 0:
            if not messagebox.askyesno("تسویه", "زمان صفر است. تسویه انجام شود؟"):
                return

        if sid in self.running:
            self.running.pop(sid, None)

        rate = self.get_active_rate(st)
        price = self.calc_price(rate, elapsed)
        players = self.get_players(st)
        customer = (self.customer_by_station.get(sid, "") or "").strip()

        sess = {
            "day": today_str(),
            "station_id": sid,
            "station_name": st["name"],
            "type": st["type"],
            "players": players,
            "rate": rate,
            "end": now_str(),
            "seconds": int(elapsed),
            "price": int(price),
            "customer": customer
        }
        self.data["sessions"].append(sess)

        # reset station
        st["elapsed_base"] = 0
        st["active_rate"] = 0
        st["active_players"] = 1
        self.customer_by_station[sid] = ""
        self.customer_var.set("")

        self.save_data()
        self.update_report()
        self.refresh_tree()

        messagebox.showinfo(
            "تسویه انجام شد",
            f"دستگاه: {st['name']}\n"
            f"نفرات: {players} نفره\n"
            f"زمان: {seconds_to_hms(int(elapsed))}\n"
            f"نرخ: {format_toman(rate)} تومان/ساعت\n"
            f"مبلغ: {format_toman(price)} تومان\n"
            f"مشتری: {customer or '—'}"
        )

    # ---------- add/delete ----------
    def open_add_station(self):
        win = tk.Toplevel(self)
        win.title("افزودن دستگاه")
        win.geometry("390x240")
        win.configure(bg=self.COL_BG)
        win.resizable(False, False)

        frm = ttk.Frame(win, style="Card.TFrame", padding=12)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        name_var = tk.StringVar(value=f"دستگاه {len(self.data['stations']) + 1}")
        type_var = tk.StringVar(value="PS5")

        ttk.Label(frm, text="نام/شماره دستگاه:", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=name_var, width=26).grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="نوع:", style="CardMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(10,0))
        ttk.Combobox(frm, textvariable=type_var, values=["PS5","PS4"], state="readonly", width=10)\
            .grid(row=1, column=1, sticky="w", pady=(10,0))

        def add():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("خطا", "نام دستگاه را وارد کنید.")
                return
            base = f"S{len(self.data['stations'])+1}"
            sid = base
            i = 2
            existing = {s["id"] for s in self.data["stations"]}
            while sid in existing:
                sid = f"{base}_{i}"
                i += 1
            self.data["stations"].append({
                "id": sid, "name": name, "type": type_var.get(),
                "elapsed_base": 0, "active_players": 1, "active_rate": 0
            })
            self.customer_by_station.setdefault(sid, "")
            self.save_data()
            self.refresh_tree()
            win.destroy()

        ttk.Button(frm, text="✅ اضافه کن", command=add).grid(row=3, column=0, columnspan=2, sticky="ew", pady=18)
        frm.columnconfigure(1, weight=1)

    def delete_station(self):
        sid = self.selected_station_id()
        if not sid:
            return
        st = self.get_station(sid)

        if sid in self.running:
            messagebox.showerror("خطا", "این دستگاه در حال بازی است. اول توقف یا تسویه کنید.")
            return

        if not messagebox.askyesno("حذف دستگاه", f"واقعاً «{st['name']}» حذف شود؟"):
            return

        self.data["stations"] = [s for s in self.data["stations"] if s["id"] != sid]
        self.customer_by_station.pop(sid, None)
        self.save_data()
        self.refresh_tree()

    # ---------- profiles (1-4 players prices) ----------
    def open_profiles(self):
        win = tk.Toplevel(self)
        win.title("تنظیم قیمت‌ها (۱ تا ۴ نفره)")
        win.geometry("520x340")
        win.configure(bg=self.COL_BG)
        win.resizable(False, False)

        frm = ttk.Frame(win, style="Card.TFrame", padding=12)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        ttk.Label(frm, text="قیمت‌ها رو برای هر دستگاه و هر تعداد نفر تنظیم کن",
                  style="Card.TLabel", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 10))

        entries = {}  # (type, players) -> var

        def make_row(r, typ):
            ttk.Label(frm, text=typ, style="CardMuted.TLabel").grid(row=r, column=0, sticky="w")
            for i, p in enumerate([1,2,3,4], start=1):
                v = tk.StringVar(value=str(self.data["price_profiles"].get(typ, {}).get(str(p), 0)))
                entries[(typ, p)] = v
                ttk.Entry(frm, textvariable=v, width=10).grid(row=r, column=i, padx=6)

        ttk.Label(frm, text="۱ نفره", style="CardMuted.TLabel").grid(row=1, column=1)
        ttk.Label(frm, text="۲ نفره", style="CardMuted.TLabel").grid(row=1, column=2)
        ttk.Label(frm, text="۳ نفره", style="CardMuted.TLabel").grid(row=1, column=3)
        ttk.Label(frm, text="۴ نفره", style="CardMuted.TLabel").grid(row=1, column=4)

        make_row(2, "PS5")
        make_row(3, "PS4")

        def save():
            for typ in ("PS5", "PS4"):
                self.data["price_profiles"].setdefault(typ, {})
                for p in (1,2,3,4):
                    self.data["price_profiles"][typ][str(p)] = max(0, safe_int(entries[(typ,p)].get(), 0))
            self.save_data()
            self.refresh_tree()
            win.destroy()

        ttk.Button(frm, text="💾 ذخیره", style="Small.TButton", command=save)\
            .grid(row=5, column=0, columnspan=5, sticky="w", pady=(18, 0))

    # ---------- reports ----------
    def update_report(self):
        day = today_str()
        today_sessions = [s for s in self.data["sessions"] if s.get("day") == day]
        total = sum(int(s.get("price", 0)) for s in today_sessions)
        self.today_count_var.set(str(len(today_sessions)))
        self.today_sum_var.set(f"{format_toman(total)} تومان")

    def show_today_sessions(self):
        day = today_str()
        rows = [s for s in self.data["sessions"] if s.get("day") == day]
        if not rows:
            messagebox.showinfo("امروز", "برای امروز هنوز تسویه‌ای ثبت نشده.")
            return

        win = tk.Toplevel(self)
        win.title("تسویه‌های امروز")
        win.geometry("980x380")
        win.configure(bg=self.COL_BG)

        frm = ttk.Frame(win, style="Card.TFrame", padding=12)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        cols = ("end", "station", "type", "players", "time", "rate", "price", "customer")
        tv = ttk.Treeview(frm, columns=cols, show="headings", height=12)
        for c, t in [
            ("end","زمان ثبت"), ("station","دستگاه"), ("type","نوع"), ("players","نفرات"),
            ("time","مدت"), ("rate","نرخ"), ("price","مبلغ"), ("customer","مشتری")
        ]:
            tv.heading(c, text=t)

        tv.column("end", width=150, anchor="center")
        tv.column("station", width=170, anchor="w")
        tv.column("type", width=60, anchor="center")
        tv.column("players", width=70, anchor="center")
        tv.column("time", width=90, anchor="center")
        tv.column("rate", width=90, anchor="center")
        tv.column("price", width=100, anchor="center")
        tv.column("customer", width=200, anchor="w")
        tv.pack(fill="both", expand=True)

        for s in rows[::-1]:
            tv.insert(
                "", "end",
                values=(
                    s.get("end",""),
                    s.get("station_name",""),
                    s.get("type",""),
                    f"{s.get('players',1)} نفره",
                    seconds_to_hms(int(s.get("seconds",0))),
                    format_toman(int(s.get("rate",0))),
                    format_toman(int(s.get("price",0))),
                    s.get("customer","")
                )
            )

    def export_csv(self):
        if not self.data["sessions"]:
            messagebox.showinfo("خروجی", "هنوز هیچ تسویه‌ای ثبت نشده.")
            return

        default_name = f"gamenet_sessions_{today_str()}.csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV Files", "*.csv")]
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["day","end","station_id","station_name","type","players","rate","seconds","price","customer"])
                for s in self.data["sessions"]:
                    w.writerow([
                        s.get("day",""),
                        s.get("end",""),
                        s.get("station_id",""),
                        s.get("station_name",""),
                        s.get("type",""),
                        s.get("players",""),
                        s.get("rate",""),
                        s.get("seconds",""),
                        s.get("price",""),
                        s.get("customer",""),
                    ])
            messagebox.showinfo("خروجی", "فایل CSV با موفقیت ذخیره شد.")
        except Exception as e:
            messagebox.showerror("خطا", f"ذخیره CSV انجام نشد:\n{e}")

    # ---------- tick ----------
    def _tick(self):
        self.refresh_tree()
        self.update_report()
        self.after(500, self._tick)

if __name__ == "__main__":
    app = GameNetApp()
    app.mainloop()