# -*- coding: utf-8 -*-
"""
LeanFocus - タスクトレイ常駐型ポモドーロタイマー
メインウィンドウを持たず、フローティングオーバーレイとタスクトレイで操作する軽量タイマー。
"""

import threading
import time
import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk
import ctypes
import locale

# サードパーティ製ライブラリ
from PIL import Image
import pystray
import pygame

# --- Windowsの高DPIスケーリング対応 ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except (AttributeError, OSError):
    try:
        ctypes.windll.user32.SetProcessDpiAware()
    except (AttributeError, OSError):
        pass

# =========================================
# グローバル設定・定数
# =========================================
CONFIG_FILE = 'LeanFocus_config.json'
WORK_DURATION = 25 * 60  # 作業時間（秒）
BREAK_DURATION = 5 * 60  # 休憩時間（秒）
APP_NAME = "LeanFocus"

# アセットパス設定
ASSET_DIR = "assets"
IMG_DIR = os.path.join(ASSET_DIR, "img")
SOUND_DIR = os.path.join(ASSET_DIR, "sounds")
ICON_FILE = os.path.join(IMG_DIR, "icon.png")
SOUND_NAMES_FILE = os.path.join(SOUND_DIR, "sound_names.json")
CREDITS_FILE = os.path.join(ASSET_DIR, "CREDITS.txt")

# 対応する音声ファイル形式
SUPPORTED_EXTENSIONS = ('.mp3', '.wav', '.ogg')

# =========================================
# 言語・翻訳設定
# =========================================
TRANSLATIONS = {
    "ja": {
        "settings_title": "設定",
        "sound_sec": "サウンド設定",
        "volume": "音量調整",
        "visual_sec": "表示設定 (タイマー)",
        "size": "サイズ調整",
        "opacity": "不透明度",
        "window_hint": "※ウィンドウ位置はドラッグで移動・保存されます",
        "close": "閉じる",
        "work_noise": "作業用ノイズ",
        "break_noise": "休憩用ノイズ",
        "none": "なし",
        "stop_timer": "タイマーを停止",
        "show_timer": "タイマーを表示",
        "settings_menu": "設定...",
        "credits": "クレジット",
        "quit": "アプリを終了",
        "state_stopped": "STOP",
        "state_work": "WORK",   # 英語表記のままの方がスタイリッシュなため変更
        "state_break": "BREAK", # 同上
        "state_paused": "PAUSE",
        "status_fmt": "{state}   {time}", # ステータス表示フォーマット
        "start": "タイマーを開始",
        "resume": "タイマーを再開",
        "pause": "タイマーを一時停止",
        # コンテキストメニュー用
        "ctx_start": "開始",
        "ctx_pause": "一時停止",
        "ctx_resume": "再開",
        "ctx_restart": "リスタート",
        "ctx_stop": "停止",
        "ctx_hide": "タイマーを隠す",
    },
    "en": {
        "settings_title": "Settings",
        "sound_sec": "Sound Settings",
        "volume": "Volume",
        "visual_sec": "Timer Appearance",
        "size": "Size",
        "opacity": "Opacity",
        "window_hint": "* Window position is saved on drag & drop.",
        "close": "Close",
        "work_noise": "Work Noise",
        "break_noise": "Break Noise",
        "none": "None",
        "stop_timer": "Stop Timer",
        "show_timer": "Show Timer",
        "settings_menu": "Settings...",
        "credits": "Credits",
        "quit": "Quit",
        "state_stopped": "STOP",
        "state_work": "WORK",
        "state_break": "BREAK",
        "state_paused": "PAUSE",
        "status_fmt": "{state}   {time}",
        "start": "Start Timer",
        "resume": "Resume Timer",
        "pause": "Pause Timer",
        # Context Menu
        "ctx_start": "Start",
        "ctx_pause": "Pause",
        "ctx_resume": "Resume",
        "ctx_restart": "Restart",
        "ctx_stop": "Stop",
        "ctx_hide": "Hide Timer",
    }
}

def get_language():
    """システムロケールを取得して言語コード('ja' or 'en')を返す"""
    try:
        windll = ctypes.windll.kernel32
        if (windll.GetUserDefaultUILanguage() & 0xFF) == 0x11:
            return 'ja'
    except:
        pass
    return 'en'

