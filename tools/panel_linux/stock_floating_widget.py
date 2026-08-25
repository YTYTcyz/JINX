from __future__ import annotations

import json
import queue
import re
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import font as tkfont
from tkinter import colorchooser, messagebox, ttk


if not getattr(sys, "frozen", False):
    ROOT_DIR = Path(__file__).resolve().parents[2]
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
else:
    ROOT_DIR = Path(sys.executable).resolve().parent

from store_skill.getprice import get_quotes  # noqa: E402
from store_skill.getprice.normalize import normalize_symbol  # noqa: E402


def _resolve_settings_file() -> Path:
    if getattr(sys, "frozen", False):
        # 打包为 exe 后保存到 exe 所在目录，避免落在临时解压目录导致设置丢失。
        return Path(sys.executable).resolve().with_name(".stock_floating_widget_settings.json")
    return Path(__file__).with_name(".stock_floating_widget_settings.json")


SETTINGS_FILE = _resolve_settings_file()
DEFAULT_BG_COLOR = "#37FFFF"
DEFAULT_FG_COLOR = "#000000"


@dataclass
class UiSettings:
    symbols_text: str = "600519,000001,000858,HK:00700,US:AAPL"
    refresh_sec: float = 5.0
    width: int = 320
    height: int = 180
    x: int = 100
    y: int = 100
    bg_color: str = DEFAULT_BG_COLOR
    fg_color: str = DEFAULT_FG_COLOR
    alpha: float = 0.95
    font_family: str = "Noto Sans CJK SC"
    font_size: int = 13
    auto_fit_height: bool = True


class StockFloatingWidgetApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("股票悬浮窗控制台")
        self.root.geometry("760x520")
        self.root.minsize(720, 460)
        self.root.configure(bg="#F3F5F9")
        self._init_ttk_styles()

        self.settings = self._load_settings()
        self.symbols: list[str] = self._parse_symbols(self.settings.symbols_text)
        self.running = False

        self.result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue()
        self.quote_lines: list[tuple[str, float | None]] = []
        self._internal_geometry_update = False
        self._last_window_height = 0

        self._build_control_panel()
        self._build_floating_window()
        self._apply_style()
        self._apply_geometry_from_settings()
        self._schedule_queue_poller()

    def _init_ttk_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure("Panel.TFrame", background="#F3F5F9")
        style.configure("Card.TFrame", background="#FFFFFF")
        style.configure("TLabel", background="#F3F5F9", foreground="#334155")
        style.configure("Title.TLabel", background="#F3F5F9", foreground="#0F172A")
        style.configure("Muted.TLabel", background="#F3F5F9", foreground="#64748B")

        style.configure(
            "TButton",
            padding=(10, 5),
            background="#E2E8F0",
            foreground="#0F172A",
            borderwidth=0,
        )
        style.map(
            "TButton",
            background=[("active", "#CBD5E1"), ("pressed", "#94A3B8")],
            foreground=[("disabled", "#94A3B8")],
        )
        style.configure("Accent.TButton", background="#2563EB", foreground="#FFFFFF")
        style.map(
            "Accent.TButton",
            background=[("active", "#1D4ED8"), ("pressed", "#1E40AF")],
            foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")],
        )

        style.configure(
            "TEntry",
            padding=4,
            fieldbackground="#FFFFFF",
            foreground="#0F172A",
            bordercolor="#CBD5E1",
        )
        style.configure(
            "TCombobox",
            padding=4,
            fieldbackground="#FFFFFF",
            foreground="#0F172A",
            bordercolor="#CBD5E1",
        )
        style.configure("TCheckbutton", background="#F3F5F9", foreground="#334155")
        style.configure("Horizontal.TScale", background="#F3F5F9", troughcolor="#E2E8F0")

    def _load_settings(self) -> UiSettings:
        if not SETTINGS_FILE.exists():
            return UiSettings()
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            settings = UiSettings(**data)
            settings.bg_color = self._safe_hex_color(settings.bg_color, DEFAULT_BG_COLOR)
            settings.fg_color = self._safe_hex_color(settings.fg_color, DEFAULT_FG_COLOR)
            return settings
        except Exception:
            return UiSettings()

    def _save_settings(self) -> None:
        alpha = float(self.alpha_var.get())
        alpha = min(1.0, max(0.01, alpha))
        font_size = max(10, min(48, int(self.font_size_var.get() or 13)))
        data = UiSettings(
            symbols_text=self.symbols_var.get().strip(),
            refresh_sec=max(0.1, float(self.refresh_var.get() or 5)),
            width=max(160, int(self.width_var.get() or 320)),
            height=max(100, int(self.height_var.get() or 180)),
            x=self.float_window.winfo_x(),
            y=self.float_window.winfo_y(),
            bg_color=self._safe_hex_color(self.bg_color_var.get().strip(), DEFAULT_BG_COLOR),
            fg_color=self._safe_hex_color(self.fg_color_var.get().strip(), DEFAULT_FG_COLOR),
            alpha=alpha,
            font_family=self.font_family_var.get().strip() or self._pick_default_font(),
            font_size=font_size,
            auto_fit_height=bool(self.auto_height_var.get()),
        )
        SETTINGS_FILE.write_text(
            json.dumps(data.__dict__, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _parse_symbols(raw: str) -> list[str]:
        tokens = re.split(r"[\s,，;；]+", raw.strip())
        return [token for token in tokens if token]

    def _build_control_panel(self) -> None:
        header = ttk.Frame(self.root, style="Panel.TFrame", padding=(16, 14, 16, 4))
        header.pack(fill=tk.X)
        ttk.Label(header, text="股票悬浮窗控制台", style="Title.TLabel").pack(anchor="w")

        frame = ttk.Frame(self.root, style="Panel.TFrame", padding=(16, 10, 16, 14))
        frame.pack(fill=tk.BOTH, expand=True)

        default_font = self.settings.font_family or self._pick_default_font()
        font_choices = self._list_font_choices()

        self.symbols_var = tk.StringVar(value=self.settings.symbols_text)
        self.refresh_var = tk.StringVar(value=str(self.settings.refresh_sec))
        self.width_var = tk.IntVar(value=max(160, int(self.settings.width)))
        self.height_var = tk.IntVar(value=max(100, int(self.settings.height)))
        self.bg_color_var = tk.StringVar(value=self.settings.bg_color)
        self.fg_color_var = tk.StringVar(value=self.settings.fg_color)
        bg_r, bg_g, bg_b = self._hex_to_rgb(self.bg_color_var.get())
        fg_r, fg_g, fg_b = self._hex_to_rgb(self.fg_color_var.get())
        self.bg_r_var = tk.StringVar(value=str(bg_r))
        self.bg_g_var = tk.StringVar(value=str(bg_g))
        self.bg_b_var = tk.StringVar(value=str(bg_b))
        self.fg_r_var = tk.StringVar(value=str(fg_r))
        self.fg_g_var = tk.StringVar(value=str(fg_g))
        self.fg_b_var = tk.StringVar(value=str(fg_b))
        self.font_family_var = tk.StringVar(value=default_font)
        font_size_init = max(10, min(48, int(self.settings.font_size)))
        self.font_size_var = tk.IntVar(value=font_size_init)
        self.font_size_text_var = tk.StringVar(value=str(font_size_init))
        self.alpha_var = tk.DoubleVar(value=min(1.0, max(0.01, float(self.settings.alpha))))
        self.alpha_text_var = tk.StringVar(value=f"{self.alpha_var.get():.2f}")
        self.auto_height_var = tk.BooleanVar(value=bool(self.settings.auto_fit_height))

        ttk.Label(frame, text="股票代码（逗号/空格分隔；A股 600519，港股 HK:00700，美股 US:AAPL）").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.symbols_var).grid(
            row=1, column=0, columnspan=7, sticky="ew", pady=(6, 12), ipady=1
        )

        ttk.Label(frame, text="刷新秒数").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, width=8, textvariable=self.refresh_var).grid(row=3, column=0, sticky="w", ipady=1)

        ttk.Label(frame, text="宽").grid(row=2, column=1, sticky="w", padx=(12, 0))
        ttk.Entry(frame, width=8, textvariable=self.width_var).grid(row=3, column=1, sticky="w", padx=(12, 0), ipady=1)

        ttk.Label(frame, text="高").grid(row=2, column=2, sticky="w", padx=(12, 0))
        ttk.Entry(frame, width=8, textvariable=self.height_var).grid(row=3, column=2, sticky="w", padx=(12, 0), ipady=1)
        ttk.Button(frame, text="应用尺寸", command=self._apply_size_from_controls, style="Accent.TButton").grid(
            row=3, column=3, sticky="w", padx=(12, 0)
        )

        ttk.Label(frame, text="悬浮窗底色").grid(row=4, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, width=12, textvariable=self.bg_color_var).grid(row=5, column=0, sticky="w", ipady=1)
        ttk.Button(frame, text="选择颜色", command=self.pick_bg_color).grid(row=5, column=1, sticky="w", padx=(12, 0))
        ttk.Button(frame, text="屏幕取色", command=lambda: self.pick_color_from_screen("bg")).grid(
            row=5, column=2, sticky="w", padx=(12, 0)
        )
        ttk.Label(frame, text="RGB").grid(row=4, column=3, sticky="e", pady=(12, 0))
        ttk.Entry(frame, width=4, textvariable=self.bg_r_var, state="readonly").grid(row=5, column=3, sticky="w")
        ttk.Entry(frame, width=4, textvariable=self.bg_g_var, state="readonly").grid(row=5, column=4, sticky="w")
        ttk.Entry(frame, width=4, textvariable=self.bg_b_var, state="readonly").grid(row=5, column=5, sticky="w")

        ttk.Label(frame, text="文字颜色").grid(row=6, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, width=12, textvariable=self.fg_color_var).grid(row=7, column=0, sticky="w", ipady=1)
        ttk.Button(frame, text="选择颜色", command=self.pick_fg_color).grid(row=7, column=1, sticky="w", padx=(12, 0))
        ttk.Button(frame, text="屏幕取色", command=lambda: self.pick_color_from_screen("fg")).grid(
            row=7, column=2, sticky="w", padx=(12, 0)
        )
        ttk.Label(frame, text="RGB").grid(row=6, column=3, sticky="e", pady=(12, 0))
        ttk.Entry(frame, width=4, textvariable=self.fg_r_var, state="readonly").grid(row=7, column=3, sticky="w")
        ttk.Entry(frame, width=4, textvariable=self.fg_g_var, state="readonly").grid(row=7, column=4, sticky="w")
        ttk.Entry(frame, width=4, textvariable=self.fg_b_var, state="readonly").grid(row=7, column=5, sticky="w")
        ttk.Button(frame, text="应用颜色", command=self._apply_style, style="Accent.TButton").grid(
            row=7, column=6, sticky="w", padx=(12, 0)
        )
        ttk.Button(frame, text="恢复默认配色", command=self.reset_default_colors).grid(
            row=8, column=6, sticky="w", padx=(12, 0)
        )

        ttk.Label(frame, text="字体").grid(row=8, column=0, sticky="w", pady=(12, 0))
        self.font_combo = ttk.Combobox(
            frame,
            textvariable=self.font_family_var,
            values=font_choices,
            width=22,
        )
        self.font_combo.grid(row=9, column=0, columnspan=2, sticky="w")

        ttk.Label(frame, text="字号").grid(row=8, column=2, sticky="w", pady=(12, 0))
        ttk.Scale(
            frame,
            from_=10,
            to=48,
            variable=self.font_size_var,
            command=self._on_font_size_scale,
        ).grid(row=9, column=2, columnspan=2, sticky="ew", padx=(0, 8))
        ttk.Label(frame, textvariable=self.font_size_text_var, width=4).grid(row=9, column=4, sticky="w")
        ttk.Button(frame, text="应用字体", command=self._apply_font, style="Accent.TButton").grid(
            row=9, column=5, sticky="w", padx=(12, 0)
        )

        ttk.Label(frame, text="透明度").grid(row=10, column=0, sticky="w", pady=(12, 0))
        ttk.Scale(
            frame,
            from_=0.01,
            to=1.00,
            variable=self.alpha_var,
            command=self._on_alpha_scale,
        ).grid(row=11, column=0, columnspan=3, sticky="ew")
        ttk.Label(frame, textvariable=self.alpha_text_var, width=6).grid(row=11, column=3, sticky="w")
        ttk.Button(frame, text="应用透明度", command=self._apply_alpha, style="Accent.TButton").grid(
            row=11, column=4, sticky="w", padx=(12, 0)
        )
        ttk.Checkbutton(frame, text="按行数自动高度", variable=self.auto_height_var).grid(
            row=11, column=5, columnspan=2, sticky="w", padx=(8, 0)
        )

        ttk.Separator(frame, orient="horizontal").grid(row=12, column=0, columnspan=7, sticky="ew", pady=(8, 10))

        action_frame = ttk.Frame(frame, style="Panel.TFrame")
        action_frame.grid(row=13, column=0, columnspan=7, sticky="ew", pady=(6, 0))
        ttk.Button(action_frame, text="更新股票列表", command=self.apply_symbols).pack(side=tk.LEFT)
        ttk.Button(action_frame, text="立即刷新", command=self.refresh_once, style="Accent.TButton").pack(
            side=tk.LEFT, padx=(8, 0)
        )
        self.toggle_btn = ttk.Button(action_frame, text="开始自动刷新", command=self.toggle_running, style="Accent.TButton")
        self.toggle_btn.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(action_frame, text="保存配置", command=self._save_settings).pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value="状态：待机")
        ttk.Label(frame, textvariable=self.status_var).grid(
            row=14, column=0, columnspan=7, sticky="w", pady=(12, 0)
        )

        for col in range(7):
            frame.columnconfigure(col, weight=1 if col == 0 else 0)
        frame.columnconfigure(1, weight=0)
        frame.columnconfigure(4, weight=1)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_floating_window(self) -> None:
        self.float_window = tk.Toplevel(self.root)
        self.float_window.title("")
        self.float_window.attributes("-topmost", True)
        self.float_window.overrideredirect(True)
        self.float_window.resizable(False, False)

        self.float_container = tk.Frame(self.float_window, bd=1, relief=tk.SOLID)
        self.float_container.pack(fill=tk.BOTH, expand=True)

        self.header = tk.Frame(self.float_container, height=24, cursor="fleur")
        self.header.pack(fill=tk.X)
        self.show_btn = tk.Button(
            self.header,
            text="⚙",
            width=2,
            height=1,
            bd=0,
            command=self.show_control_panel,
            cursor="hand2",
        )
        self.show_btn.pack(side=tk.LEFT, padx=(2, 1), pady=1)
        self.title_label = tk.Label(self.header, text="", anchor="w")
        self.title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.close_btn = tk.Button(
            self.header,
            text="X",
            width=2,
            height=1,
            bd=0,
            command=self.exit_app,
            cursor="hand2",
        )
        self.close_btn.pack(side=tk.RIGHT, padx=(1, 2), pady=1)

        self.content = tk.Text(
            self.float_container,
            height=8,
            wrap=tk.NONE,
            bd=0,
            highlightthickness=0,
            state=tk.DISABLED,
        )
        self.content.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        self.resize_handle = tk.Label(
            self.float_container,
            text="⇲",
            cursor="bottom_right_corner",
            width=2,
            height=1,
            bd=1,
            relief=tk.SOLID,
        )
        self.resize_handle.place(relx=1.0, rely=1.0, x=-2, y=-2, anchor="se")

        self.header.bind("<ButtonPress-1>", self._on_drag_start)
        self.header.bind("<B1-Motion>", self._on_drag_motion)
        self.title_label.bind("<ButtonPress-1>", self._on_drag_start)
        self.title_label.bind("<B1-Motion>", self._on_drag_motion)
        self.resize_handle.bind("<ButtonPress-1>", self._on_resize_start)
        self.resize_handle.bind("<B1-Motion>", self._on_resize_motion)

        self._drag_start_xy = (0, 0)
        self._drag_window_xy = (0, 0)
        self._resize_start_xy = (0, 0)
        self._resize_start_wh = (0, 0)

    def _pick_default_font(self) -> str:
        names = set(tkfont.families(self.root))
        candidates = [
            "Noto Sans CJK SC",
            "Source Han Sans SC",
            "WenQuanYi Micro Hei",
            "Microsoft YaHei",
            "PingFang SC",
            "SimHei",
            "Arial",
        ]
        for name in candidates:
            if name in names:
                return name
        return "TkDefaultFont"

    def _list_font_choices(self) -> list[str]:
        names = set(tkfont.families(self.root))
        preferred = [
            "Noto Sans CJK SC",
            "Source Han Sans SC",
            "WenQuanYi Micro Hei",
            "Microsoft YaHei",
            "PingFang SC",
            "SimHei",
            "Arial",
            "Helvetica",
        ]
        choices = [name for name in preferred if name in names]
        fallback = sorted([name for name in names if "Sans" in name or "Hei" in name])[:12]
        merged = choices + [name for name in fallback if name not in choices]
        return merged or [self._pick_default_font()]

    def _apply_geometry_from_settings(self) -> None:
        width = max(160, int(self.settings.width))
        height = max(100, int(self.settings.height))
        x = int(self.settings.x)
        y = int(self.settings.y)
        self._set_window_geometry(f"{width}x{height}+{x}+{y}")

    def _on_drag_start(self, event: tk.Event) -> None:
        self._drag_start_xy = (event.x_root, event.y_root)
        self._drag_window_xy = (self.float_window.winfo_x(), self.float_window.winfo_y())

    def _on_drag_motion(self, event: tk.Event) -> None:
        dx = event.x_root - self._drag_start_xy[0]
        dy = event.y_root - self._drag_start_xy[1]
        x = self._drag_window_xy[0] + dx
        y = self._drag_window_xy[1] + dy
        self._set_window_geometry(f"+{x}+{y}")

    def _on_resize_start(self, event: tk.Event) -> None:
        self._resize_start_xy = (event.x_root, event.y_root)
        self._resize_start_wh = (self.float_window.winfo_width(), self.float_window.winfo_height())

    def _on_resize_motion(self, event: tk.Event) -> None:
        dx = event.x_root - self._resize_start_xy[0]
        dy = event.y_root - self._resize_start_xy[1]
        width = max(160, self._resize_start_wh[0] + dx)
        height = max(100, self._resize_start_wh[1] + dy)
        if self.auto_height_var.get():
            self.auto_height_var.set(False)
            self.status_var.set("状态：检测到手动改高，已关闭自动高度")
        self._set_window_geometry(f"{width}x{height}")
        self.width_var.set(width)
        self.height_var.set(height)

    def _on_float_configure(self, event: tk.Event) -> None:
        if event.widget is not self.float_window:
            return
        width = max(160, int(self.float_window.winfo_width()))
        height = max(100, int(self.float_window.winfo_height()))
        if (not self._internal_geometry_update) and self._last_window_height and height != self._last_window_height:
            if self.auto_height_var.get():
                self.auto_height_var.set(False)
                self.status_var.set("状态：检测到手动改高，已关闭自动高度")
        self.width_var.set(width)
        self.height_var.set(height)
        self._last_window_height = height

    def apply_symbols(self) -> None:
        symbols = self._parse_symbols(self.symbols_var.get())
        if not symbols:
            messagebox.showwarning("提示", "请至少输入一个股票代码")
            return
        self.symbols = symbols
        self.status_var.set(f"状态：已更新股票列表，共 {len(symbols)} 只")

    def _apply_size_from_controls(self) -> None:
        try:
            width = max(160, int(self.width_var.get()))
            height = max(100, int(self.height_var.get()))
        except (ValueError, tk.TclError):
            messagebox.showerror("输入错误", "宽高必须是数字")
            return
        if self.auto_height_var.get():
            self.auto_height_var.set(False)
        x = self.float_window.winfo_x()
        y = self.float_window.winfo_y()
        self._set_window_geometry(f"{width}x{height}+{x}+{y}")

    def _set_window_geometry(self, geometry: str) -> None:
        self._internal_geometry_update = True
        try:
            self.float_window.geometry(geometry)
        finally:
            self._internal_geometry_update = False

    def show_control_panel(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def pick_bg_color(self) -> None:
        selected = colorchooser.askcolor(color=self.bg_color_var.get(), title="选择背景色")
        if selected and selected[1]:
            self._set_bg_color(selected[1], apply_style=True)

    def pick_fg_color(self) -> None:
        selected = colorchooser.askcolor(color=self.fg_color_var.get(), title="选择前景色")
        if selected and selected[1]:
            self._set_fg_color(selected[1], apply_style=True)

    @staticmethod
    def _hex_to_rgb(color: str) -> tuple[int, int, int]:
        color = color.strip()
        if not color.startswith("#") or len(color) != 7:
            return 0, 0, 0
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            return r, g, b
        except ValueError:
            return 0, 0, 0

    @staticmethod
    def _rgb_to_hex(r: int, g: int, b: int) -> str:
        return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"

    @staticmethod
    def _safe_hex_color(color: str, default: str) -> str:
        text = (color or "").strip().upper()
        if re.fullmatch(r"#[0-9A-F]{6}", text):
            return text
        return default

    def _set_bg_color(self, hex_color: str, *, apply_style: bool = False) -> None:
        normalized = self._safe_hex_color(hex_color, DEFAULT_BG_COLOR)
        self.bg_color_var.set(normalized)
        r, g, b = self._hex_to_rgb(normalized)
        self.bg_r_var.set(str(r))
        self.bg_g_var.set(str(g))
        self.bg_b_var.set(str(b))
        if apply_style:
            self._apply_style()

    def _set_fg_color(self, hex_color: str, *, apply_style: bool = False) -> None:
        normalized = self._safe_hex_color(hex_color, DEFAULT_FG_COLOR)
        self.fg_color_var.set(normalized)
        r, g, b = self._hex_to_rgb(normalized)
        self.fg_r_var.set(str(r))
        self.fg_g_var.set(str(g))
        self.fg_b_var.set(str(b))
        if apply_style:
            self._apply_style()

    def reset_default_colors(self) -> None:
        self._set_bg_color(DEFAULT_BG_COLOR)
        self._set_fg_color(DEFAULT_FG_COLOR)
        self._apply_style()
        self.status_var.set("状态：已恢复默认配色")

    def pick_color_from_screen(self, target: str) -> None:
        try:
            from PIL import ImageGrab, ImageTk
        except Exception:
            messagebox.showerror("缺少依赖", "屏幕取色需要 Pillow，请先执行：pip install pillow")
            return

        self.status_var.set("状态：请在全屏截图上点击取色点，Esc 取消")
        self.root.withdraw()
        self.float_window.withdraw()

        picker: tk.Toplevel | None = None

        def _restore_main_windows() -> None:
            self.root.deiconify()
            self.float_window.deiconify()
            self.root.lift()
            self.float_window.lift()

        try:
            screenshot = ImageGrab.grab()
        except Exception as exc:
            _restore_main_windows()
            self.status_var.set("状态：当前环境不支持屏幕取色，已切换为普通取色")
            messagebox.showwarning(
                "屏幕取色不可用",
                f"当前环境无法截图取色（{exc}）。\n已自动切换为普通颜色选择器。",
            )
            if target == "bg":
                self.pick_bg_color()
            else:
                self.pick_fg_color()
            return

        picker = tk.Toplevel()
        picker.attributes("-topmost", True)
        picker.attributes("-fullscreen", True)
        picker.overrideredirect(True)

        tk_image = ImageTk.PhotoImage(screenshot)
        canvas = tk.Canvas(picker, highlightthickness=0, bd=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.create_image(0, 0, image=tk_image, anchor="nw")
        canvas.image = tk_image

        def _cancel(_: tk.Event | None = None) -> None:
            if picker is not None and picker.winfo_exists():
                picker.destroy()
            _restore_main_windows()
            self.status_var.set("状态：已取消屏幕取色")

        def _pick(event: tk.Event) -> None:
            x, y = int(event.x), int(event.y)
            pixel = screenshot.getpixel((x, y))
            if isinstance(pixel, tuple) and len(pixel) >= 3:
                r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
                hex_color = self._rgb_to_hex(r, g, b)
                if target == "bg":
                    self._set_bg_color(hex_color, apply_style=True)
                else:
                    self._set_fg_color(hex_color, apply_style=True)
                self.status_var.set(f"状态：取色成功 RGB({r},{g},{b})")
            _cancel()

        canvas.bind("<Button-1>", _pick)
        picker.bind("<Escape>", _cancel)

    def _apply_style(self) -> None:
        bg = self._safe_hex_color(self.bg_color_var.get().strip(), DEFAULT_BG_COLOR)
        fg = self._safe_hex_color(self.fg_color_var.get().strip(), DEFAULT_FG_COLOR)
        try:
            self._set_bg_color(bg)
            self._set_fg_color(fg)
            self.float_container.configure(bg=bg)
            self.header.configure(bg=bg)
            self.title_label.configure(bg=bg, fg=fg)
            if self.show_btn is not None:
                self.show_btn.configure(bg=bg, fg=fg, activebackground=bg, activeforeground=fg)
            if self.close_btn is not None:
                self.close_btn.configure(bg=bg, fg=fg, activebackground=bg, activeforeground=fg)
            self.content.configure(bg=bg, fg=fg, insertbackground=fg)
            self.resize_handle.configure(bg=bg, fg=fg, highlightbackground=fg, highlightcolor=fg)
            self.content.tag_configure("up", foreground="#FF3030")
            self.content.tag_configure("down", foreground="#00B050")
            self.content.tag_configure("flat", foreground=fg)
            self.status_var.set("状态：颜色已应用")
        except tk.TclError as exc:
            messagebox.showerror("颜色错误", f"颜色无效：{exc}")

    def _on_font_size_scale(self, value: str) -> None:
        size = max(10, min(48, int(float(value))))
        self.font_size_var.set(size)
        self.font_size_text_var.set(str(size))
        self._apply_font(silent=True)

    def _apply_font(self, *, silent: bool = False) -> None:
        family = self.font_family_var.get().strip() or self._pick_default_font()
        try:
            size = max(10, min(48, int(self.font_size_var.get())))
        except ValueError:
            messagebox.showerror("字号错误", "字号必须是数字")
            return
        self.font_size_var.set(size)
        self.font_size_text_var.set(str(size))
        content_font = tkfont.Font(family=family, size=size, weight="bold")
        header_font = tkfont.Font(family=family, size=max(10, size - 1), weight="bold")
        button_font = tkfont.Font(family=family, size=max(9, size - 2), weight="normal")
        self.content.configure(font=content_font, spacing1=1, spacing2=1, spacing3=2)
        self.title_label.configure(font=header_font)
        if self.show_btn is not None:
            self.show_btn.configure(font=button_font)
        if self.close_btn is not None:
            self.close_btn.configure(font=button_font)
        if not silent:
            self.status_var.set(f"状态：已应用字体 {family} {size}px")

    def _on_alpha_scale(self, _: str) -> None:
        self.alpha_text_var.set(f"{self.alpha_var.get():.2f}")
        self._apply_alpha()

    def _apply_alpha(self) -> None:
        alpha = min(1.0, max(0.01, float(self.alpha_var.get())))
        self.alpha_var.set(alpha)
        self.alpha_text_var.set(f"{alpha:.2f}")
        try:
            self.float_window.attributes("-alpha", alpha)
            self.status_var.set(f"状态：透明度已应用 {alpha:.2f}")
        except tk.TclError as exc:
            self.status_var.set(f"状态：当前系统不支持透明度 ({exc})")

    def refresh_once(self) -> None:
        self.apply_symbols()
        symbols = list(self.symbols)
        if not symbols:
            return
        self.status_var.set("状态：正在刷新行情...")
        thread = threading.Thread(target=self._fetch_quotes_worker, args=(symbols,), daemon=True)
        thread.start()

    @staticmethod
    def _quote_identity(symbol: str) -> tuple[str, str] | None:
        try:
            info = normalize_symbol(symbol)
        except ValueError:
            return None
        return info.market, info.symbol

    def _fetch_quotes_worker(self, symbols: list[str]) -> None:
        try:
            result = get_quotes(symbols)
            if not result.ok:
                self.result_queue.put((False, result.error or "未知错误"))
                return
            lines: list[tuple[str, float | None]] = []
            rows = result.data or []
            by_identity = {(str(row.get("market") or ""), str(row.get("symbol") or "")): row for row in rows}
            for symbol in symbols:
                row = by_identity.get(self._quote_identity(symbol))
                if not row:
                    lines.append((f"{symbol}  数据缺失", None))
                    continue
                name = row.get("name") or "-"
                price = row.get("price")
                pct = row.get("change_pct")
                market = str(row.get("market") or "")
                try:
                    decimals = 3 if market in {"SH", "SZ", "BJ"} else 2
                    price_text = f"{float(price):.{decimals}f}"
                except (TypeError, ValueError):
                    price_text = str(price or "-")
                if isinstance(pct, (int, float)):
                    pct_text = f"{pct:+.2f}%"
                    pct_value: float | None = float(pct)
                else:
                    pct_text = "-"
                    pct_value = None
                source = row.get("source") or "-"
                quote_time = row.get("time")
                time_text = f"{quote_time}" if quote_time else "时间未知"
                lines.append((f"{symbol} {name}  {price_text}  {pct_text}  [{source} {time_text}]", pct_value))
            self.result_queue.put((True, lines))
        except Exception as exc:  # noqa: BLE001
            self.result_queue.put((False, str(exc)))

    def _schedule_queue_poller(self) -> None:
        self.root.after(200, self._poll_result_queue)

    def _poll_result_queue(self) -> None:
        try:
            while True:
                ok, payload = self.result_queue.get_nowait()
                if ok:
                    self.quote_lines = payload
                    self._render_quote_lines(payload)
                    self.status_var.set("状态：刷新成功（免费源可能延迟）")
                else:
                    self.status_var.set(f"状态：刷新失败 - {payload}")
        except queue.Empty:
            pass
        finally:
            self._schedule_queue_poller()

    def _render_quote_lines(self, lines: list[tuple[str, float | None]]) -> None:
        self.content.configure(state=tk.NORMAL)
        self.content.delete("1.0", tk.END)
        for line_text, pct_value in lines:
            if pct_value is None:
                tag = "flat"
            elif pct_value > 0:
                tag = "up"
            elif pct_value < 0:
                tag = "down"
            else:
                tag = "flat"
            self.content.insert(tk.END, line_text + "\n", tag)
        self.content.configure(state=tk.DISABLED)
        self._fit_height_to_line_count(lines)

    def _fit_height_to_line_count(self, lines: list[str]) -> None:
        if not self.auto_height_var.get():
            return
        line_count = max(1, len(lines))
        try:
            content_font = tkfont.Font(font=self.content.cget("font"))
            line_height = max(14, int(content_font.metrics("linespace")))
        except Exception:
            line_height = 16

        # 总高度 = 顶栏 + 文本行高 + 内边距 + 右下角缩放区
        header_height = max(6, self.header.winfo_height())
        vertical_padding = 22
        resize_zone = 14
        target_height = header_height + (line_count * (line_height + 2)) + vertical_padding + resize_zone
        target_height = max(100, min(900, target_height))

        width = max(160, int(self.width_var.get()))
        x = self.float_window.winfo_x()
        y = self.float_window.winfo_y()
        self._set_window_geometry(f"{width}x{target_height}+{x}+{y}")
        self.height_var.set(target_height)

    def toggle_running(self) -> None:
        self.running = not self.running
        if self.running:
            self.toggle_btn.configure(text="停止自动刷新")
            self.status_var.set("状态：自动刷新中")
            self._auto_refresh_loop()
        else:
            self.toggle_btn.configure(text="开始自动刷新")
            self.status_var.set("状态：已停止自动刷新")

    def _auto_refresh_loop(self) -> None:
        if not self.running:
            return
        self.refresh_once()
        try:
            interval_sec = max(0.1, float(self.refresh_var.get()))
            delay_ms = int(interval_sec * 1000)
        except ValueError:
            delay_ms = 5000
            self.refresh_var.set("5.0")
        self.root.after(delay_ms, self._auto_refresh_loop)

    def on_close(self) -> None:
        self._save_settings()
        self.root.withdraw()

    def exit_app(self) -> None:
        self.running = False
        self._save_settings()
        if self.float_window.winfo_exists():
            self.float_window.destroy()
        self.root.destroy()

    def run(self) -> None:
        self.float_window.deiconify()
        self._apply_font()
        self._apply_alpha()
        self.root.mainloop()


def main() -> None:
    app = StockFloatingWidgetApp()
    app.run()


if __name__ == "__main__":
    main()
