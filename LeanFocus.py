# -*- coding: utf-8 -*-
import threading
import time
import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw
import pystray
import pygame
import ctypes

# --- Windowsの高DPIスケーリングに対応 ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except (AttributeError, OSError):
    try:
        ctypes.windll.user32.SetProcessDpiAware()
    except (AttributeError, OSError):
        pass

# --- グローバル設定 ---
CONFIG_FILE = 'LeanFocus_config.json'
WORK_DURATION = 25 * 60
BREAK_DURATION = 5 * 60
APP_NAME = "LeanFocus"
ASSET_DIR = "assets"
IMG_DIR = os.path.join(ASSET_DIR, "img")
SOUND_DIR = os.path.join(ASSET_DIR, "sounds")
ICON_FILE = os.path.join(IMG_DIR, "icon.png")
SOUND_NAMES_FILE = os.path.join(SOUND_DIR, "sound_names.json")
CREDITS_FILE = os.path.join(ASSET_DIR, "CREDITS.txt")

SUPPORTED_EXTENSIONS = ('.mp3', '.wav', '.ogg')

class ConfigWindow(tk.Toplevel):
    """
    設定ウィンドウ（表示・音量）
    """
    def __init__(self, parent, timer_window):
        super().__init__(parent)
        self.timer_window = timer_window
        self.app = timer_window.timer_app # アプリロジックへの参照
        
        self.title("設定")
        self.geometry("300x380") # 高さを拡張
        self.resizable(False, False)
        self.attributes("-topmost", True)

        # 全体コンテナ
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill='both', expand=True)

        # --- サウンド設定セクション ---
        ttk.Label(main_frame, text="サウンド設定", font=("", 10, "bold")).pack(anchor='w', pady=(0, 10))
        
        # 音量
        ttk.Label(main_frame, text="音量調整").pack(anchor='w')
        # デフォルト1.0 (100%)
        self.volume_var = tk.DoubleVar(value=self.app.config.get("volume", 1.0))
        scale_vol = ttk.Scale(main_frame, from_=0.0, to=1.0, variable=self.volume_var, command=self.on_volume_change)
        scale_vol.pack(fill='x', pady=(0, 15))

        # 区切り線
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=10)

        # --- 表示設定セクション ---
        ttk.Label(main_frame, text="表示設定 (タイマー)", font=("", 10, "bold")).pack(anchor='w', pady=(0, 10))

        # サイズ
        ttk.Label(main_frame, text="サイズ調整").pack(anchor='w')
        self.size_var = tk.DoubleVar(value=timer_window.font_size)
        scale_size = ttk.Scale(main_frame, from_=12, to=72, variable=self.size_var, command=self.on_visual_change)
        scale_size.pack(fill='x', pady=(0, 15))

        # 透明度
        ttk.Label(main_frame, text="不透明度").pack(anchor='w')
        self.alpha_var = tk.DoubleVar(value=timer_window.opacity)
        scale_alpha = ttk.Scale(main_frame, from_=0.1, to=1.0, variable=self.alpha_var, command=self.on_visual_change)
        scale_alpha.pack(fill='x', pady=(0, 5))

        # 説明
        ttk.Label(main_frame, text="※ウィンドウ位置はドラッグで移動・保存されます", font=("", 8), foreground="gray").pack(pady=(5, 0))

        # 閉じるボタン
        ttk.Button(main_frame, text="閉じる", command=self.destroy).pack(side='bottom', anchor='e', pady=10)

    def on_visual_change(self, event=None):
        """見た目の変更を適用"""
        self.timer_window.apply_visual_settings(self.size_var.get(), self.alpha_var.get())

    def on_volume_change(self, event=None):
        """音量の変更を適用"""
        self.app.set_volume(self.volume_var.get())