CURRENT_LANG = get_language()

def tr(key):
    """キーに対応する翻訳テキストを返す"""
    return TRANSLATIONS[CURRENT_LANG].get(key, key)


# =========================================
# クラス定義: 設定ウィンドウ
# =========================================
class ConfigWindow(tk.Toplevel):
    """
    設定画面クラス。
    """
    def __init__(self, parent, timer_window):
        super().__init__(parent)
        self.timer_window = timer_window
        self.app = timer_window.timer_app
        
        self.title(tr("settings_title"))
        
        window_width = 370
        window_height = 560
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

        self.resizable(True, True)
        self.attributes("-topmost", True)

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        main_frame = ttk.Frame(canvas, padding="20")

        main_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_frame_id = canvas.create_window((0, 0), window=main_frame, anchor="nw")

        def on_canvas_configure(event):
            canvas.itemconfig(canvas_frame_id, width=event.width)
        
        canvas.bind("<Configure>", on_canvas_configure)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            if canvas.bbox("all")[3] > canvas.winfo_height():
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.bind("<MouseWheel>", _on_mousewheel)

        # --- UI部品 ---
        ttk.Label(main_frame, text=tr("sound_sec"), font=("", 10, "bold")).pack(anchor='w', pady=(0, 10))
        
        self.sound_keys = sorted(list(self.app.available_noises.keys()))
        if "None" in self.sound_keys:
            self.sound_keys.remove("None")
            self.sound_keys.insert(0, "None")
        
        display_values = [tr("none") if k == "None" else k for k in self.sound_keys]

        ttk.Label(main_frame, text=tr("work_noise")).pack(anchor='w')
        current_work = self.app.config.get("work_noise", "None")
        work_idx = self.sound_keys.index(current_work) if current_work in self.sound_keys else 0
        
        self.combo_work = ttk.Combobox(main_frame, values=display_values, state="readonly")
        self.combo_work.current(work_idx)
        self.combo_work.pack(fill='x', pady=(0, 10))
        self.combo_work.bind("<<ComboboxSelected>>", lambda e: self.on_sound_change("work"))

        ttk.Label(main_frame, text=tr("break_noise")).pack(anchor='w')
        current_break = self.app.config.get("break_noise", "None")
        break_idx = self.sound_keys.index(current_break) if current_break in self.sound_keys else 0

        self.combo_break = ttk.Combobox(main_frame, values=display_values, state="readonly")
        self.combo_break.current(break_idx)
        self.combo_break.pack(fill='x', pady=(0, 10))
        self.combo_break.bind("<<ComboboxSelected>>", lambda e: self.on_sound_change("break"))

        ttk.Label(main_frame, text=tr("volume")).pack(anchor='w')
        self.volume_var = tk.DoubleVar(value=self.app.config.get("volume", 1.0))
        scale_vol = ttk.Scale(main_frame, from_=0.0, to=1.0, variable=self.volume_var, command=self.on_volume_change)
        scale_vol.pack(fill='x', pady=(0, 5))

        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=15)

        ttk.Label(main_frame, text=tr("visual_sec"), font=("", 10, "bold")).pack(anchor='w', pady=(0, 10))

        ttk.Label(main_frame, text=tr("size")).pack(anchor='w')
        self.size_var = tk.DoubleVar(value=timer_window.font_size)
        scale_size = ttk.Scale(main_frame, from_=6, to=72, variable=self.size_var, command=self.on_visual_change)
        scale_size.pack(fill='x', pady=(0, 10))

        ttk.Label(main_frame, text=tr("opacity")).pack(anchor='w')
        self.alpha_var = tk.DoubleVar(value=timer_window.opacity)
        scale_alpha = ttk.Scale(main_frame, from_=0.1, to=1.0, variable=self.alpha_var, command=self.on_visual_change)
        scale_alpha.pack(fill='x', pady=(0, 5))

        ttk.Label(main_frame, text=tr("window_hint"), font=("", 8), foreground="gray").pack(pady=(5, 0))

        ttk.Button(main_frame, text=tr("close"), command=self.destroy).pack(side='bottom', anchor='e', pady=10)

    def on_sound_change(self, noise_type):
        if noise_type == "work":
            idx = self.combo_work.current()
            key = self.sound_keys[idx]
        else:
            idx = self.combo_break.current()
            key = self.sound_keys[idx]
        self.app.set_noise_config(noise_type, key)

    def on_visual_change(self, event=None):
        self.timer_window.apply_visual_settings(self.size_var.get(), self.alpha_var.get())

    def on_volume_change(self, event=None):
        self.app.set_volume(self.volume_var.get())


