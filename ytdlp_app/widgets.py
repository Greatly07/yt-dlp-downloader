import math
import tkinter as tk
from tkinter import messagebox

# ============================================================================
# SONGPULSE COLOR PALETTES (Dark & Light)
# ============================================================================
SONGPULSE_DARK = {
    "bg": "#0e1013",             # Main content background
    "sidebar_bg": "#131519",     # Top navbar background
    "sidebar_border": "#1e222a", # 1px divider
    "card_bg": "#15181e",        # Card surface
    "card_border": "#222630",    # 1px card outline
    "input_bg": "#191c23",       # Entry / Combobox / Secondary button fill
    "input_border": "#2c313d",   # Entry / Secondary button border
    "input_hover": "#3d4455",    # Hover border
    "btn_sec_bg": "#1b1f27",     # Secondary button fill
    "btn_sec_hover": "#252a35",  # Secondary button hover fill
    "primary": "#1d63dc",        # Active nav pill & primary button blue
    "primary_hover": "#256ef0",  # Primary button hover
    "accent": "#2997ff",         # Checkbox / Slider cyan-blue accent
    "fg": "#f3f4f6",             # Primary white text
    "fg_secondary": "#d1d5db",   # Normal label text
    "fg_muted": "#8e95a5",       # Muted / inactive nav text
    "fg_disabled": "#525866",    # Disabled text
    "badge_bg": "#2a2f3a",       # Circular (?) badge fill
    "badge_fg": "#9ca3af",       # Circular (?) badge text
    "slider_track": "#787d87",   # Slider unfilled track
    "slider_thumb": "#252a34",   # Slider thumb center
    "scroll_thumb": "#393e4a",   # Scrollbar gray pill
    "scroll_hover": "#52596a",   # Scrollbar gray pill hover
    "log_bg": "#0b0d10",         # Terminal log background
    "log_fg": "#e5e7eb",         # Terminal log text
    "fail_bg": "#2a1218",        # Failed downloads box
    "fail_fg": "#fecdd3",        # Failed downloads text
    "warn_bg": "#2e1c08",        # Missing dependency warning banner
    "warn_border": "#d97706",
    "warn_fg": "#fde68a",
}

SONGPULSE_LIGHT = {
    "bg": "#f3f4f8",
    "sidebar_bg": "#e9ecf2",
    "sidebar_border": "#d5d9e2",
    "card_bg": "#ffffff",
    "card_border": "#dcdfe6",
    "input_bg": "#f8f9fb",
    "input_border": "#c8cdd8",
    "input_hover": "#9aa3b5",
    "btn_sec_bg": "#f1f3f7",
    "btn_sec_hover": "#e4e7ee",
    "primary": "#1d63dc",
    "primary_hover": "#1552bd",
    "accent": "#1d63dc",
    "fg": "#111827",
    "fg_secondary": "#1f2937",
    "fg_muted": "#6b7280",
    "fg_disabled": "#9ca3af",
    "badge_bg": "#e2e6ef",
    "badge_fg": "#4b5563",
    "slider_track": "#cbd5e1",
    "slider_thumb": "#ffffff",
    "scroll_thumb": "#c2c8d4",
    "scroll_hover": "#9aa3b5",
    "log_bg": "#f8fafc",
    "log_fg": "#0f172a",
    "fail_bg": "#fff1f2",
    "fail_fg": "#881337",
    "warn_bg": "#fffbeb",
    "warn_border": "#d97706",
    "warn_fg": "#92400e",
}


def get_palette(is_dark=True):
    return SONGPULSE_DARK if is_dark else SONGPULSE_LIGHT


# ============================================================================
# ANTI-ALIASED SDF VECTOR ICON & SHAPE RENDERER (Razor-Sharp at 1080p–4K)
# ============================================================================
_ICON_CACHE = {}