class FloatingTimer(tk.Tk):
    """
    フローティングタイマーウィンドウ
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

        self.label = tk.Label(
            self, 
            text="--:--", 
            font=("Segoe UI", self.font_size, "bold"),
            fg="#E0E0E0", 
            bg="black"
        )
        self.label.pack(expand=True, fill='both', padx=5, pady=5)

        self.refresh_layout()

        self.label.bind("<Button-1>", self.start_move)
        self.label.bind("<B1-Motion>", self.do_move)
        self.label.bind("<ButtonRelease-1>", self.on_release)
        self.label.bind("<Enter>", self.on_hover_enter)
        self.label.bind("<Leave>", self.on_hover_leave)
        
        self.x = 0
        self.y = 0
        self.is_visible = False

        self.update_timer_display()

    def refresh_layout(self):
        """ウィンドウサイズと位置を強制的に再適用する"""
        # 幅係数 9.5 (文字切れ対策済み)
        win_w = int(self.font_size * 9.5)
        win_h = int(self.font_size * 2.0)
        
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
        self.label.config(font=("Segoe UI", self.font_size, "bold"))

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def on_release(self, event):
        self.timer_app.config["window_x"] = self.winfo_x()
        self.timer_app.config["window_y"] = self.winfo_y()
        self.timer_app.save_config()

    def on_hover_enter(self, event):
        current = self.attributes("-alpha")
        self.attributes("-alpha", min(1.0, current + 0.2))

    def on_hover_leave(self, event):
        self.attributes("-alpha", self.opacity)

    def apply_visual_settings(self, size, opacity):
        self.font_size = int(float(size))
        self.opacity = float(opacity)
        self.attributes("-alpha", self.opacity)
        
        win_w = int(self.font_size * 9.5)
        win_h = int(self.font_size * 2.0)
        x = self.winfo_x()
        y = self.winfo_y()
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        
        self.label.config(font=("Segoe UI", self.font_size, "bold"))
        
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
        
        status_text = ""
        color = "#E0E0E0"
        
        if state == PomodoroTimer.STATE_WORK:
            status_text = "WORK"
            color = "#9E9E9E"
        elif state == PomodoroTimer.STATE_BREAK:
            status_text = "BREAK"
            color = "#80CBC4"
        elif state == PomodoroTimer.STATE_PAUSED:
            status_text = "PAUSE"
            color = "#FFF59D"
        else:
            status_text = "STOP"
            color = "#FF8A80"
            time_text = "--:--"

        display_text = f"{status_text}   {time_text}"
        self.label.config(text=display_text, fg=color)

        if self.is_visible:
            self.lift()
            self.attributes("-topmost", True)

        self.after(200, self.update_timer_display)


class PomodoroTimer:
    STATE_STOPPED = "停止中"
    STATE_WORK = "作業中"
    STATE_BREAK = "休憩中"
    STATE_PAUSED = "一時停止中"

    def __init__(self):
        self.state = self.STATE_STOPPED
        self.resume_state = self.STATE_WORK
        self.remaining_time = WORK_DURATION
        
        self.stop_event = threading.Event()
        self.timer_thread = None
        
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
        noises = {"なし": None}
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
                        menu_key = name_map[filename]
                    else:
                        menu_key = os.path.splitext(filename)[0]
                    noises[menu_key] = file_path
        except OSError: pass
        return noises

    def load_config(self):
        # デフォルト設定 (volume: 1.0 = 100%)
        default = {
            "work_noise": "なし", "break_noise": "なし", "volume": 1.0,
            "show_timer": False, 
            "font_size": 24, "opacity": 0.7, "window_x": None, "window_y": None
        }
        if not os.path.exists(CONFIG_FILE): return default
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                d = json.load(f)
            
            work = d.get("work_noise", "なし")
            if work not in self.available_noises: work = "なし"
            break_ = d.get("break_noise", "なし")
            if break_ not in self.available_noises: break_ = "なし"
            
            return {
                "work_noise": work, 
                "break_noise": break_,
                "volume": d.get("volume", 1.0), # 音量設定
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
            if not self.floating_window.is_visible:
                self.toggle_timer_display()
            ConfigWindow(self.floating_window, self.floating_window)

    def open_credits(self):
        """CREDITS.txt を開く"""
        if os.path.exists(CREDITS_FILE):
            try:
                if os.name == 'nt':
                    os.startfile(CREDITS_FILE)
                else:
                    opener = "open" if sys.platform == "darwin" else "xdg-open"
                    subprocess.call([opener, CREDITS_FILE])
            except Exception as e:
                print(f"ファイルオープンエラー: {e}")

    # --- [新機能] 音量設定 ---
    def set_volume(self, volume):
        """音量を設定し、反映する (0.0 - 1.0)"""
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
            # [修正] 再生前に設定された音量を適用
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
        sound_key = "なし"
        if self.state == self.STATE_STOPPED:
            self.state = self.STATE_WORK
            self.remaining_time = WORK_DURATION
            sound_key = self.config.get("work_noise")
        elif self.state == self.STATE_PAUSED:
            self.state = self.resume_state
            if self.state == self.STATE_WORK: sound_key = self.config.get("work_noise")
            elif self.state == self.STATE_BREAK: sound_key = self.config.get("break_noise")
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

    def run_timer(self):
        while not self.stop_event.is_set():
            if self.stop_event.wait(1.0): break
            if self.state == self.STATE_STOPPED or self.state == self.STATE_PAUSED: break
            self.remaining_time -= 1
            if self.remaining_time < 0:
                self._transition_state()

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
        if self.state == self.STATE_STOPPED: return f"状態: {self.STATE_STOPPED}"
        mins, secs = divmod(max(0, self.remaining_time), 60)
        return f"状態: {self.state} (残り {mins:02d}:{secs:02d})"

    def get_start_stop_text(self) -> str:
        if self.state == self.STATE_STOPPED: return "タイマーを開始"
        elif self.state == self.STATE_PAUSED: return "タイマーを再開"
        else: return "タイマーを一時停止"

    def quit_app(self):
        self.stop_event.set()
        if self.timer_thread: self.timer_thread.join()
        pygame.mixer.quit()
        if self.icon: self.icon.stop()
        if self.floating_window: self.floating_window.quit()

# --- pystray設定 ---

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
        key = "なし"
        if key in timer_app.available_noises:
            yield pystray.MenuItem(key, create_noise_callback(type_, key), checked=is_noise_checked(type_, key), radio=True)
        for key in sorted([k for k in timer_app.available_noises if k != "なし"]):
            yield pystray.MenuItem(key, create_noise_callback(type_, key), checked=is_noise_checked(type_, key), radio=True)

    menu = pystray.Menu(
        pystray.MenuItem(lambda text: timer_app.get_start_stop_text(), on_start_stop, default=True),
        pystray.MenuItem("タイマーを停止", on_reset),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda text: timer_app.get_menu_state_text(), None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("タイマーを表示", on_toggle_display, checked=is_display_checked),
        pystray.MenuItem("設定...", on_open_settings),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("作業用ノイズ", pystray.Menu(lambda: generate_noise_menu("work"))),
        pystray.MenuItem("休憩用ノイズ", pystray.Menu(lambda: generate_noise_menu("break"))),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("クレジット", on_open_credits),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("アプリを終了", on_quit)
    )

    try:
        icon_image = Image.open(ICON_FILE)
    except Exception:
        icon_image = Image.new('RGBA', (64, 64), (0,0,0,0))
        
    icon = pystray.Icon(APP_NAME, icon_image, APP_NAME, menu)
    timer_app.icon = icon
    icon.run()

# --- メイン実行 ---
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