# =========================================
# クラス定義: フローティングタイマー（オーバーレイ）
# =========================================
class FloatingTimer(tk.Tk):
    """
    常に最前面に表示される透過ウィンドウ。
    """
    def __init__(self, timer_app):
        super().__init__()
        self.timer_app = timer_app
        
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.config(bg="black")

        self.font_size = self.timer_app.config.get("font_size", 24)
        self.opacity = self.timer_app.config.get("opacity", 0.7)
        self.attributes("-alpha", self.opacity)

        # レイアウトモード管理
        self.is_pause_layout = False

        # --- 通常時用のコンテナ (1行表示) ---
        self.frame_normal = tk.Frame(self, bg="black")
        self.label_normal = tk.Label(
            self.frame_normal, 
            text="--:--", 
            font=("Segoe UI", self.font_size, "bold"),
            fg="#E0E0E0", 
            bg="black"
        )
        self.label_normal.pack(expand=True, fill='both', padx=5, pady=5)

        # --- PAUSE時用のコンテナ (2カラム表示) ---
        self.frame_pause = tk.Frame(self, bg="black")
        
        # 左カラム
        self.frame_pause_left = tk.Frame(self.frame_pause, bg="black")
        self.frame_pause_left.pack(side="left", padx=(5, 2))
        
        # "WORK/BREAK" (左上)
        self.label_pause_resume = tk.Label(
            self.frame_pause_left,
            text="WORK",
            font=("Segoe UI", int(self.font_size * 0.55), "bold"), # 初期値も0.5に
            fg="#9E9E9E",
            bg="black",
            anchor="w"
        )
        # 余白を詰めるため pady=0 を明示（デフォルトですが念のため）
        self.label_pause_resume.pack(side="top", anchor="w", pady=0)

        # "PAUSE" (左下)
        self.label_pause_status = tk.Label(
            self.frame_pause_left,
            text="PAUSE",
            font=("Segoe UI", int(self.font_size * 0.55), "bold"), # 初期値も0.5に
            fg="#FFF59D",
            bg="black",
            anchor="w"
        )
        self.label_pause_status.pack(side="top", anchor="w", pady=0)

        # 右カラム: 時間
        self.label_pause_time = tk.Label(
            self.frame_pause,
            text="25:00",
            font=("Segoe UI", self.font_size, "bold"),
            fg="#E0E0E0",
            bg="black"
        )
        self.label_pause_time.pack(side="right", fill="both", padx=(2, 5))

        # 初期状態は通常フレームを表示
        self.frame_normal.pack(expand=True, fill='both')
        
        self.update_idletasks()
        self.refresh_layout()

        # ドラッグ・クリック判定用の変数
        self.drag_start_x_root = 0
        self.drag_start_y_root = 0
        self.click_start_time = 0

        self.menu_window = None
        self.is_menu_open = False

        # 【重要】全てのウィジェットをリストアップして明示的にバインドする
        # これにより、どのパーツをクリックしても反応するようにする
        self.all_widgets = [
            self,
            self.frame_normal, self.label_normal,
            self.frame_pause, self.frame_pause_left,
            self.label_pause_status, self.label_pause_resume, self.label_pause_time
        ]
        self._bind_events_to_all()
        
        self.x = 0
        self.y = 0
        self.is_visible = False

        self.update_timer_display()

    def _bind_events_to_all(self):
        """定義済みの全ウィジェットにイベントをバインド"""
        for widget in self.all_widgets:
            try:
                widget.bind("<Button-1>", self.start_move)
                widget.bind("<B1-Motion>", self.do_move)
                widget.bind("<ButtonRelease-1>", self.on_release)
                widget.bind("<Button-3>", self.show_custom_menu)
                widget.bind("<Enter>", self.on_hover_enter)
                widget.bind("<Leave>", self.on_hover_leave)
            except:
                pass

    def show_custom_menu(self, event):
        """カスタムコンテキストメニューを表示"""
        self.close_custom_menu()
        self.is_menu_open = True

        menu = tk.Toplevel(self)
        menu.overrideredirect(True)
        menu.attributes("-topmost", True)
        
        bg_color = "#2B2B2B"
        fg_color = "#F0F0F0"
        hover_bg = "#414141"
        
        menu.config(bg=bg_color, relief="solid", bd=1)
        self.menu_window = menu

        def add_menu_item(text, command):
            item = tk.Label(
                menu, text=text, 
                font=("Yu Gothic", 9),
                bg=bg_color, fg=fg_color,
                anchor="w", 
                padx=12, pady=4
            )
            item.pack(fill="x", padx=0, pady=0)
            
            def on_click(e):
                command()
                self.close_custom_menu()
            def on_enter(e):
                item.config(bg=hover_bg)
            def on_leave(e):
                item.config(bg=bg_color)

            item.bind("<Button-1>", on_click)
            item.bind("<Enter>", on_enter)
            item.bind("<Leave>", on_leave)

        def add_separator():
            sep_frame = tk.Frame(menu, bg=bg_color, height=6)
            sep_frame.pack(fill="x")
            sep = tk.Frame(sep_frame, height=1, bg="#555555")
            sep.place(relx=0.02, rely=0.5, relwidth=0.96, anchor="w")

        state = self.timer_app.state

        # 1. 一時停止 / 再開 / 開始
        if state in [PomodoroTimer.STATE_WORK, PomodoroTimer.STATE_BREAK]:
            add_menu_item(tr("ctx_pause"), self.toggle_timer_action)
        elif state == PomodoroTimer.STATE_PAUSED:
            add_menu_item(tr("ctx_resume"), self.toggle_timer_action)
        else:
            add_menu_item(tr("ctx_start"), self.toggle_timer_action)

        # 2. リスタート (作業中・休憩中のみ表示)
        if state in [PomodoroTimer.STATE_WORK, PomodoroTimer.STATE_BREAK]:
            add_menu_item(tr("ctx_restart"), self.timer_app.restart_and_pause)

        # 3. 停止 (停止中以外)
        if state != PomodoroTimer.STATE_STOPPED:
            add_menu_item(tr("ctx_stop"), self.timer_app.reset_timer)

        # 4. 隠す
        add_menu_item(tr("ctx_hide"), self.timer_app.toggle_timer_display)

        add_separator()

        # 5. 設定
        add_menu_item(tr("settings_menu"), self.timer_app.open_config_window)

        menu.update_idletasks()
        w = menu.winfo_reqwidth()
        h = menu.winfo_reqheight()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = event.x_root
        y = event.y_root
        if x + w > screen_w: x = screen_w - w
        if y + h > screen_h: y = screen_h - h
        menu.geometry(f"{w}x{h}+{x}+{y}")

        menu.focus_force()
        def check_focus_out(e):
            self.after(10, self._check_focus_and_close)
        menu.bind("<FocusOut>", check_focus_out)
        menu.bind("<Escape>", lambda e: self.close_custom_menu())

    def _check_focus_and_close(self):
        if self.menu_window:
            focused = self.menu_window.focus_get()
            if focused != self.menu_window and focused not in self.menu_window.winfo_children():
                self.close_custom_menu()

    def close_custom_menu(self):
        if self.menu_window:
            try: self.menu_window.destroy()
            except: pass
            self.menu_window = None
        self.is_menu_open = False
        self.lift()
        self.attributes("-topmost", True)

    def refresh_layout(self):
        base_font = ("Segoe UI", self.font_size, "bold")
        # 最小値を 8 ではなく 1 に変更し、計算上の比率を優先させる
        small_font = ("Segoe UI", max(1, int(self.font_size * 0.55)), "bold")
        
        self.label_normal.config(font=base_font)
        self.label_pause_time.config(font=base_font)
        self.label_pause_status.config(font=small_font)
        self.label_pause_resume.config(font=small_font)

        self.update_idletasks()
        
        win_w = self.winfo_reqwidth()
        win_h = self.winfo_reqheight()
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        saved_x = self.timer_app.config.get("window_x")
        saved_y = self.timer_app.config.get("window_y")

        if saved_x is not None and saved_y is not None:
            x, y = saved_x, saved_y
        else:
            x = screen_width - win_w - 30
            y = screen_height - win_h - 80 
        
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

    def start_move(self, event):
        if self.is_menu_open:
            self.close_custom_menu()
        self.x = event.x
        self.y = event.y
        self.drag_start_x_root = event.x_root
        self.drag_start_y_root = event.y_root
        self.click_start_time = time.time()

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def on_release(self, event):
        # start_moveが呼ばれていない場合（click_start_timeが0）は無視
        if self.click_start_time == 0:
            return

        press_duration = time.time() - self.click_start_time
        dx = event.x_root - self.drag_start_x_root
        dy = event.y_root - self.drag_start_y_root
        distance_sq = dx**2 + dy**2 

        is_short_click = press_duration < 0.3
        is_small_move = distance_sq < 25 

        if is_short_click and is_small_move:
            self.toggle_timer_action()
        
        # 処理後にリセット
        self.click_start_time = 0

        self.timer_app.config["window_x"] = self.winfo_x()
        self.timer_app.config["window_y"] = self.winfo_y()
        self.timer_app.save_config()

    def toggle_timer_action(self):
        state = self.timer_app.state
        if state in [PomodoroTimer.STATE_WORK, PomodoroTimer.STATE_BREAK]:
            self.timer_app.stop_pomodoro()
        else:
            self.timer_app.start_pomodoro()

    def on_hover_enter(self, event):
        current = self.attributes("-alpha")
        self.attributes("-alpha", min(1.0, current + 0.2))

    def on_hover_leave(self, event):
        self.attributes("-alpha", self.opacity)

    def apply_visual_settings(self, size, opacity):
        self.font_size = int(float(size))
        self.opacity = float(opacity)
        self.attributes("-alpha", self.opacity)
        
        self.refresh_layout()
        
        self.timer_app.config["font_size"] = self.font_size
        self.timer_app.config["opacity"] = self.opacity
        self.timer_app.save_config()

    def toggle_visibility(self, show):
        if show:
            self.deiconify()
            self.is_visible = True
            self.refresh_layout()
            self.lift()
            self.attributes("-topmost", True)
        else:
            self.withdraw()
            self.is_visible = False

    def update_timer_display(self):
        state = self.timer_app.state
        remaining = max(0, self.timer_app.remaining_time)
        mins, secs = divmod(remaining, 60)
        time_text = f"{mins:02d}:{secs:02d}"
        
        COLOR_WORK = "#9E9E9E"
        COLOR_BREAK = "#80CBC4"
        COLOR_PAUSE = "#FFF59D"
        COLOR_STOP = "#FF8A80"

        if state == PomodoroTimer.STATE_PAUSED:
            if not self.is_pause_layout:
                self.frame_normal.pack_forget()
                self.frame_pause.pack(expand=True, fill='both')
                self.is_pause_layout = True

            resume_st = self.timer_app.resume_state
            
            if resume_st == PomodoroTimer.STATE_WORK:
                resume_text = tr("state_work")
                resume_fg = COLOR_WORK
            else:
                resume_text = tr("state_break")
                resume_fg = COLOR_BREAK

            self.label_pause_resume.config(text=resume_text, fg=resume_fg)
            self.label_pause_status.config(text=tr("state_paused"), fg=COLOR_PAUSE)
            self.label_pause_time.config(text=time_text, fg=resume_fg) 

        else:
            if self.is_pause_layout:
                self.frame_pause.pack_forget()
                self.frame_normal.pack(expand=True, fill='both')
                self.is_pause_layout = False

            if state == PomodoroTimer.STATE_WORK:
                st_text = tr("state_work")
                fg = COLOR_WORK
            elif state == PomodoroTimer.STATE_BREAK:
                st_text = tr("state_break")
                fg = COLOR_BREAK
            else:
                st_text = tr("state_stopped")
                fg = COLOR_STOP
                time_text = "--:--"
            
            display_text = f"{st_text}   {time_text}"
            self.label_normal.config(text=display_text, fg=fg)
        
        self.update_idletasks()
        req_w = self.winfo_reqwidth()
        req_h = self.winfo_reqheight()
        if self.winfo_width() != req_w or self.winfo_height() != req_h:
             x = self.winfo_x()
             y = self.winfo_y()
             self.geometry(f"{req_w}x{req_h}+{x}+{y}")

        if self.is_visible and not self.is_menu_open:
            self.attributes("-topmost", True)

        self.after(200, self.update_timer_display)