def _hex_to_rgb(h, fallback=(21, 24, 30)):
    if not h or not isinstance(h, str) or not h.startswith("#") or len(h) < 7:
        return fallback
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _dist_to_segment(px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _dist_to_rounded_box(px, py, cx, cy, hw, hh, r):
    qx = abs(px - cx) - (hw - r)
    qy = abs(py - cy) - (hh - r)
    return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - r


def _cov_from_sdf(d):
    """Converts signed distance d (negative inside) to smooth [0..1] anti-aliased alpha."""
    return max(0.0, min(1.0, 0.5 - d))


def get_aa_icon(kind, fg_hex, bg_hex, extra_hex="#ffffff", size=20):
    """
    Renders a sub-pixel anti-aliased vector icon as a cached tk.PhotoImage (PPM P6)
    so circles, diagonal lines, checkboxes, radios, and navbar icons have zero jagged edges.
    """
    key = (kind, fg_hex, bg_hex, extra_hex, size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    fg_r, fg_g, fg_b = _hex_to_rgb(fg_hex)
    bg_r, bg_g, bg_b = _hex_to_rgb(bg_hex)
    ex_r, ex_g, ex_b = _hex_to_rgb(extra_hex)

    cx = (size - 1) / 2.0
    cy = (size - 1) / 2.0
    buf = bytearray(size * size * 3)
    idx = 0

    for y in range(size):
        py = float(y)
        for x in range(size):
            px = float(x)
            r, g, b = float(bg_r), float(bg_g), float(bg_b)

            if kind == "settings":
                # SongPulse 2-bar horizontal tuning sliders with circular knobs + gap outline
                y1, y2 = cy - 3.8, cy + 3.8
                kx1, kx2 = cx - 2.2, cx + 2.2
                # Track lines
                d_track = min(
                    _dist_to_segment(px, py, cx - 6.5, y1, cx + 6.5, y1) - 0.95,
                    _dist_to_segment(px, py, cx - 6.5, y2, cx + 6.5, y2) - 0.95,
                )
                a_track = _cov_from_sdf(d_track)
                r = r * (1.0 - a_track) + fg_r * a_track
                g = g * (1.0 - a_track) + fg_g * a_track
                b = b * (1.0 - a_track) + fg_b * a_track

                # Gap ring around knobs
                d_gap = min(
                    math.hypot(px - kx1, py - y1) - 3.3,
                    math.hypot(px - kx2, py - y2) - 3.3,
                )
                a_gap = _cov_from_sdf(d_gap)
                r = r * (1.0 - a_gap) + bg_r * a_gap
                g = g * (1.0 - a_gap) + bg_g * a_gap
                b = b * (1.0 - a_gap) + bg_b * a_gap

                # Solid knobs
                d_knob = min(
                    math.hypot(px - kx1, py - y1) - 2.35,
                    math.hypot(px - kx2, py - y2) - 2.35,
                )
                a_knob = _cov_from_sdf(d_knob)
                r = r * (1.0 - a_knob) + fg_r * a_knob
                g = g * (1.0 - a_knob) + fg_g * a_knob
                b = b * (1.0 - a_knob) + fg_b * a_knob

            elif kind == "downloader":
                d = min(
                    _dist_to_segment(px, py, cx, cy - 6.0, cx, cy + 2.2) - 0.95,
                    _dist_to_segment(px, py, cx - 4.0, cy - 1.2, cx, cy + 2.8) - 0.95,
                    _dist_to_segment(px, py, cx + 4.0, cy - 1.2, cx, cy + 2.8) - 0.95,
                    _dist_to_segment(px, py, cx - 5.5, cy + 5.8, cx + 5.5, cy + 5.8) - 0.95,
                )
                a = _cov_from_sdf(d)
                r = r * (1.0 - a) + fg_r * a
                g = g * (1.0 - a) + fg_g * a
                b = b * (1.0 - a) + fg_b * a

            elif kind == "history":
                dist_c = math.hypot(px - cx, py - cy)
                d_ring = abs(dist_c - 6.4) - 0.85
                d_hands = min(
                    _dist_to_segment(px, py, cx, cy - 3.6, cx, cy) - 0.85,
                    _dist_to_segment(px, py, cx, cy, cx + 2.8, cy + 1.8) - 0.85,
                )
                a = _cov_from_sdf(min(d_ring, d_hands))
                r = r * (1.0 - a) + fg_r * a
                g = g * (1.0 - a) + fg_g * a
                b = b * (1.0 - a) + fg_b * a

            elif kind == "about":
                dist_c = math.hypot(px - cx, py - cy)
                d_ring = abs(dist_c - 6.4) - 0.85
                d_dot = math.hypot(px - cx, py - (cy - 3.2)) - 1.05
                d_stem = _dist_to_segment(px, py, cx, cy - 0.5, cx, cy + 3.6) - 0.85
                a = _cov_from_sdf(min(d_ring, d_dot, d_stem))
                r = r * (1.0 - a) + fg_r * a
                g = g * (1.0 - a) + fg_g * a
                b = b * (1.0 - a) + fg_b * a

            elif kind == "video":
                # Rounded video screen outline + play triangle
                d_box = abs(_dist_to_rounded_box(px, py, cx, cy, 6.6, 5.2, 2.0)) - 0.8
                d_tri = min(
                    _dist_to_segment(px, py, cx - 1.8, cy - 2.3, cx - 1.8, cy + 2.3) - 0.75,
                    _dist_to_segment(px, py, cx - 1.8, cy - 2.3, cx + 2.4, cy) - 0.75,
                    _dist_to_segment(px, py, cx - 1.8, cy + 2.3, cx + 2.4, cy) - 0.75,
                )
                a = _cov_from_sdf(min(d_box, d_tri))
                r = r * (1.0 - a) + fg_r * a
                g = g * (1.0 - a) + fg_g * a
                b = b * (1.0 - a) + fg_b * a

            elif kind == "music":
                # Beamed eighth notes (♫)
                d_heads = min(
                    math.hypot(px - (cx - 3.6), py - (cy + 3.5)) - 2.1,
                    math.hypot(px - (cx + 2.6), py - (cy + 2.5)) - 2.1,
                )
                d_stems = min(
                    _dist_to_segment(px, py, cx - 1.9, cy + 3.2, cx - 1.9, cy - 4.2) - 0.85,
                    _dist_to_segment(px, py, cx + 4.3, cy + 2.2, cx + 4.3, cy - 5.2) - 0.85,
                    _dist_to_segment(px, py, cx - 1.9, cy - 4.2, cx + 4.3, cy - 5.2) - 1.25,
                )
                a = _cov_from_sdf(min(d_heads, d_stems))
                r = r * (1.0 - a) + fg_r * a
                g = g * (1.0 - a) + fg_g * a
                b = b * (1.0 - a) + fg_b * a

            elif kind == "playlist":
                # Clean stacked tracklist lines + play/bullet dots
                y1, y2, y3 = cy - 4.0, cy, cy + 4.0
                d_lines = min(
                    _dist_to_segment(px, py, cx - 2.2, y1, cx + 5.8, y1) - 0.9,
                    _dist_to_segment(px, py, cx - 2.2, y2, cx + 5.8, y2) - 0.9,
                    _dist_to_segment(px, py, cx - 2.2, y3, cx + 5.8, y3) - 0.9,
                )
                d_dots = min(
                    math.hypot(px - (cx - 5.2), py - y1) - 1.15,
                    math.hypot(px - (cx - 5.2), py - y2) - 1.15,
                    math.hypot(px - (cx - 5.2), py - y3) - 1.15,
                )
                a = _cov_from_sdf(min(d_lines, d_dots))
                r = r * (1.0 - a) + fg_r * a
                g = g * (1.0 - a) + fg_g * a
                b = b * (1.0 - a) + fg_b * a

            elif kind == "help_circle":
                d_disc = math.hypot(px - cx, py - cy) - (size / 2.0 - 1.2)
                a = _cov_from_sdf(d_disc)
                r = r * (1.0 - a) + fg_r * a
                g = g * (1.0 - a) + fg_g * a
                b = b * (1.0 - a) + fg_b * a

            elif kind == "chk_on":
                d_box = _dist_to_rounded_box(px, py, cx, cy, 7.6, 7.6, 3.8)
                a_box = _cov_from_sdf(d_box)
                r = r * (1.0 - a_box) + fg_r * a_box
                g = g * (1.0 - a_box) + fg_g * a_box
                b = b * (1.0 - a_box) + fg_b * a_box
                # Crisp anti-aliased white checkmark
                d_chk = min(
                    _dist_to_segment(px, py, cx - 3.5, cy + 0.2, cx - 0.8, cy + 3.0) - 0.95,
                    _dist_to_segment(px, py, cx - 0.8, cy + 3.0, cx + 4.0, cy - 2.6) - 0.95,
                )
                a_chk = _cov_from_sdf(d_chk)
                r = r * (1.0 - a_chk) + 255.0 * a_chk
                g = g * (1.0 - a_chk) + 255.0 * a_chk
                b = b * (1.0 - a_chk) + 255.0 * a_chk

            elif kind == "chk_off":
                d_box = _dist_to_rounded_box(px, py, cx, cy, 7.6, 7.6, 3.8)
                a_fill = _cov_from_sdf(d_box)
                r = r * (1.0 - a_fill) + ex_r * a_fill
                g = g * (1.0 - a_fill) + ex_g * a_fill
                b = b * (1.0 - a_fill) + ex_b * a_fill
                d_border = abs(d_box + 0.5) - 0.65
                a_bdr = _cov_from_sdf(d_border)
                r = r * (1.0 - a_bdr) + fg_r * a_bdr
                g = g * (1.0 - a_bdr) + fg_g * a_bdr
                b = b * (1.0 - a_bdr) + fg_b * a_bdr

            elif kind == "radio_on":
                dist_c = math.hypot(px - cx, py - cy)
                a_outer = _cov_from_sdf(dist_c - 7.2)
                r = r * (1.0 - a_outer) + fg_r * a_outer
                g = g * (1.0 - a_outer) + fg_g * a_outer
                b = b * (1.0 - a_outer) + fg_b * a_outer
                a_dot = _cov_from_sdf(dist_c - 3.1)
                r = r * (1.0 - a_dot) + 255.0 * a_dot
                g = g * (1.0 - a_dot) + 255.0 * a_dot
                b = b * (1.0 - a_dot) + 255.0 * a_dot

            elif kind == "radio_off":
                dist_c = math.hypot(px - cx, py - cy)
                a_fill = _cov_from_sdf(dist_c - 7.2)
                r = r * (1.0 - a_fill) + ex_r * a_fill
                g = g * (1.0 - a_fill) + ex_g * a_fill
                b = b * (1.0 - a_fill) + ex_b * a_fill
                a_ring = _cov_from_sdf(abs(dist_c - 6.7) - 0.68)
                r = r * (1.0 - a_ring) + fg_r * a_ring
                g = g * (1.0 - a_ring) + fg_g * a_ring
                b = b * (1.0 - a_ring) + fg_b * a_ring

            elif kind == "chevron_down":
                # Crisp SongPulse downward chevron 'v' for dropdowns
                d = min(
                    _dist_to_segment(px, py, cx - 3.8, cy - 1.6, cx, cy + 2.2) - 0.85,
                    _dist_to_segment(px, py, cx, cy + 2.2, cx + 3.8, cy - 1.6) - 0.85,
                )
                a = _cov_from_sdf(d)
                r = r * (1.0 - a) + fg_r * a
                g = g * (1.0 - a) + fg_g * a
                b = b * (1.0 - a) + fg_b * a

            elif kind == "chevron_up":
                d = min(
                    _dist_to_segment(px, py, cx - 3.8, cy + 1.8, cx, cy - 2.0) - 0.85,
                    _dist_to_segment(px, py, cx, cy - 2.0, cx + 3.8, cy + 1.8) - 0.85,
                )
                a = _cov_from_sdf(d)
                r = r * (1.0 - a) + fg_r * a
                g = g * (1.0 - a) + fg_g * a
                b = b * (1.0 - a) + fg_b * a

            buf[idx] = int(round(max(0.0, min(255.0, r))))
            buf[idx + 1] = int(round(max(0.0, min(255.0, g))))
            buf[idx + 2] = int(round(max(0.0, min(255.0, b))))
            idx += 3

    ppm = f"P6\n{size} {size}\n255\n".encode("ascii") + bytes(buf)
    img = tk.PhotoImage(data=ppm)
    _ICON_CACHE[key] = img
    return img


_ROUNDED_RECT_CACHE = {}


def _draw_rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    """Draws a sub-pixel anti-aliased rounded rectangle on a tk.Canvas using an SDF PhotoImage."""
    pw = int(round(x2 - x1)) + 1
    ph = int(round(y2 - y1)) + 1
    if pw <= 2 or ph <= 2:
        return canvas.create_rectangle(x1, y1, x2, y2, **kwargs)

    r = max(0.0, min(float(r), (pw - 1) / 2.0, (ph - 1) / 2.0))
    if r <= 1.0:
        return canvas.create_rectangle(x1, y1, x2, y2, **kwargs)

    fill_hex = kwargs.get("fill") or "#1b1f27"
    outline_hex = kwargs.get("outline") or fill_hex
    stroke_w = float(kwargs.get("width", 1))
    try:
        bg_hex = canvas.cget("background")
    except Exception:
        bg_hex = "#15181e"
    if not isinstance(bg_hex, str) or not bg_hex.startswith("#") or len(bg_hex) < 7:
        bg_hex = "#15181e"

    key = (pw, ph, round(r, 2), fill_hex, outline_hex, bg_hex, round(stroke_w, 2))
    img = _ROUNDED_RECT_CACHE.get(key)
    if img is None:
        if len(_ROUNDED_RECT_CACHE) >= 512:
            _ROUNDED_RECT_CACHE.clear()

        bg_r, bg_g, bg_b = _hex_to_rgb(bg_hex)
        fl_r, fl_g, fl_b = _hex_to_rgb(fill_hex)
        has_border = outline_hex != fill_hex and stroke_w > 0.0
        ol_r, ol_g, ol_b = _hex_to_rgb(outline_hex) if has_border else (fl_r, fl_g, fl_b)

        cx = (pw - 1) / 2.0
        cy = (ph - 1) / 2.0
        hw = cx
        hh = cy

        def _eval_pixel(px, py):
            d_out = _dist_to_rounded_box(px, py, cx, cy, hw, hh, r)
            a_out = _cov_from_sdf(d_out)
            if a_out <= 0.0:
                return bg_r, bg_g, bg_b
            if has_border:
                a_in = _cov_from_sdf(d_out + stroke_w)
                pr = ol_r * (1.0 - a_in) + fl_r * a_in
                pg = ol_g * (1.0 - a_in) + fl_g * a_in
                pb = ol_b * (1.0 - a_in) + fl_b * a_in
            else:
                pr, pg, pb = fl_r, fl_g, fl_b
            return (
                int(bg_r * (1.0 - a_out) + pr * a_out + 0.5),
                int(bg_g * (1.0 - a_out) + pg * a_out + 0.5),
                int(bg_b * (1.0 - a_out) + pb * a_out + 0.5),
            )

        cb = min(pw // 2, ph // 2, int(math.ceil(r + stroke_w + 2)))
        buf = bytearray(pw * ph * 3)
        row_bytes = pw * 3

        # Precompute flat interior row (used for middle rows where y is away from corners)
        mid_row = bytearray(row_bytes)
        if ph > 2 * cb:
            for x in range(pw):
                if cb <= x < pw - cb:
                    # Pure fill interior
                    mid_row[x * 3] = fl_r
                    mid_row[x * 3 + 1] = fl_g
                    mid_row[x * 3 + 2] = fl_b
                else:
                    rr, gg, bb = _eval_pixel(float(x), cy)
                    mid_row[x * 3] = rr
                    mid_row[x * 3 + 1] = gg
                    mid_row[x * 3 + 2] = bb

        for y in range(ph):
            row_off = y * row_bytes
            if cb <= y < ph - cb:
                buf[row_off : row_off + row_bytes] = mid_row
            else:
                py = float(y)
                # Left corner band
                for x in range(cb):
                    rr, gg, bb = _eval_pixel(float(x), py)
                    idx = row_off + x * 3
                    buf[idx] = rr
                    buf[idx + 1] = gg
                    buf[idx + 2] = bb
                # Middle horizontal strip (constant x-independent distance)
                if pw > 2 * cb:
                    mr, mg, mb = _eval_pixel(cx, py)
                    strip = bytes((mr, mg, mb)) * (pw - 2 * cb)
                    buf[row_off + cb * 3 : row_off + (pw - cb) * 3] = strip
                # Right corner band
                for x in range(max(cb, pw - cb), pw):
                    rr, gg, bb = _eval_pixel(float(x), py)
                    idx = row_off + x * 3
                    buf[idx] = rr
                    buf[idx + 1] = gg
                    buf[idx + 2] = bb

        header = f"P6\n{pw} {ph}\n255\n".encode("ascii")
        img = tk.PhotoImage(data=header + bytes(buf), format="PPM")
        _ROUNDED_RECT_CACHE[key] = img

    imgs = getattr(canvas, "_rr_imgs", None)
    if imgs is None:
        imgs = []
        canvas._rr_imgs = imgs
    imgs.append(img)
    if len(imgs) > 32:
        del imgs[:-16]

    return canvas.create_image(int(round(x1)), int(round(y1)), image=img, anchor="nw")


# ============================================================================
# MODERN GRAY PILL SCROLLBAR (Zero Arrow Buttons, Smooth Pill Thumb)
# ============================================================================
class ModernScrollbar(tk.Canvas):
    """
    A sleek SongPulse-style scrollbar with a rounded gray pill thumb and no arrow buttons.
    Drop-in replacement for ttk.Scrollbar supporting vertical and horizontal orientation.
    """

    def __init__(self, master, orient="vertical", command=None, app_ref=None, thickness=10, **kwargs):
        w = thickness if orient == "vertical" else 40
        h = 40 if orient == "vertical" else thickness
        super().__init__(master, width=w, height=h, highlightthickness=0, bd=0, **kwargs)
        self.orient = orient
        self.command = command
        self.app_ref = app_ref
        self.thickness = thickness

        self._first = 0.0
        self._last = 1.0
        self._hover = False
        self._dragging = False
        self._drag_start_coord = 0
        self._drag_start_first = 0.0

        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    def config(self, **kwargs):
        self.configure(**kwargs)

    def configure(self, **kwargs):
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        if kwargs:
            super().configure(**kwargs)

    def set(self, first, last):
        try:
            f = max(0.0, min(1.0, float(first)))
            l = max(0.0, min(1.0, float(last)))
        except (ValueError, TypeError):
            return
        if abs(f - self._first) < 0.0005 and abs(l - self._last) < 0.0005:
            return
        self._first = f
        self._last = l
        self.redraw()

    def _on_enter(self, event=None):
        self._hover = True
        self.redraw()

    def _on_leave(self, event=None):
        if not self._dragging:
            self._hover = False
            self.redraw()

    def _get_track_and_thumb(self):
        total = max(
            1,
            self.winfo_height() if self.orient == "vertical" else self.winfo_width(),
        )
        pad = 3
        usable = max(1, total - pad * 2)
        span = max(0.04, self._last - self._first)
        thumb_len = max(24, int(usable * span))
        if span >= 0.999:
            return total, pad, usable, 0, total
        max_offset = usable - thumb_len
        ratio = self._first / max(0.0001, 1.0 - span)
        t0 = pad + int(max(0.0, min(1.0, ratio)) * max_offset)
        t1 = t0 + thumb_len
        return total, pad, usable, t0, t1

    def _on_press(self, event):
        if self._last - self._first >= 0.999:
            return
        coord = event.y if self.orient == "vertical" else event.x
        _, _, _, t0, t1 = self._get_track_and_thumb()
        if t0 <= coord <= t1:
            self._dragging = True
            self._drag_start_coord = coord
            self._drag_start_first = self._first
            self.redraw()
        elif self.command:
            # Page jump when clicking above/below pill
            direction = -1 if coord < t0 else 1
            self.command("scroll", direction, "pages")

    def _on_drag(self, event):
        if not self._dragging or not self.command:
            return
        coord = event.y if self.orient == "vertical" else event.x
        _, _, usable, t0, t1 = self._get_track_and_thumb()
        thumb_len = t1 - t0
        scrollable_px = max(1, usable - thumb_len)
        delta_px = coord - self._drag_start_coord
        span = self._last - self._first
        new_first = self._drag_start_first + (delta_px / scrollable_px) * (1.0 - span)
        new_first = max(0.0, min(1.0 - span, new_first))
        self.command("moveto", new_first)

    def _on_release(self, event):
        self._dragging = False
        self.redraw()

    def redraw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        is_dark = self.app_ref.get_target_dark_state() if self.app_ref else True
        pal = get_palette(is_dark)
        try:
            track_bg = self.master.cget("background")
            if not track_bg:
                raise tk.TclError()
        except Exception:
            track_bg = pal["bg"]
        super().configure(bg=track_bg)

        # Hide thumb completely when all content fits without scrolling
        if self._last - self._first >= 0.999:
            return

        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 2 or h <= 2:
            return

        _, _, _, t0, t1 = self._get_track_and_thumb()
        thumb_color = pal["scroll_hover"] if (self._hover or self._dragging) else pal["scroll_thumb"]

        if self.orient == "vertical":
            cx = w / 2.0
            half_t = 3.0 if (self._hover or self._dragging) else 2.5
            self.create_line(
                cx,
                t0 + half_t,
                cx,
                max(t0 + half_t + 1, t1 - half_t),
                fill=thumb_color,
                width=half_t * 2,
                capstyle="round",
            )
        else:
            cy = h / 2.0
            half_t = 3.0 if (self._hover or self._dragging) else 2.5
            self.create_line(
                t0 + half_t,
                cy,
                max(t0 + half_t + 1, t1 - half_t),
                cy,
                fill=thumb_color,
                width=half_t * 2,
                capstyle="round",
            )


# ============================================================================
# FAST NATIVE SONGPULSE CARD CONTAINER (Zero Nested-Canvas Resize Lag!)
# ============================================================================
class RoundedCard(tk.Frame):
    """
    A fast native tk.Frame card with a 1px SongPulse border, bold internal section header,
    and an inner self.body Frame for child widgets.
    Eliminates nested tk.Canvas create_window viewports so window resizing is 100% lag-free.
    """

    def __init__(self, master, title="", app_ref=None, pad_x=16, pad_y=12, **kwargs):
        super().__init__(
            master,
            highlightthickness=1,
            bd=0,
            padx=pad_x,
            pady=pad_y,
            **kwargs,
        )
        self.title_text = title
        self.app_ref = app_ref

        if title:
            self.title_lbl = tk.Label(
                self,
                text=title,
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            )
            self.title_lbl.pack(fill="x", pady=(0, 8))
        else:
            self.title_lbl = None

        self.body = tk.Frame(self, bd=0, highlightthickness=0)
        self.body.pack(fill="both", expand=True)
        self.update_theme()

    def update_theme(self):
        is_dark = self.app_ref.get_target_dark_state() if self.app_ref else True
        pal = get_palette(is_dark)
        self.configure(
            bg=pal["card_bg"],
            highlightbackground=pal["card_border"],
            highlightcolor=pal["card_border"],
        )
        self.body.configure(bg=pal["card_bg"])
        if self.title_lbl:
            self.title_lbl.configure(bg=pal["card_bg"], fg=pal["fg"])


class RoundedButton(tk.Canvas):
    """
    A SongPulse-style rounded button supporting 'primary', 'secondary', 'danger', 'warning', and 'pill' variants.
    Only redraws when its dimensions or visual state actually change.
    """

    def __init__(
        self,
        master,
        text="",
        command=None,
        app_ref=None,
        variant="secondary",
        icon_kind=None,
        tooltip=None,
        width=None,
        height=31,
        radius=11,
        font=("Segoe UI", 9),
        padx=14,
        **kwargs,
    ):
        super().__init__(master, height=height, highlightthickness=0, bd=0, cursor="hand2", **kwargs)
        self.text = text
        self.command = command
        self.app_ref = app_ref
        self.variant = variant
        self.icon_kind = icon_kind
        self.tooltip = tooltip
        self.tip_win = None
        self.radius = radius
        self.font = font
        self.padx = padx
        self._fixed_width = width
        self._state = "normal"
        self._hover = False
        self._selected = False
        self._custom_bg = None
        self._custom_active_bg = None
        self._last_drawn_size = (0, 0)
        self._icon_img = None

        self._measure_and_resize()
        self.bind("<Configure>", self._on_configure)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_click)

    def _on_configure(self, event):
        sz = (event.width, event.height)
        if sz != self._last_drawn_size:
            self._last_drawn_size = sz
            self.redraw()

    def _measure_and_resize(self):
        if self._fixed_width:
            px_w = self._fixed_width * 8 + 18 if self._fixed_width < 40 else self._fixed_width
            super().configure(width=px_w)
        else:
            temp = tk.Label(self, text=self.text, font=self.font)
            icon_extra = 22 if self.icon_kind else 0
            req_w = temp.winfo_reqwidth() + self.padx * 2 + icon_extra
            temp.destroy()
            super().configure(width=max(48, req_w))

    def config(self, **kwargs):
        self.configure(**kwargs)

    def configure(self, **kwargs):
        need_redraw = False
        if "text" in kwargs:
            self.text = kwargs.pop("text")
            self._measure_and_resize()
            need_redraw = True
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            super().configure(cursor="hand2" if self._state == "normal" else "")
            need_redraw = True
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        if "variant" in kwargs:
            self.variant = kwargs.pop("variant")
            need_redraw = True
        if "selected" in kwargs:
            self._selected = bool(kwargs.pop("selected"))
            need_redraw = True
        if "bg" in kwargs:
            self._custom_bg = kwargs.pop("bg")
            need_redraw = True
        if "activebackground" in kwargs:
            self._custom_active_bg = kwargs.pop("activebackground")
            need_redraw = True
        if "fg" in kwargs:
            kwargs.pop("fg")
            need_redraw = True
        if kwargs:
            super().configure(**kwargs)
        if need_redraw:
            self.redraw()

    def _on_enter(self, event=None):
        if self._state == "normal" and not self._hover:
            self._hover = True
            self.redraw()
        if self.tooltip:
            self._show_tooltip()

    def _on_leave(self, event=None):
        if self._hover:
            self._hover = False
            self.redraw()
        self._hide_tooltip()

    def _show_tooltip(self):
        if self.tip_win or not self.tooltip:
            return
        is_dark = self.app_ref.get_target_dark_state() if self.app_ref else True
        pal = get_palette(is_dark)

        x = self.winfo_rootx() + 10
        y = self.winfo_rooty() + self.winfo_height() + 6

        self.tip_win = tw = tk.Toplevel(self)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)

        frame = tk.Frame(
            tw,
            bg=pal["card_bg"],
            highlightbackground=pal["input_border"],
            highlightthickness=1,
            padx=10,
            pady=7,
        )
        frame.pack()

        tk.Label(
            frame,
            text=self.tooltip,
            justify="left",
            bg=pal["card_bg"],
            fg=pal["fg"],
            font=("Segoe UI", 8),
            wraplength=280,
        ).pack()

    def _hide_tooltip(self):
        if self.tip_win:
            try:
                self.tip_win.destroy()
            except Exception:
                pass
            self.tip_win = None

    def _on_click(self, event=None):
        self._hide_tooltip()
        if self._state != "normal":
            return
        if 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            if self.command:
                self.command()

    def redraw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        is_dark = self.app_ref.get_target_dark_state() if self.app_ref else True
        pal = get_palette(is_dark)

        try:
            parent_bg = self.master.cget("background")
        except Exception:
            parent_bg = pal["card_bg"]
        super().configure(bg=parent_bg)

        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 4 or h <= 4:
            return

        disabled = self._state != "normal"

        if self._custom_bg and self.variant == "primary":
            fill = (
                self._custom_active_bg
                if (self._hover and self._custom_active_bg)
                else self._custom_bg
            )
            outline = fill
            fg = "#ffffff"
        elif self.variant == "primary" or (self.variant == "pill" and self._selected):
            fill = pal["primary_hover"] if (self._hover and not disabled) else pal["primary"]
            if disabled:
                fill = pal["btn_sec_bg"]
            outline = fill
            fg = pal["fg_disabled"] if disabled else "#ffffff"
        elif self.variant == "danger":
            fill = "#ef4444" if (self._hover and not disabled) else "#dc2626"
            outline = fill
            fg = "#ffffff"
        elif self.variant == "warning":
            fill = "#f59e0b" if (self._hover and not disabled) else "#d97706"
            outline = fill
            fg = "#ffffff"
        else:
            fill = pal["btn_sec_hover"] if (self._hover and not disabled) else pal["btn_sec_bg"]
            outline = pal["input_hover"] if (self._hover and not disabled) else pal["input_border"]
            fg = pal["fg_disabled"] if disabled else pal["fg"]

        _draw_rounded_rect(
            self, 1, 1, w - 2, h - 2, self.radius, fill=fill, outline=outline, width=1
        )
        if self.icon_kind:
            self._icon_img = get_aa_icon(self.icon_kind, fg, fill, size=18)
            self.create_image(self.padx + 7, int(h / 2), image=self._icon_img)
            self.create_text(
                self.padx + 22,
                h / 2,
                text=self.text,
                fill=fg,
                font=self.font,
                anchor="w",
            )
        else:
            self.create_text(
                w / 2,
                h / 2,
                text=self.text,
                fill=fg,
                font=self.font,
            )


class TopNavButton(tk.Canvas):
    """
    SongPulse-style top navbar pill button with sub-pixel anti-aliased SDF icons
    (including SongPulse's exact 2-slider-bars icon for Settings).
    """

    def __init__(self, master, icon_kind, label, command, app_ref, height=36, **kwargs):
        super().__init__(
            master, height=height, width=136, highlightthickness=0, bd=0, cursor="hand2", **kwargs
        )
        self.icon_kind = icon_kind
        self.label = label
        self.command = command
        self.app_ref = app_ref
        self.active = False
        self._hover = False
        self._icon_img = None

        tmp = tk.Label(self, text=label, font=("Segoe UI", 10, "bold"))
        req_w = tmp.winfo_reqwidth() + 50
        tmp.destroy()
        self.configure(width=max(118, req_w))

        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_click)

    def set_active(self, is_active):
        self.active = bool(is_active)
        self.redraw()

    def _on_enter(self, event=None):
        if not self._hover:
            self._hover = True
            self.redraw()

    def _on_leave(self, event=None):
        if self._hover:
            self._hover = False
            self.redraw()

    def _on_click(self, event=None):
        if self.command:
            self.command()

    def redraw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        is_dark = self.app_ref.get_target_dark_state() if self.app_ref else True
        pal = get_palette(is_dark)
        super().configure(bg=pal["sidebar_bg"])

        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 4 or h <= 4:
            return

        if self.active:
            fill = pal["primary"]
            fg = "#ffffff"
            font = ("Segoe UI", 10, "bold")
            _draw_rounded_rect(self, 2, 2, w - 3, h - 3, 11, fill=fill, outline=fill, width=1)
            icon_bg = fill
        elif self._hover:
            fill = pal["btn_sec_bg"]
            fg = pal["fg"]
            font = ("Segoe UI", 10)
            _draw_rounded_rect(self, 2, 2, w - 3, h - 3, 11, fill=fill, outline=fill, width=1)
            icon_bg = fill
        else:
            fg = pal["fg_muted"]
            font = ("Segoe UI", 10)
            icon_bg = pal["sidebar_bg"]

        self._icon_img = get_aa_icon(self.icon_kind, fg, icon_bg, size=20)
        self.create_image(22, int(h / 2), image=self._icon_img)
        self.create_text(38, h / 2, text=self.label, fill=fg, font=font, anchor="w")