# =========================================
# クラス定義: ポモドーロタイマー本体（ロジック）
# =========================================
class PomodoroTimer:
    STATE_STOPPED = "STOP"
    STATE_WORK = "WORK"
    STATE_BREAK = "BREAK"
    STATE_PAUSED = "PAUSE"

    def __init__(self):
        self.state = self.STATE_STOPPED
        self.resume_state = self.STATE_WORK
        self.remaining_time = WORK_DURATION
        
        self.stop_event = threading.Event()
        self.timer_thread = None
        self.end_time = 0 
        
        self.available_noises = self._scan_assets()
        self.config = self.load_config() 
        
        self.icon = None 
        self.floating_window: FloatingTimer = None
        
        self._init_pygame()

    def _init_pygame(self):
        try:
            pygame.mixer.init()
        except pygame.error: pass

    def _scan_assets(self) -> dict:
        noises = {"None": None}
        if not os.path.isdir(SOUND_DIR): return noises
        
        name_map = {}
        if os.path.exists(SOUND_NAMES_FILE):
            try:
                with open(SOUND_NAMES_FILE, 'r', encoding='utf-8') as f:
                    name_map = json.load(f)
            except Exception: pass

        try:
            for filename in os.listdir(SOUND_DIR):
                file_path = os.path.join(SOUND_DIR, filename)
                if os.path.isfile(file_path) and filename.lower().endswith(SUPPORTED_EXTENSIONS):
                    if filename in name_map:
                        entry = name_map[filename]
                        if isinstance(entry, dict):
                            menu_key = entry.get(CURRENT_LANG, entry.get("en", filename))
                        else:
                            menu_key = str(entry)
                    else:
                        menu_key = os.path.splitext(filename)[0]
                    noises[menu_key] = file_path
        except OSError: pass
        return noises

    def load_config(self):
        default = {
            "work_noise": "None", "break_noise": "None", "volume": 1.0,
            "show_timer": False, 
            "font_size": 24, "opacity": 0.7, "window_x": None, "window_y": None
        }
        if not os.path.exists(CONFIG_FILE): return default
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                d = json.load(f)
            
            work = d.get("work_noise", "None")
            if work == "なし": work = "None"
            break_ = d.get("break_noise", "None")
            if break_ == "なし": break_ = "None"

            if work not in self.available_noises: work = "None"
            if break_ not in self.available_noises: break_ = "None"
            
            return {
                "work_noise": work, 
                "break_noise": break_,
                "volume": d.get("volume", 1.0),
                "show_timer": d.get("show_timer", False),
                "font_size": d.get("font_size", 24),
                "opacity": d.get("opacity", 0.7),
                "window_x": d.get("window_x"),
                "window_y": d.get("window_y")
            }
        except json.JSONDecodeError: return default

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except IOError: pass

    def open_config_window(self):
        if self.floating_window:
            ConfigWindow(self.floating_window, self.floating_window)

    def open_credits(self):
        if os.path.exists(CREDITS_FILE):
            try:
                if os.name == 'nt':
                    os.startfile(CREDITS_FILE)
                else:
                    opener = "open" if sys.platform == "darwin" else "xdg-open"
                    subprocess.call([opener, CREDITS_FILE])
            except Exception as e:
                print(f"ファイルオープンエラー: {e}")

    def set_volume(self, volume):
        self.config["volume"] = volume
        try:
            pygame.mixer.music.set_volume(volume)
        except pygame.error: pass
        self.save_config()

    def set_noise_config(self, noise_type: str, noise_key: str):
        if noise_key not in self.available_noises: return
        self.config[f"{noise_type}_noise"] = noise_key
        self.save_config()
        if (self.state == self.STATE_WORK and noise_type == "work") or \
           (self.state == self.STATE_BREAK and noise_type == "break"):
            self.play_sound_from_key(noise_key)
        self._update_menu()

    def toggle_timer_display(self):
        current = self.config.get("show_timer", False)
        new_state = not current
        self.config["show_timer"] = new_state
        self.save_config()
        if self.floating_window:
            self.floating_window.toggle_visibility(new_state)
        self._update_menu()

    def play_sound_from_key(self, noise_key: str):
        file_path = self.available_noises.get(noise_key)
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.set_volume(self.config.get("volume", 1.0))
            if file_path and os.path.exists(file_path):
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play(-1)
        except pygame.error: pass

    def stop_sound(self):
        try: pygame.mixer.music.stop()
        except pygame.error: pass

    def start_pomodoro(self):
        if self.state == self.STATE_WORK or self.state == self.STATE_BREAK: return
        sound_key = "None"
        if self.state == self.STATE_STOPPED:
            self.state = self.STATE_WORK
            self.remaining_time = WORK_DURATION
            sound_key = self.config.get("work_noise")
        elif self.state == self.STATE_PAUSED:
            self.state = self.resume_state
            if self.state == self.STATE_WORK: sound_key = self.config.get("work_noise")
            elif self.state == self.STATE_BREAK: sound_key = self.config.get("break_noise")
        
        self.end_time = time.time() + self.remaining_time
        self.play_sound_from_key(sound_key)
        self.stop_event.clear()
        self.timer_thread = threading.Thread(target=self.run_timer, daemon=True)
        self.timer_thread.start()
        self._update_menu()

    def stop_pomodoro(self):
        if self.state == self.STATE_STOPPED or self.state == self.STATE_PAUSED: return
        self.resume_state = self.state
        self.state = self.STATE_PAUSED
        self.stop_event.set()
        if self.timer_thread:
            self.timer_thread.join()
            self.timer_thread = None
        self.stop_sound()
        self._update_menu()

    def reset_timer(self):
        self.stop_event.set()
        if self.timer_thread:
            self.timer_thread.join()
            self.timer_thread = None
        self.stop_sound()
        self.state = self.STATE_STOPPED
        self.remaining_time = WORK_DURATION
        self._update_menu()

    # --- リスタート機能 ---
    def restart_and_pause(self):
        """現在のセッションを初期化し、一時停止状態で待機する"""
        if self.state == self.STATE_STOPPED: return

        if self.state in [self.STATE_WORK, self.STATE_BREAK]:
            self.resume_state = self.state
        
        if self.resume_state == self.STATE_WORK:
            self.remaining_time = WORK_DURATION
        else:
            self.remaining_time = BREAK_DURATION
        
        self.state = self.STATE_PAUSED
        self.stop_event.set()
        if self.timer_thread:
            self.timer_thread.join()
            self.timer_thread = None
        self.stop_sound()
        self._update_menu()

    def run_timer(self):
        while not self.stop_event.is_set():
            if self.stop_event.wait(0.1): break
            if self.state == self.STATE_STOPPED or self.state == self.STATE_PAUSED: break
            
            now = time.time()
            remaining_seconds = self.end_time - now
            self.remaining_time = int(remaining_seconds + 0.9) 

            if remaining_seconds <= 0:
                self.remaining_time = 0
                self._transition_state()
                if self.state in [self.STATE_WORK, self.STATE_BREAK]:
                    self.end_time = time.time() + self.remaining_time
                else:
                    break

    def _transition_state(self):
        if self.state == self.STATE_WORK:
            self.state = self.STATE_BREAK
            self.remaining_time = BREAK_DURATION
            self.play_sound_from_key(self.config.get("break_noise"))
        elif self.state == self.STATE_BREAK:
            self.state = self.STATE_WORK
            self.remaining_time = WORK_DURATION
            self.play_sound_from_key(self.config.get("work_noise"))
        self._update_menu()

    def _update_menu(self):
        if self.icon:
            try: self.icon.update_menu()
            except Exception: pass

    def get_menu_state_text(self) -> str:
        st_text = ""
        if self.state == self.STATE_STOPPED: st_text = tr("state_stopped")
        elif self.state == self.STATE_WORK: st_text = tr("state_work")
        elif self.state == self.STATE_BREAK: st_text = tr("state_break")
        elif self.state == self.STATE_PAUSED: st_text = tr("state_paused")
        
        if self.state == self.STATE_STOPPED:
            return tr("status_fmt").format(state=st_text, time="--:--")
        
        mins, secs = divmod(max(0, self.remaining_time), 60)
        time_str = f"{mins:02d}:{secs:02d}"
        return tr("status_fmt").format(state=st_text, time=time_str)

    def get_start_stop_text(self) -> str:
        if self.state == self.STATE_STOPPED: return tr("start")
        elif self.state == self.STATE_PAUSED: return tr("resume")
        else: return tr("pause")

    def quit_app(self):
        self.stop_event.set()
        if self.timer_thread: self.timer_thread.join()
        pygame.mixer.quit()
        if self.icon: self.icon.stop()
        if self.floating_window: self.floating_window.quit()

# =========================================
# タスクトレイアイコンの設定・実行
# =========================================
def run_tray_icon(timer_app):
    def on_start_stop(icon, item):
        if timer_app.state in [PomodoroTimer.STATE_WORK, PomodoroTimer.STATE_BREAK]:
            timer_app.stop_pomodoro()
        else:
            timer_app.start_pomodoro()

    def on_reset(icon, item): timer_app.reset_timer()
    def on_quit(icon, item): timer_app.quit_app()
    def on_toggle_display(icon, item): timer_app.toggle_timer_display()
    def on_open_credits(icon, item): timer_app.open_credits()
    
    def on_open_settings(icon, item):
        if timer_app.floating_window:
            timer_app.floating_window.after(0, timer_app.open_config_window)

    def create_noise_callback(type_, key):
        return lambda icon, item: timer_app.set_noise_config(type_, key)
    
    def is_noise_checked(type_, key):
        return lambda item: timer_app.config.get(f"{type_}_noise") == key
    
    def is_display_checked(item):
        return timer_app.config.get("show_timer", False)

    def generate_noise_menu(type_):
        key = "None"
        display_key = tr("none")
        
        if key in timer_app.available_noises:
            yield pystray.MenuItem(display_key, create_noise_callback(type_, key), checked=is_noise_checked(type_, key), radio=True)
        
        for key in sorted([k for k in timer_app.available_noises if k != "None"]):
            yield pystray.MenuItem(key, create_noise_callback(type_, key), checked=is_noise_checked(type_, key), radio=True)

    menu = pystray.Menu(
        pystray.MenuItem(lambda text: timer_app.get_start_stop_text(), on_start_stop, default=True),
        pystray.MenuItem(tr("stop_timer"), on_reset),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda text: timer_app.get_menu_state_text(), None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(tr("show_timer"), on_toggle_display, checked=is_display_checked),
        pystray.MenuItem(tr("settings_menu"), on_open_settings),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(tr("work_noise"), pystray.Menu(lambda: generate_noise_menu("work"))),
        pystray.MenuItem(tr("break_noise"), pystray.Menu(lambda: generate_noise_menu("break"))),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(tr("credits"), on_open_credits),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(tr("quit"), on_quit)
    )

    try:
        icon_image = Image.open(ICON_FILE)
    except Exception:
        icon_image = Image.new('RGBA', (64, 64), (0,0,0,0))
        
    icon = pystray.Icon(APP_NAME, icon_image, APP_NAME, menu)
    timer_app.icon = icon
    icon.run()

# =========================================
# メインエントリーポイント
# =========================================
def main():
    app = PomodoroTimer()
    
    tray_thread = threading.Thread(target=run_tray_icon, args=(app,), daemon=True)
    tray_thread.start()

    app.floating_window = FloatingTimer(app)
    
    if app.config.get("show_timer", False):
        app.floating_window.deiconify()
        app.floating_window.is_visible = True
        app.floating_window.refresh_layout()
    else:
        app.floating_window.withdraw()
        app.floating_window.is_visible = False
        
    app.floating_window.mainloop()

if __name__ == "__main__":
    main()