class SongPulseDropdown(tk.Canvas):
    """
    SongPulse-style custom rounded dropdown with floating dark popup menu,
    rounded item highlight pill, bright cyan-blue left accent bar on the active item,
    and optional per-item hover explanation tooltips.
    Drop-in replacement for ttk.Combobox.
    """

    def __init__(
        self,
        master,
        textvariable=None,
        values=None,
        item_descriptions=None,
        state="readonly",
        width=20,
        height=32,
        radius=10,
        command=None,
        app_ref=None,
        **kwargs,
    ):
        px_w = width * 7 + 34 if width < 60 else width
        super().__init__(
            master,
            width=px_w,
            height=height,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            **kwargs,
        )
        self.textvariable = textvariable
        self.values = list(values or [])
        self.item_descriptions = dict(item_descriptions or {})
        self._state = state
        self._char_width = width
        self.radius = radius
        self.command = command
        self.app_ref = app_ref
        self._hover = False
        self._popup = None
        self._tip_win = None
        self._chev_img = None
        self._last_size = (0, 0)

        if self.textvariable is not None:
            self.textvariable.trace_add("write", lambda *args: self.redraw())

        self.bind("<Configure>", self._on_configure)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._toggle_popup)

    def _on_configure(self, event):
        sz = (event.width, event.height)
        if sz != self._last_size:
            self._last_size = sz
            self.redraw()

    def get(self):
        return self.textvariable.get() if self.textvariable is not None else ""

    def set(self, val):
        if self.textvariable is not None:
            self.textvariable.set(val)
        self.redraw()

    def config(self, **kwargs):
        self.configure(**kwargs)

    def configure(self, **kwargs):
        need_redraw = False
        if "values" in kwargs:
            self.values = list(kwargs.pop("values") or [])
            need_redraw = True
        if "item_descriptions" in kwargs:
            self.item_descriptions = dict(kwargs.pop("item_descriptions") or {})
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            super().configure(cursor="hand2" if self._state != "disabled" else "")
            if self._state == "disabled":
                self._close_popup()
            need_redraw = True
        if "textvariable" in kwargs:
            self.textvariable = kwargs.pop("textvariable")
            if self.textvariable is not None:
                self.textvariable.trace_add("write", lambda *args: self.redraw())
            need_redraw = True
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        if kwargs:
            super().configure(**kwargs)
        if need_redraw:
            self.redraw()

    def _on_enter(self, event=None):
        if self._state != "disabled" and not self._hover:
            self._hover = True
            self.redraw()
        if self.item_descriptions and not (self._popup and self._popup.winfo_exists()):
            cur_desc = self.item_descriptions.get(str(self.get()))
            if cur_desc:
                self._show_item_tip(
                    cur_desc,
                    self.winfo_rootx() + 12,
                    self.winfo_rooty() + self.winfo_height() + 6,
                )

    def _on_leave(self, event=None):
        if self._hover:
            self._hover = False
            self.redraw()
        if not (self._popup and self._popup.winfo_exists()):
            self._hide_item_tip()

    def _show_item_tip(self, text, x, y):
        self._hide_item_tip()
        if not text:
            return
        is_dark = self.app_ref.get_target_dark_state() if self.app_ref else True
        pal = get_palette(is_dark)

        screen_w = self.winfo_screenwidth()
        if x + 340 > screen_w - 20:
            x = max(10, self.winfo_rootx() - 335)

        self._tip_win = tw = tk.Toplevel(self)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{int(x)}+{int(y)}")
        tw.attributes("-topmost", True)

        frame = tk.Frame(
            tw,
            bg=pal["card_bg"],
            highlightbackground=pal["input_border"],
            highlightthickness=1,
            padx=12,
            pady=9,
        )
        frame.pack()

        tk.Label(
            frame,
            text=text,
            justify="left",
            bg=pal["card_bg"],
            fg=pal["fg"],
            font=("Segoe UI", 9),
            wraplength=310,
        ).pack()

    def _hide_item_tip(self):
        if self._tip_win:
            try:
                self._tip_win.destroy()
            except Exception:
                pass
            self._tip_win = None

    def _toggle_popup(self, event=None):
        if self._state == "disabled":
            return
        self._hide_item_tip()
        if self._popup and self._popup.winfo_exists():
            self._close_popup()
        else:
            self._open_popup()

    def _close_popup(self, event=None):
        self._hide_item_tip()
        if self._popup and self._popup.winfo_exists():
            try:
                self._popup.destroy()
            except Exception:
                pass
        self._popup = None
        if self.winfo_exists():
            self.redraw()

    def _open_popup(self):
        if not self.values:
            return
        self._close_popup()
        is_dark = self.app_ref.get_target_dark_state() if self.app_ref else True
        pal = get_palette(is_dark)

        row_h = 34
        pad_outer = 6
        max_vis = min(8, len(self.values))
        pop_h = max_vis * row_h + pad_outer * 2

        # Ensure popup is wide enough for longest item or matches widget width
        tmp = tk.Label(self, font=("Segoe UI", 9))
        max_text_w = 0
        for v in self.values:
            tmp.configure(text=str(v))
            max_text_w = max(max_text_w, tmp.winfo_reqwidth())
        tmp.destroy()
        pop_w = max(self.winfo_width(), max_text_w + 36)

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 3
        screen_h = self.winfo_screenheight()
        if y + pop_h > screen_h - 40:
            y = max(10, self.winfo_rooty() - pop_h - 3)

        pop = tk.Toplevel(self)
        pop.wm_overrideredirect(True)
        pop.wm_geometry(f"{pop_w}x{pop_h}+{x}+{y}")
        pop.attributes("-topmost", True)
        self._popup = pop
        self.redraw()

        menu_bg = "#141820" if is_dark else "#ffffff"
        menu_bdr = "#283040" if is_dark else "#cbd5e1"
        hover_pill = "#202634" if is_dark else "#eef2f9"
        accent_bar = pal["accent"]

        outer = tk.Frame(
            pop,
            bg=menu_bg,
            highlightbackground=menu_bdr,
            highlightthickness=1,
            padx=pad_outer - 1,
            pady=pad_outer - 1,
        )
        outer.pack(fill="both", expand=True)

        cv = tk.Canvas(outer, bg=menu_bg, highlightthickness=0, bd=0, cursor="hand2")
        if len(self.values) > max_vis:
            sb = ModernScrollbar(
                outer, orient="vertical", command=cv.yview, app_ref=self.app_ref, thickness=8
            )
            sb.pack(side="right", fill="y", padx=(2, 0))
            cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)

        total_h = len(self.values) * row_h
        cv.configure(scrollregion=(0, 0, pop_w - 16, total_h))

        cur_val = self.get()
        state = {"hover_idx": -1}

        def draw_items():
            cv.delete("all")
            cw = max(pop_w - (22 if len(self.values) > max_vis else 12), cv.winfo_width())
            for idx, val in enumerate(self.values):
                y0 = idx * row_h
                y1 = y0 + row_h
                is_sel = str(val) == str(cur_val)
                is_hov = idx == state["hover_idx"]

                if is_sel or is_hov:
                    _draw_rounded_rect(
                        cv,
                        2,
                        y0 + 2,
                        cw - 2,
                        y1 - 2,
                        7,
                        fill=hover_pill,
                        outline=hover_pill,
                        width=1,
                    )
                if is_sel:
                    # SongPulse signature cyan-blue left vertical accent bar
                    cv.create_line(
                        5,
                        y0 + 8,
                        5,
                        y1 - 8,
                        fill=accent_bar,
                        width=3,
                        capstyle="round",
                    )

                txt_fg = pal["fg"] if (is_sel or is_hov) else pal["fg_secondary"]
                cv.create_text(
                    15,
                    (y0 + y1) / 2,
                    text=str(val),
                    fill=txt_fg,
                    font=("Segoe UI", 9, "bold" if is_sel else "normal"),
                    anchor="w",
                )

        def on_motion(e):
            cy = cv.canvasy(e.y)
            idx = int(cy // row_h)
            if 0 <= idx < len(self.values):
                if state["hover_idx"] != idx:
                    state["hover_idx"] = idx
                    draw_items()
                    if self.item_descriptions:
                        val_str = str(self.values[idx])
                        desc = self.item_descriptions.get(val_str)
                        if desc:
                            tip_x = pop.winfo_rootx() + pop_w + 8
                            tip_y = pop.winfo_rooty() + max(0, int(idx * row_h - cv.canvasy(0)))
                            self._show_item_tip(desc, tip_x, tip_y)
                        else:
                            self._hide_item_tip()

        def on_leave_cv(e):
            self._hide_item_tip()

        def on_click(e):
            cy = cv.canvasy(e.y)
            idx = int(cy // row_h)
            if 0 <= idx < len(self.values):
                chosen = self.values[idx]
                self.set(chosen)
                self._close_popup()
                if self.command:
                    self.command(chosen)
                self.event_generate("<<ComboboxSelected>>")

        def on_wheel(e):
            if len(self.values) > max_vis:
                cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
            return "break"

        cv.bind("<Configure>", lambda e: draw_items())
        cv.bind("<Motion>", on_motion)
        cv.bind("<Leave>", on_leave_cv)
        cv.bind("<ButtonRelease-1>", on_click)
        cv.bind("<MouseWheel>", on_wheel)
        pop.bind("<Escape>", self._close_popup)
        pop.bind("<FocusOut>", lambda e: self.after(80, self._check_popup_focus))
        pop.focus_force()

    def _check_popup_focus(self):
        if not self._popup or not self._popup.winfo_exists():
            return
        focused = self.focus_get()
        if focused is None or (focused is not self._popup and not str(focused).startswith(str(self._popup))):
            self._close_popup()

    def redraw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        is_dark = self.app_ref.get_target_dark_state() if self.app_ref else True
        pal = get_palette(is_dark)

        try:
            parent_bg = self.master.cget("background")
            if not parent_bg or not str(parent_bg).startswith("#"):
                raise tk.TclError()
        except Exception:
            parent_bg = pal["card_bg"]
        super().configure(bg=parent_bg)

        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 4 or h <= 4:
            return

        disabled = self._state == "disabled"
        is_open = bool(self._popup and self._popup.winfo_exists())

        fill = pal["card_bg"] if disabled else pal["input_bg"]
        if is_open or (self._hover and not disabled):
            outline = "#1f6f8b" if is_dark else pal["accent"]
        else:
            outline = pal["input_border"]

        _draw_rounded_rect(
            self, 1, 1, w - 2, h - 2, self.radius, fill=fill, outline=outline, width=1
        )

        fg = pal["fg_disabled"] if disabled else pal["fg"]
        chev_fg = pal["fg_disabled"] if disabled else pal["fg_muted"]
        chev_kind = "chevron_up" if is_open else "chevron_down"
        self._chev_img = get_aa_icon(chev_kind, chev_fg, fill, size=16)
        self.create_image(w - 15, int(h / 2), image=self._chev_img)

        # Clip text cleanly so it never overlaps the right chevron
        val_txt = str(self.get() or "")
        max_chars = max(6, int((w - 36) / 6.8))
        if len(val_txt) > max_chars:
            val_txt = val_txt[: max_chars - 1] + "…"

        self.create_text(
            12,
            h / 2,
            text=val_txt,
            fill=fg,
            font=("Segoe UI", 9),
            anchor="w",
        )


class SongPulseCheckbox(tk.Frame):
    """
    A SongPulse-style rounded-square cyan-blue checkbox rendered with anti-aliased SDF PhotoImage.
    """

    def __init__(self, master, text="", variable=None, command=None, app_ref=None, **kwargs):
        super().__init__(master, cursor="hand2", **kwargs)
        self.text = text
        self.variable = variable
        self.command = command
        self.app_ref = app_ref
        self._state = "normal"
        self._hover = False
        self._img = None

        self.box = tk.Label(self, bd=0, highlightthickness=0)
        self.box.pack(side="left", padx=(0, 6))

        self.lbl = tk.Label(self, text=text, font=("Segoe UI", 9), anchor="w")
        self.lbl.pack(side="left")

        for widget in (self, self.box, self.lbl):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<ButtonRelease-1>", self._on_click)

        if self.variable is not None:
            self.variable.trace_add("write", lambda *args: self.redraw())

        self.redraw()

    def config(self, **kwargs):
        self.configure(**kwargs)

    def configure(self, **kwargs):
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            cur = "hand2" if self._state == "normal" else ""
            super().configure(cursor=cur)
            self.box.configure(cursor=cur)
            self.lbl.configure(cursor=cur)
            self.redraw()
        if "text" in kwargs:
            self.text = kwargs.pop("text")
            self.lbl.configure(text=self.text)
        if kwargs:
            super().configure(**kwargs)

    def _on_enter(self, event=None):
        if self._state == "normal" and not self._hover:
            self._hover = True
            self.redraw()

    def _on_leave(self, event=None):
        if self._hover:
            self._hover = False
            self.redraw()

    def _on_click(self, event=None):
        if self._state != "normal":
            return
        if self.variable is not None:
            self.variable.set(not bool(self.variable.get()))
        self.redraw()
        if self.command:
            self.command()

    def redraw(self):
        if not self.winfo_exists():
            return
        is_dark = self.app_ref.get_target_dark_state() if self.app_ref else True
        pal = get_palette(is_dark)
        try:
            bg = self.master.cget("background")
            if not bg or not str(bg).startswith("#"):
                raise tk.TclError()
        except Exception:
            bg = pal["card_bg"]

        super().configure(bg=bg)
        disabled = self._state != "normal"
        self.lbl.configure(bg=bg, fg=pal["fg_disabled"] if disabled else pal["fg_secondary"])

        checked = bool(self.variable.get()) if self.variable is not None else False
        if checked:
            fill = pal["fg_disabled"] if disabled else pal["accent"]
            self._img = get_aa_icon("chk_on", fill, bg, size=20)
        else:
            outline = pal["accent"] if (self._hover and not disabled) else pal["input_border"]
            self._img = get_aa_icon("chk_off", outline, bg, extra_hex=pal["input_bg"], size=20)
        self.box.configure(bg=bg, image=self._img)


class SongPulseRadio(tk.Frame):
    """
    A SongPulse-style circular radio indicator rendered with anti-aliased SDF PhotoImage.
    """

    def __init__(self, master, text="", value="", variable=None, command=None, app_ref=None, **kwargs):
        super().__init__(master, cursor="hand2", **kwargs)
        self.text = text
        self.value = value
        self.variable = variable
        self.command = command
        self.app_ref = app_ref
        self._state = "normal"
        self._hover = False
        self._img = None

        self.circle = tk.Label(self, bd=0, highlightthickness=0)
        self.circle.pack(side="left", padx=(0, 5))

        self.lbl = tk.Label(self, text=text, font=("Segoe UI", 9), anchor="w")
        self.lbl.pack(side="left")

        for widget in (self, self.circle, self.lbl):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<ButtonRelease-1>", self._on_click)

        if self.variable is not None:
            self.variable.trace_add("write", lambda *args: self.redraw())

        self.redraw()

    def config(self, **kwargs):
        self.configure(**kwargs)

    def configure(self, **kwargs):
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            cur = "hand2" if self._state == "normal" else ""
            super().configure(cursor=cur)
            self.circle.configure(cursor=cur)
            self.lbl.configure(cursor=cur)
            self.redraw()
        if "text" in kwargs:
            self.text = kwargs.pop("text")
            self.lbl.configure(text=self.text)
        if kwargs:
            super().configure(**kwargs)

    def _on_enter(self, event=None):
        if self._state == "normal" and not self._hover:
            self._hover = True
            self.redraw()

    def _on_leave(self, event=None):
        if self._hover:
            self._hover = False
            self.redraw()

    def _on_click(self, event=None):
        if self._state != "normal":
            return
        if self.variable is not None:
            self.variable.set(self.value)
        self.redraw()
        if self.command:
            self.command()

    def redraw(self):
        if not self.winfo_exists():
            return
        is_dark = self.app_ref.get_target_dark_state() if self.app_ref else True
        pal = get_palette(is_dark)
        try:
            bg = self.master.cget("background")
            if not bg or not str(bg).startswith("#"):
                raise tk.TclError()
        except Exception:
            bg = pal["card_bg"]

        super().configure(bg=bg)
        disabled = self._state != "normal"
        selected = (self.variable.get() == self.value) if self.variable is not None else False
        self.lbl.configure(
            bg=bg,
            fg=pal["fg_disabled"] if disabled else (pal["fg"] if selected else pal["fg_secondary"]),
            font=("Segoe UI", 9, "bold" if selected else "normal"),
        )

        if selected:
            ring = pal["fg_disabled"] if disabled else pal["accent"]
            self._img = get_aa_icon("radio_on", ring, bg, size=20)
        else:
            outline = pal["accent"] if (self._hover and not disabled) else pal["input_border"]
            self._img = get_aa_icon("radio_off", outline, bg, extra_hex=pal["input_bg"], size=20)
        self.circle.configure(bg=bg, image=self._img)


class ModernSlider(tk.Canvas):
    """SongPulse-style slider with cyan-blue progress fill and dark-centered ringed circular thumb."""

    def __init__(
        self,
        master,
        from_=0.0,
        to=100.0,
        value=0.0,
        height=22,
        on_start=None,
        on_move=None,
        on_end=None,
        **kwargs,
    ):
        super().__init__(master, height=height, highlightthickness=0, bd=0, cursor="hand2", **kwargs)
        self.from_ = float(from_)
        self.to = float(to)
        self._value = float(value)
        self.on_start = on_start
        self.on_move = on_move
        self.on_end = on_end

        self.bg_color = "#15181e"
        self.track_color = "#787d87"
        self.fill_color = "#2997ff"
        self.thumb_color = "#252a34"
        self._hover = False
        self._dragging = False
        self._pad = 9

        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    def set_theme(self, bg, track, fill, thumb):
        self.bg_color = bg
        self.track_color = track
        self.fill_color = fill
        self.thumb_color = thumb
        self.configure(bg=bg)
        self.redraw()

    def set_range(self, from_, to):
        self.from_ = float(from_)
        self.to = max(self.from_ + 0.001, float(to))
        self.redraw()

    def set(self, val):
        self._value = max(self.from_, min(self.to, float(val)))
        self.redraw()

    def get(self):
        return self._value

    def _x_to_val(self, x):
        w = max(1, self.winfo_width() - 2 * self._pad)
        ratio = max(0.0, min(1.0, (x - self._pad) / w))
        return self.from_ + ratio * (self.to - self.from_)

    def _on_enter(self, event):
        self._hover = True
        self.redraw()

    def _on_leave(self, event):
        self._hover = False
        self.redraw()

    def _on_press(self, event):
        self._dragging = True
        self._value = self._x_to_val(event.x)
        self.redraw()
        if self.on_start:
            self.on_start(self._value)
        if self.on_move:
            self.on_move(self._value)

    def _on_drag(self, event):
        if not self._dragging:
            return
        self._value = self._x_to_val(event.x)
        self.redraw()
        if self.on_move:
            self.on_move(self._value)

    def _on_release(self, event):
        if not self._dragging:
            return
        self._dragging = False
        self._value = self._x_to_val(event.x)
        self.redraw()
        if self.on_end:
            self.on_end(self._value)

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 4 or h <= 4:
            return

        cy = h / 2
        x0 = self._pad
        x1 = max(x0 + 1, w - self._pad)
        ratio = (self._value - self.from_) / max(0.001, self.to - self.from_)
        kx = x0 + ratio * (x1 - x0)

        self.create_line(x0, cy, x1, cy, fill=self.track_color, width=4, capstyle="round")
        if kx > x0 + 1:
            self.create_line(x0, cy, kx, cy, fill=self.fill_color, width=4, capstyle="round")

        r = 7 if (self._hover or self._dragging) else 6
        self.create_oval(
            kx - r, cy - r, kx + r, cy + r, fill=self.thumb_color, outline=self.fill_color, width=2.5
        )
        self.create_oval(
            kx - 2, cy - 2, kx + 2, cy + 2, fill=self.fill_color, outline=""
        )


class HelpBadge(tk.Canvas):
    """SongPulse circular (?) badge rendered with anti-aliased SDF disc."""

    def __init__(self, master, title, description, app_ref):
        super().__init__(
            master,
            width=18,
            height=18,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.title = title
        self.description = description
        self.app_ref = app_ref
        self.tip_win = None
        self._hover = False
        self._disc_img = None

        self.bind("<Enter>", self.show_tip)
        self.bind("<Leave>", self.hide_tip)
        self.bind("<Button-1>", self.show_dialog)
        self.update_colors()

    def update_colors(self):
        if not self.winfo_exists():
            return
        is_dark = self.app_ref.get_target_dark_state()
        pal = get_palette(is_dark)
        try:
            parent_bg = self.master.cget("background")
            if not parent_bg or not str(parent_bg).startswith("#"):
                raise tk.TclError()
        except Exception:
            parent_bg = pal["card_bg"]

        self.configure(bg=parent_bg)
        self.delete("all")
        fill = pal["primary"] if self._hover else pal["badge_bg"]
        fg = "#ffffff" if self._hover else pal["badge_fg"]
        self._disc_img = get_aa_icon("help_circle", fill, parent_bg, size=18)
        self.create_image(9, 9, image=self._disc_img)
        self.create_text(9, 9, text="?", fill=fg, font=("Segoe UI", 8, "bold"))

    def show_tip(self, event=None):
        self._hover = True
        self.update_colors()
        if self.tip_win:
            return
        is_dark = self.app_ref.get_target_dark_state()
        pal = get_palette(is_dark)

        x = self.winfo_rootx() + 20
        y = self.winfo_rooty() + 20

        self.tip_win = tw = tk.Toplevel(self)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)

        frame = tk.Frame(
            tw,
            bg=pal["card_bg"],
            highlightbackground=pal["input_border"],
            highlightthickness=1,
            padx=12,
            pady=9,
        )
        frame.pack()

        tk.Label(
            frame,
            text=self.description,
            justify="left",
            bg=pal["card_bg"],
            fg=pal["fg"],
            font=("Segoe UI", 9),
            wraplength=340,
        ).pack()

    def hide_tip(self, event=None):
        self._hover = False
        self.update_colors()
        if self.tip_win:
            self.tip_win.destroy()
            self.tip_win = None

    def show_dialog(self, event=None):
        self.hide_tip()
        messagebox.showinfo(f"About {self.title}", self.description)


class WrapFrame(tk.Frame):
    """A container that wraps child widgets onto new rows only after resize settles."""

    def __init__(self, master=None, padx=6, pady=3, **kwargs):
        super().__init__(master, **kwargs)
        self.padx = padx
        self.pady = pady
        self._last_width = -1
        self._after_id = None
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event):
        if abs(event.width - self._last_width) >= 4:
            self._last_width = event.width
            if self._after_id:
                self.after_cancel(self._after_id)
            self._after_id = self.after(18, self.rearrange)

    def rearrange(self, event=None):
        self._after_id = None
        if not self.winfo_exists():
            return
        width = self.winfo_width()
        if width <= 1:
            return
        self._last_width = width
        x = 0
        y = self.pady
        row_h = 0
        for child in self.winfo_children():
            cw = child.winfo_reqwidth()
            ch = child.winfo_reqheight()
            max_cw = max(40, width - self.padx * 2)
            if x > 0 and x + cw + self.padx > width:
                x = 0
                y += row_h + self.pady * 2
                row_h = 0
            if cw > max_cw:
                child.place(x=x, y=y, width=max_cw)
                x += max_cw + self.padx * 2
            else:
                child.place(x=x, y=y, width="")
                x += cw + self.padx * 2
            if ch > row_h:
                row_h = ch
        total_h = max(28, y + row_h + self.pady)
        if self.winfo_height() != total_h:
            self.configure(height=total_h)
