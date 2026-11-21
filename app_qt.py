# -*- coding: utf-8 -*-
"""Zsharp (Qt) — 磨砂玻璃界面 · 图片/视频超分 · 本地 AI"""
import os, sys, json, time, tempfile, subprocess, queue, shutil, threading, glob
from PyQt5.QtCore import Qt, QTimer, QSize, QUrl, QRect, QPoint, QPointF, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QIcon, QColor, QPainter, QPainterPath, QFont, QKeySequence, QPen
from PyQt5.QtWidgets import (QStyle, QShortcut, QMenu, QSplitter, QLineEdit, QTextBrowser, QTabWidget, QApplication, QMainWindow, QWidget, QLabel, QPushButton,
                             QVBoxLayout, QHBoxLayout, QFrame, QComboBox, QSlider,
                             QListWidget, QListWidgetItem, QTextEdit, QProgressBar,
                             QFileDialog, QColorDialog, QMessageBox, QStackedWidget,
                             QDialog, QGridLayout, QSizePolicy, QGraphicsDropShadowEffect)
import ctypes

APP = "Zsharp"
APP_VERSION = "1.5.1"
# 更新清单：只有这里能改，打包时写死，用户端不可编辑
UPDATE_URL = ""
BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(BASE, "bin")
TMP = os.path.join(tempfile.gettempdir(), "zsharp_qt")
SETTINGS = os.path.join(BASE, "settings.json")
CREATEFLAGS = 0x08000000

IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
VID_EXT = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".m4v", ".ts", ".webm"}

def find_exe(names):
    for root, _, files in os.walk(BIN):
        for n in names:
            if n in files:
                return os.path.join(root, n)
    return None

VLC_DIR = None
for _root, _dirs, _files in os.walk(BIN):
    if "libvlc.dll" in _files and "plugins" in _dirs:
        VLC_DIR = _root
        break

def detect_gpu():
    """返回 (厂商, 名称)，用于自动选性能参数"""
    try:
        out = subprocess.run(["wmic", "path", "win32_VideoController", "get", "name"],
                             capture_output=True, creationflags=CREATEFLAGS).stdout.decode("utf-8", "replace")
    except Exception:
        out = ""
    up = out.upper()
    name = ""
    for line in out.splitlines():
        line = line.strip()
        if line and "NAME" not in line.upper():
            name = line
            if any(k in line.upper() for k in ("NVIDIA", "RADEON", "INTEL", "AMD", "ARC")):
                break
    if "NVIDIA" in up or "GEFORCE" in up or "RTX" in up or "GTX" in up:
        return "nvidia", name
    if "RADEON" in up or "AMD" in up:
        return "amd", name
    if "INTEL" in up or "ARC" in up:
        return "intel", name
    return "other", name


GPU_VENDOR, GPU_NAME = detect_gpu()

LIBMPV = find_exe(["libmpv-2.dll"])

RIFE = find_exe(["rife-ncnn-vulkan.exe"])
REALSR = find_exe(["realsr-ncnn-vulkan.exe"])
ESRGAN = find_exe(["realesrgan-ncnn-vulkan.exe"])
CUGAN = find_exe(["realcugan-ncnn-vulkan.exe"])
WAIFU = find_exe(["waifu2x-ncnn-vulkan.exe"])
FFMPEG = find_exe(["ffmpeg.exe"])

ENGINES = {
    "realesrgan": {"name": "Real-ESRGAN", "exe": ESRGAN, "models": [
        {"id": "realesr-animevideov3", "label": "动漫 / 视频 · 快速", "scales": [2, 3, 4], "dn": None},
        {"id": "realesrgan-x4plus-anime", "label": "动漫 · 高质量", "scales": [4], "dn": None},
        {"id": "realesrgan-x4plus", "label": "真人 / 实拍", "scales": [4], "dn": None}]},
    "realcugan": {"name": "Real-CUGAN", "exe": CUGAN, "models": [
        {"id": "models-se", "label": "动漫 · 均衡（SE）", "scales": [2, 3, 4], "dn": [-1, 0, 1, 2, 3]},
        {"id": "models-pro", "label": "动漫 · 强力（Pro）", "scales": [2, 3], "dn": [-1, 0, 3]}]},
    "realsr": {"name": "RealSR", "exe": REALSR, "models": [
        {"id": "models-DF2K", "label": "真人 / 实拍 · 高保真（DF2K）", "scales": [4], "dn": None},
        {"id": "models-DF2K_JPEG", "label": "真人 / 实拍 · 去 JPEG 脏边", "scales": [4], "dn": None}]},
    "waifu2x": {"name": "waifu2x", "exe": WAIFU, "models": [
        {"id": "models-cunet", "label": "动漫 · 降噪（CUNet）", "scales": [1, 2], "dn": [0, 1, 2, 3]},
        {"id": "models-upconv_7_anime_style_art_rgb", "label": "动漫 · 快速（Upconv）", "scales": [1, 2], "dn": [0, 1, 2, 3]},
        {"id": "models-upconv_7_photo", "label": "真人 · 快速（Photo）", "scales": [1, 2], "dn": [0, 1, 2, 3]}]},
}

def vtuple(v):
    import re
    nums = [int(x) for x in re.findall(r"\d+", str(v))[:3]]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def fetch_update(url, timeout=6):
    """读更新清单 JSON：{"version": "1.0.1", "url": "...", "notes": "..."}"""
    import urllib.request, json as _json
    req = urllib.request.Request(url, headers={"User-Agent": "Zsharp/" + APP_VERSION})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    return _json.loads(raw)


def load_cfg():
    d = {"accent": "#4f8cff", "bg": "", "blur": 0, "dim": 0, "model": 0, "scale": "4",
         "bg_crop": [0.0, 0.0, 1.0, 1.0]}
    try:
        d.update(json.load(open(SETTINGS, encoding="utf-8")))
    except Exception:
        pass
    return d

def save_cfg(d):
    try:
        json.dump(d, open(SETTINGS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass

def run(cmd, cwd=None):
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         startupinfo=_si(), creationflags=CREATEFLAGS)
    out = p.stdout.read()
    p.wait()
    return p.returncode, out.decode("utf-8", "replace")

def _si():
    s = subprocess.STARTUPINFO()
    s.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return s

def unique_path(path):
    """同名文件自动加 (1)、(2)…"""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while True:
        cand = f"{base}({i}){ext}"
        if not os.path.exists(cand):
            return cand
        i += 1


def fmt_t(sec):
    sec = max(0, int(sec))
    return f"{sec // 60}:{sec % 60:02d}"

def probe_video(path):
    import re
    rc, txt = run([FFMPEG, "-hide_banner", "-i", path])
    dur = 0.0
    w = h = 0
    fps = 0.0
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", txt)
    if m:
        dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = re.search(r"(\d{2,5})x(\d{2,5})", txt)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*fps", txt)
    if m:
        fps = float(m.group(1))
    return fps, dur, w, h

def probe_info(path):
    """返回 (w, h, fps, dur, frames)"""
    import re
    if not path or not os.path.exists(path):
        return (0, 0, 0.0, 0.0, 0)
    rc, txt = run([FFMPEG, "-hide_banner", "-i", path])
    w = h = 0
    fps = 0.0
    dur = 0.0
    m = re.search(r"(\d{2,5})x(\d{2,5})", txt)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", txt)
    if m:
        dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = re.search(r"(\d+(?:\.\d+)?)\s*fps", txt)
    if m:
        fps = float(m.group(1))
    frames = int(round(fps * dur)) if fps and dur else 0
    return (w, h, fps, dur, frames)


def build_cmd(ek, model, src, dst, scale, tile, dn, fmt="png", threads=None):
    exe = ENGINES[ek]["exe"]
    extra = ["-f", fmt]
    if threads:
        extra += ["-j", threads]
    if ek == "realesrgan":
        return [exe, "-i", src, "-o", dst, "-n", model["id"], "-s", str(scale), "-t", str(tile)] + extra, os.path.dirname(exe)
    if ek == "realsr":
        mdir = os.path.join(os.path.dirname(exe), model["id"])
        return [exe, "-i", src, "-o", dst, "-m", mdir, "-s", "4", "-t", str(tile)] + extra, os.path.dirname(exe)
    if ek == "realcugan":
        return [exe, "-i", src, "-o", dst, "-m", model["id"], "-s", str(scale), "-n", str(dn), "-t", str(tile)] + extra, os.path.dirname(exe)
    return [exe, "-i", src, "-o", dst, "-m", model["id"], "-s", str(scale), "-n", str(dn), "-t", str(tile)] + extra, os.path.dirname(exe)

class LibMpv:
    """libmpv 直连（无管道、无线程）：原帧率 / 原画幅 / 带声音，暂停不会卡界面"""
    def __init__(self, dll_path):
        self.ok = False
        self.h = None
        self.dll = None
        self.attached = False
        self.duration = 0.0
        if not dll_path:
            return
        try:
            d = ctypes.CDLL(dll_path)
            d.mpv_create.restype = ctypes.c_void_p
            d.mpv_set_option_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
            d.mpv_initialize.argtypes = [ctypes.c_void_p]
            d.mpv_command.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p)]
            d.mpv_get_property.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p]
            d.mpv_set_property_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
            d.mpv_get_property_string.restype = ctypes.c_char_p
            d.mpv_get_property_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            d.mpv_terminate_destroy.argtypes = [ctypes.c_void_p]
            self.dll = d
            self.h = d.mpv_create()
            self.ok = bool(self.h)
        except Exception:
            self.ok = False

    def attach(self, hwnd):
        if not self.ok or self.attached:
            return self.attached
        d = self.dll
        d.mpv_set_option_string(self.h, b"wid", str(int(hwnd)).encode())
        d.mpv_set_option_string(self.h, b"vo", b"gpu")
        d.mpv_set_option_string(self.h, b"hwdec", b"auto-safe")
        d.mpv_set_option_string(self.h, b"terminal", b"no")
        d.mpv_set_option_string(self.h, b"osc", b"no")
        d.mpv_set_option_string(self.h, b"input-default-bindings", b"no")
        d.mpv_set_option_string(self.h, b"keep-open", b"yes")
        rc = d.mpv_initialize(self.h)
        self.attached = (rc == 0)
        return self.attached

    def cmd(self, *args):
        if not self.ok:
            return -1
        arr = (ctypes.c_char_p * (len(args) + 1))(*[a.encode("utf-8") for a in args], None)
        return self.dll.mpv_command(self.h, arr)

    def load(self, path):
        return self.cmd("loadfile", path)

    def set_mute(self, on):
        try:
            self.dll.mpv_set_property_string(self.h, b"mute", b"yes" if on else b"no")
        except Exception:
            pass

    def set_pause(self, paused):
        self.dll.mpv_set_property_string(self.h, b"pause", b"yes" if paused else b"no")

    def set_osd(self, text):
        """在画面左上角常驻显示一行参数"""
        try:
            for k, v in (("osd-align-x", "left"), ("osd-align-y", "top"),
                         ("osd-margin-x", "14"), ("osd-margin-y", "6"),
                         ("osd-font-size", "24"), ("osd-level", "1"),
                         ("osd-back-color", "#000000B0"),
                         ("osd-border-color", "#000000B0"),
                         ("osd-border-size", "7")):
                self.dll.mpv_set_property_string(self.h, k.encode(), v.encode())
            self.cmd("show-text", text, "100000000")
        except Exception:
            pass

    def set_speed(self, v):
        try:
            self.dll.mpv_set_property_string(self.h, b"speed", ("%.3f" % v).encode())
        except Exception:
            pass

    def paused(self):
        try:
            v = ctypes.c_int(0)
            rc = self.dll.mpv_get_property(self.h, b"pause", 3, ctypes.byref(v))
            return bool(v.value) if rc == 0 else False
        except Exception:
            return False

    def seek(self, seconds):
        return self.cmd("seek", f"{seconds:.3f}", "absolute")

    def _prop(self, name):
        v = ctypes.c_double(0)
        rc = self.dll.mpv_get_property(self.h, name.encode(), 5, ctypes.byref(v))
        return v.value if rc == 0 else None

    def time(self):
        v = self._prop("time-pos")
        return v or 0.0

    def eof(self):
        try:
            v = ctypes.c_int(0)
            rc = self.dll.mpv_get_property(self.h, b"eof-reached", 3, ctypes.byref(v))
            return bool(v.value) if rc == 0 else False
        except Exception:
            return False

    def dur(self):
        v = self._prop("duration")
        if v:
            self.duration = v
        return self.duration

    def stop(self):
        try:
            self.cmd("stop")
        except Exception:
            pass

    def destroy(self):
        try:
            self.stop()
        except Exception:
            pass
        try:
            if self.h:
                self.dll.mpv_terminate_destroy(self.h)
        except Exception:
            pass
        self.h = None
        self.attached = False
        self.ok = False


QSS = """
QWidget { color: #e8e9ea; font-family: "Microsoft YaHei UI"; font-size: 9pt; }
QFrame#glass { background: rgba(24,26,31,150); border: 1px solid rgba(255,255,255,26); border-radius: 14px; }
QLabel { background: transparent; }
QLabel#title { font-size: 20pt; font-weight: bold; }
QLabel#sub { color: #a9adb4; font-size: 9pt; }
QLabel#hint { color: #9aa0a8; font-size: 8pt; }
QPushButton { background: rgba(255,255,255,30); border: 1px solid rgba(255,255,255,20);
              border-radius: 8px; padding: 6px 14px; }
QPushButton:hover { background: rgba(255,255,255,55); }
QPushButton:checked { background: rgba(79,140,255,200); border: 1px solid rgba(255,255,255,40); }
QPushButton#accent { background: rgba(79,140,255,220); font-weight: bold; padding: 8px 22px; }
QPushButton#accent:hover { background: rgba(100,160,255,240); }
QPushButton:disabled { color: #777c85; background: rgba(255,255,255,12); }
QComboBox { background: rgba(255,255,255,20); border: 1px solid rgba(255,255,255,18);
            border-radius: 6px; padding: 4px 8px; }
QComboBox QAbstractItemView { background: #24262b; selection-background-color: rgba(79,140,255,180); }
QListWidget { background: rgba(0,0,0,90); border: 1px solid rgba(255,255,255,16); border-radius: 10px; }
QListWidget::item { border-radius: 8px; padding: 4px; }
QListWidget::item:selected { background: rgba(79,140,255,150); }
QTextEdit { background: rgba(0,0,0,90); border: 1px solid rgba(255,255,255,16); border-radius: 10px;
            color: #cfd3d8; font-family: Consolas; }
QProgressBar { background: rgba(0,0,0,110); border-radius: 6px; text-align: center; height: 12px; }
QProgressBar::chunk { background: rgba(79,140,255,220); border-radius: 6px; }
QSlider::groove:horizontal { height: 6px; background: rgba(255,255,255,30); border-radius: 3px; }
QSlider::sub-page:horizontal { background: rgba(79,140,255,220); border-radius: 3px; }
QSlider::handle:horizontal { width: 14px; margin: -5px 0; border-radius: 7px; background: #ffffff; }
QScrollBar:vertical { background: transparent; width: 8px; }
QScrollBar::handle:vertical { background: rgba(255,255,255,60); border-radius: 4px; }
"""

class ClickSlider(QSlider):
    """点哪儿跳哪儿，拖动实时跟随"""
    jumped = pyqtSignal(int)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            val = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(),
                                                 int(e.x()), max(1, self.width()))
            self.setValue(val)
            self.jumped.emit(val)
        super().mousePressEvent(e)


class SplitHandle(QWidget):
    """对比模式下中间那条可拖动的分割线"""
    def __init__(self, on_drag):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint)
        self.on_drag = on_drag
        self.setStyleSheet("background: rgba(255,255,255,0.85);")
        self.setCursor(Qt.SizeHorCursor)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.hide()

    def mousePressEvent(self, e):
        self._press = e.globalPos().x()

    def mouseMoveEvent(self, e):
        if getattr(self, "_press", None) is not None:
            self.on_drag(self._press, e.globalPos().x())

    def mouseReleaseEvent(self, e):
        self._press = None


class _Sig(QObject):
    done = pyqtSignal(object)


def run_async(fn, cb):
    """后台跑 ffmpeg/解码，回主线程回调（参数是 QImage 或元组）"""
    sig = _Sig()
    sig.done.connect(cb)

    def job():
        try:
            res = fn()
        except Exception:
            res = None
        try:
            sig.done.emit(res)
        except Exception:
            pass

    threading.Thread(target=job, daemon=True).start()
    return sig


class CompareView(QWidget):
    """左右分割对比：左原图 / 右超分图，中间分割线可拖动"""
    def __init__(self):
        super().__init__()
        self.left = None
        self.right = None
        self.left_zoom = 1.0
        self.right_zoom = 1.0
        self.left_off = QPointF(0, 0)
        self.right_off = QPointF(0, 0)
        self._pan = None
        self.left_info = ""
        self.right_info = ""
        self.ratio = 0.5
        self._drag = False
        self.setMinimumHeight(200)
        self.setStyleSheet("background: rgba(0,0,0,150); border-radius: 8px;")
        self.setMouseTracking(True)

    def set_images(self, left, right, li="", ri=""):
        self.left, self.right = left, right
        self.left_info, self.right_info = li, ri
        self.left_zoom = self.right_zoom = 1.0
        self.left_off = QPointF(0, 0)
        self.right_off = QPointF(0, 0)
        self._cache = None
        self.update()

    def wheelEvent(self, e):
        d = e.angleDelta().y()
        f = 1.0 + (0.04 if d > 0 else -0.04) * (abs(d) / 120.0)
        if e.x() < self._split_x():
            self.left_zoom = max(1.0, min(10.0, self.left_zoom * f))
        else:
            self.right_zoom = max(1.0, min(10.0, self.right_zoom * f))
        self._cache = None
        self.update()
        e.accept()

    def _scaled(self):
        w, h = self.width(), self.height()
        if getattr(self, "_cache", None) and self._cache[0] == (w, h):
            return self._cache[1], self._cache[2]
        x = int(w * self.ratio)
        lp = self.left.scaled(x, h, Qt.KeepAspectRatio, Qt.SmoothTransformation) if self.left and not self.left.isNull() else None
        rp = self.right.scaled(max(1, w - x), h, Qt.KeepAspectRatio, Qt.SmoothTransformation) if self.right and not self.right.isNull() else None
        self._cache = ((w, h), lp, rp)
        return lp, rp

    def resizeEvent(self, e):
        self._cache = None
        super().resizeEvent(e)

    def _split_x(self):
        return int(self.width() * self.ratio)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(0, 0, 0, 200))
        x = self._split_x()
        # 左侧：以半区为基准自适应
        if self.left and not self.left.isNull():
            base = min(x / self.left.width(), h / self.left.height())
            sc = base * self.left_zoom
            lw = max(1, int(self.left.width() * sc))
            lh = max(1, int(self.left.height() * sc))
            lp = self.left.scaled(lw, lh, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.save()
            p.setClipRect(0, 0, x, h)
            p.drawPixmap(int((x - lp.width()) / 2 + self.left_off.x()),
                         int((h - lp.height()) / 2 + self.left_off.y()), lp)
            p.restore()
            self._label(p, 8, 6, self.left_info)
        # 右侧
        if self.right and not self.right.isNull():
            base = min((w - x) / self.right.width(), h / self.right.height())
            sc = base * self.right_zoom
            rw = max(1, int(self.right.width() * sc))
            rh = max(1, int(self.right.height() * sc))
            rp = self.right.scaled(rw, rh, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.save()
            p.setClipRect(x, 0, w - x, h)
            p.drawPixmap(int(x + ((w - x) - rp.width()) / 2 + self.right_off.x()),
                         int((h - rp.height()) / 2 + self.right_off.y()), rp)
            p.restore()
            self._label(p, x + 8, 6, self.right_info)
        p.setPen(QColor(255, 255, 255, 230))
        p.drawLine(x, 0, x, h)
        p.setBrush(QColor(255, 255, 255, 240))
        p.setPen(QColor(0, 0, 0, 0))
        p.drawEllipse(x - 9, h // 2 - 9, 18, 18)
        p.setPen(QColor(60, 60, 60))
        p.drawText(x - 4, h // 2 + 4, "↔")
        if getattr(self, "_loading", False):
            p.setPen(QColor(180, 185, 192))
            p.drawText(0, 0, w, h, Qt.AlignCenter, "加载中…")


    def _label(self, p, lx, ly, text):
        if not text:
            return
        p.setBrush(QColor(0, 0, 0, 180))
        p.setPen(Qt.NoPen)
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text) + 16
        th = fm.height() + 8
        p.drawRoundedRect(lx, ly, tw, th, 6, 6)
        p.setPen(QColor(233, 235, 238))
        p.drawText(lx + 8, ly + fm.ascent() + 3, text)

    def mousePressEvent(self, e):
        if abs(e.x() - self._split_x()) < 26:
            self._drag = True
        elif e.button() == Qt.LeftButton:
            self._pan = (e.pos(), e.x() < self._split_x())

    def mouseMoveEvent(self, e):
        if self._pan is not None:
            last, is_left = self._pan
            d = QPointF(e.pos() - last)
            if is_left:
                self.left_off += d
            else:
                self.right_off += d
            self._pan = (e.pos(), is_left)
            self.update()
            return
        if self._drag:
            self.ratio = max(0.05, min(0.95, e.x() / max(1, self.width())))
            self.update()
        else:
            self.setCursor(Qt.SizeHorCursor if abs(e.x() - self._split_x()) < 26 else Qt.ArrowCursor)

    def mouseReleaseEvent(self, e):
        self._drag = False
        self._pan = None


class ZoomLabel(QLabel):
    """图片预览：自适应铺满 + 滚轮细调缩放 + 左键拖拽平移 + 左上角参数框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background: rgba(0,0,0,120); border-radius: 8px; color:#7d828a;")
        self.pix = QPixmap()
        self.zoom = 1.0
        self.info = ""
        self.off = QPointF(0, 0)
        self._drag = None
        self.setMouseTracking(True)
        self.setCursor(Qt.OpenHandCursor)

    def set_image(self, pix, info=""):
        self.pix = pix
        self.info = info
        self.zoom = 1.0
        self.off = QPointF(0, 0)
        self.update()

    def clear_image(self, text="预览区"):
        self.pix = QPixmap()
        self.info = ""
        self.zoom = 1.0
        self.off = QPointF(0, 0)
        self.setText(text)
        self.update()

    def _base_scale(self):
        if self.pix.isNull():
            return 1.0
        return min(self.width() / self.pix.width(), self.height() / self.pix.height())

    def wheelEvent(self, e):
        if self.pix.isNull():
            return
        d = e.angleDelta().y()
        step = 1.0 + (0.04 if d > 0 else -0.04) * (abs(d) / 120.0)
        self.zoom = max(1.0, min(10.0, self.zoom * step))
        self._clamp()
        self.update()
        e.accept()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.pix.isNull():
            self._drag = e.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.off += QPointF(e.pos() - self._drag)
            self._drag = e.pos()
            self._clamp()
            self.update()

    def mouseReleaseEvent(self, e):
        self._drag = None
        self.setCursor(Qt.OpenHandCursor)

    def _clamp(self):
        if self.pix.isNull():
            return
        s = self._base_scale() * self.zoom
        iw, ih = self.pix.width() * s, self.pix.height() * s
        maxx = max(0.0, (iw - self.width()) / 2)
        maxy = max(0.0, (ih - self.height()) / 2)
        self.off = QPointF(max(-maxx, min(maxx, self.off.x())),
                           max(-maxy, min(maxy, self.off.y())))

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 150))
        if not self.pix.isNull():
            s = self._base_scale() * self.zoom
            w, h = max(1, int(self.pix.width() * s)), max(1, int(self.pix.height() * s))
            pm = self.pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self.width() - pm.width()) / 2 + self.off.x()
            y = (self.height() - pm.height()) / 2 + self.off.y()
            p.drawPixmap(int(x), int(y), pm)
        if self.info:
            p.setBrush(QColor(0, 0, 0, 180))
            p.setPen(Qt.NoPen)
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(self.info) + 18
            th = fm.height() + 10
            p.drawRoundedRect(8, 6, tw, th, 6, 6)
            p.setPen(QColor(233, 235, 238))
            p.drawText(17, 6 + fm.ascent() + 4, self.info)


class Glass(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glass")


class Panel(QWidget):
    """一个工作区（图片 / 视频）"""
    def __init__(self, app, kind):
        super().__init__()
        self.app = app
        self.kind = kind
        self.tasks = []
        self.worker = None
        self.stop_flag = False
        self.proc = None
        self._thumb_icons = []
        self.build()

    # ---------- UI ----------
    def build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(14)

        # 左：参数
        left = Glass()
        left.setFixedWidth(300)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 14, 16, 14)
        ll.setSpacing(6)

        ll.addWidget(QLabel("模型"))
        self.cmb_model = QComboBox()
        ll.addWidget(self.cmb_model)
        self.lbl_hint = QLabel("")
        self.lbl_hint.setObjectName("hint")
        self.lbl_hint.setWordWrap(True)
        ll.addWidget(self.lbl_hint)

        ll.addWidget(QLabel("放大倍数"))
        self.cmb_scale = QComboBox()
        ll.addWidget(self.cmb_scale)

        ll.addWidget(QLabel("降噪强度（-1 = 不降噪）"))
        self.cmb_dn = QComboBox()
        ll.addWidget(self.cmb_dn)

        row = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("切块"))
        self.cmb_tile = QComboBox()
        self.cmb_tile.addItems(["0", "128", "256", "384", "512"])
        self.cmb_tile.setCurrentText("512" if GPU_VENDOR == "nvidia" else "256")
        col1.addWidget(self.cmb_tile)
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("视频画质"))
        self.cmb_crf = QComboBox()
        self.cmb_crf.addItems(["16", "18", "20", "23"])
        self.cmb_crf.setCurrentText("18")
        col2.addWidget(self.cmb_crf)
        row.addLayout(col1)
        if self.kind == "video":
            row.addLayout(col2)
        ll.addLayout(row)

        if self.kind == "video":
            ll.addWidget(QLabel("插帧方式"))
            self.cmb_fps = QComboBox()
            self.cmb_fps.addItems(["关闭", "光流（ffmpeg）", "RIFE（AI 动漫）", "RIFE（AI 通用）"])
            ll.addWidget(self.cmb_fps)
            ll.addWidget(QLabel("插帧倍数"))
            self.cmb_mult = QComboBox()
            self.cmb_mult.addItems(["2×", "3×", "4×"])
            self.cmb_mult.setEnabled(False)
            self.cmb_fps.currentIndexChanged.connect(
                lambda i: self.cmb_mult.setEnabled(i != 0))
            ll.addWidget(self.cmb_mult)
            self.chk_dedup = QPushButton("替换重复帧（去重）")
            self.chk_dedup.setCheckable(True)
            self.chk_dedup.setToolTip("去掉完全重复的帧，适合 12fps 平移的番剧；开插帧前先开它效果更好")
            ll.addWidget(self.chk_dedup)
            ll.addWidget(QLabel("并行线程（加载:处理:保存）"))
            self.cmb_j = QComboBox()
            self.cmb_j.addItems(["1:2:2", "2:2:2", "2:4:4", "3:6:6"])
            self.cmb_j.setCurrentText("2:4:4" if GPU_VENDOR == "nvidia" else "1:2:2")
            ll.addWidget(self.cmb_j)
            self.chk_fast = QPushButton("快速模式（中间帧用 JPG）")
            self.chk_fast.setCheckable(True)
            self.chk_fast.setChecked(GPU_VENDOR == "nvidia")
            self.chk_fast.setToolTip("更快，画质几乎无损；A 卡可不开")
            ll.addWidget(self.chk_fast)

        ll.addWidget(QLabel("画面调整"))
        self.sl = {}
        for key, label, lo, hi, dv in (("c", "对比度", -30, 50, 0), ("s", "饱和度", -40, 60, 0),
                                       ("h", "锐化", 0, 150, 0), ("q", "清晰度", 0, 100, 0),
                                       ("b", "亮度", -10, 10, 0)):
            r = QHBoxLayout()
            r.addWidget(QLabel(label))
            val = QLabel("+0" if key not in ("h", "q") else "0")
            val.setObjectName("hint")
            r.addStretch()
            r.addWidget(val)
            ll.addLayout(r)
            s = QSlider(Qt.Horizontal)
            s.setRange(lo, hi)
            s.setValue(dv)
            s.valueChanged.connect(lambda v, vl=val, k=key: vl.setText(
                (f"{v:+d}" if k not in ('h', 'q') else f"{v}") ))
            self.sl[key] = s
            ll.addWidget(s)

        ll.addStretch()
        ll.addWidget(QLabel("输出目录"))
        default_out = self.app.cfg.get("out_video" if self.kind == "video" else "out_image") or \
            os.path.join(BASE, "output", "视频" if self.kind == "video" else "图片")
        self.txt_out = QLabel(default_out)
        self.txt_out.setObjectName("hint")
        self.txt_out.setWordWrap(True)
        ll.addWidget(self.txt_out)
        r = QHBoxLayout()
        b1 = QPushButton("选择…")
        b1.clicked.connect(self.choose_out)
        b2 = QPushButton("打开")
        b2.clicked.connect(self.open_out)
        r.addWidget(b1)
        r.addWidget(b2)
        ll.addLayout(r)
        lay.addWidget(left)

        # 右
        right = QVBoxLayout()
        right.setSpacing(10)

        prev_frame = Glass()
        pv = QVBoxLayout(prev_frame)
        pv.setContentsMargins(10, 8, 10, 8)
        self.lbl_info = QLabel("把文件拖进来就能在这里看到")
        self.lbl_info.setObjectName("hint")
        pv.addWidget(self.lbl_info)

        self.stack = QStackedWidget()
        self.stack.setMinimumHeight(300)
        self.lbl_preview = ZoomLabel()
        self.lbl_preview.setText("预览区")
        self.stack.addWidget(self.lbl_preview)
        self.vlc = None
        if self.kind == "video":
            self.vhost = QWidget()
            self.vhost.setAttribute(Qt.WA_NativeWindow, True)
            self.vhost.setStyleSheet("background: #000;")
            self.vhost2 = QWidget()
            self.vhost2.setAttribute(Qt.WA_NativeWindow, True)
            self.vhost2.setStyleSheet("background: #000;")
            self.split = QSplitter(Qt.Horizontal)
            self.split.setStyleSheet(
                "QSplitter::handle { background: rgba(255,255,255,0.85); width: 6px; }")
            self.split.addWidget(self.vhost)
            self.split.addWidget(self.vhost2)
            self.split.setSizes([500, 500])
            self.stack.addWidget(self.split)

            self.mpv = LibMpv(LIBMPV)
            self.mpv2 = LibMpv(LIBMPV)
            self._loaded = None
            self._loaded2 = None
            self._paused = False
            self._timer = QTimer(self)
            self._timer.timeout.connect(self.tick)
            self._timer.start(250)
        self.cmp = CompareView()
        self.lbl_result = ZoomLabel()
        self.lbl_result.setText("超分结果")
        self.stack.addWidget(self.cmp)
        self.stack.addWidget(self.lbl_result)
        pv.addWidget(self.stack, 1)

        self.i_cmp = self.stack.indexOf(self.cmp)
        self.i_res = self.stack.indexOf(self.lbl_result)
        self.i_video = self.stack.indexOf(self.split) if self.kind == "video" else -1

        mrow = QHBoxLayout()
        mrow.setSpacing(6)
        self.btn_modes = []
        for i, name in enumerate(("原素材", "超分后", "左右对比")):
            b = QPushButton(name)
            b.setCheckable(True)
            b.setFixedHeight(26)
            b.clicked.connect(lambda _, i=i: self.set_mode(i))
            self.btn_modes.append(b)
            mrow.addWidget(b)
        self.btn_modes[0].setChecked(True)
        mrow.addStretch()
        pv.addLayout(mrow)
        self.mode = 0

        if self.kind == "video":
            row = QHBoxLayout()
            self.btn_play = QPushButton()
            self.btn_play.setFixedSize(74, 30)
            self.btn_play.setIconSize(QSize(18, 18))
            self.btn_play.setIcon(QIcon(os.path.join(BASE, "ic_play.png")))
            self.btn_play.setToolTip("播放 / 暂停")
            self.btn_play.clicked.connect(self.toggle_play)
            row.addWidget(self.btn_play)
            self.slider = ClickSlider(Qt.Horizontal)
            self.slider.setRange(0, 1000)
            self.slider.sliderMoved.connect(self.seek)
            self.slider.jumped.connect(self.seek)
            self.slider.setToolTip("点击或拖动跳转")
            row.addWidget(self.slider, 1)
            self.lbl_time = QLabel("0:00 / 0:00")
            self.lbl_time.setObjectName("hint")
            row.addWidget(self.lbl_time)
            pv.addLayout(row)
        right.addWidget(prev_frame, 1)

        bar = QHBoxLayout()
        badd = QPushButton("＋ 添加图片" if self.kind == "image" else "＋ 添加视频")
        badd.clicked.connect(self.add_files)
        bdir = QPushButton("＋ 添加文件夹")
        bdir.clicked.connect(self.add_folder)
        bclr = QPushButton("清空")
        bclr.clicked.connect(self.clear)
        tip = QLabel("支持拖入窗口" + ("，png/jpg/bmp/webp" if self.kind == "image" else "，mp4/mkv/avi/mov"))
        tip.setObjectName("hint")
        bar.addWidget(badd)
        bar.addWidget(bdir)
        bar.addWidget(bclr)
        bar.addWidget(tip)
        bar.addStretch()
        right.addLayout(bar)

        self.list = QListWidget()
        if self.kind == "image":
            self.list.setViewMode(QListWidget.IconMode)
            self.list.setIconSize(QSize(150, 84))
            self.list.setGridSize(QSize(166, 130))
            self.list.setResizeMode(QListWidget.Adjust)
            self.list.setSpacing(6)
        self.list.setSelectionMode(QListWidget.ExtendedSelection)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.list_menu)
        self.list.setFixedHeight(150 if self.kind == "image" else 110)
        for key in (Qt.Key_Backspace, Qt.Key_Delete):
            sc = QShortcut(QKeySequence(key), self.list)
            sc.setContext(Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(self.delete_selected)
        self.list.currentRowChanged.connect(self.on_select)
        right.addWidget(self.list)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(78)
        right.addWidget(self.log)

        self.lbl_now = QLabel("就绪")
        self.lbl_now.setObjectName("hint")
        self.lbl_now.setStyleSheet("color:#9fb6d6; font-size:9pt; padding-left:2px;")
        right.addWidget(self.lbl_now)

        bot = QHBoxLayout()
        self.prog = QProgressBar()
        self.prog.setValue(0)
        bot.addWidget(self.prog, 1)
        self.lbl_all = QLabel("0%")
        self.lbl_all.setObjectName("hint")
        bot.addWidget(self.lbl_all)
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.cancel)
        self.btn_start = QPushButton("开始处理")
        self.btn_start.setObjectName("accent")
        self.btn_start.clicked.connect(self.start)
        bot.addWidget(self.btn_stop)
        bot.addWidget(self.btn_start)
        right.addLayout(bot)

        lay.addLayout(right, 1)
        self.reload_models()

    @property
    def out_dir(self):
        return self.txt_out.text()

    # ---------- 模型 ----------
    def reload_models(self):
        self.model_map = {}
        self.cmb_model.clear()
        for k, eng in ENGINES.items():
            if not eng["exe"]:
                continue
            for m in eng["models"]:
                label = f"{m['label']}  ·  {eng['name']}"
                self.model_map[label] = (k, m)
                self.cmb_model.addItem(label)
        self.cmb_model.currentTextChanged.connect(self.on_model)
        self.on_model()

    def on_model(self):
        label = self.cmb_model.currentText()
        if label not in self.model_map:
            return
        k, m = self.model_map[label]
        self.cmb_scale.clear()
        self.cmb_scale.addItems([str(s) for s in m["scales"]])
        self.cmb_scale.setCurrentText("2" if (self.kind == "video" and "2" in [str(s) for s in m["scales"]]) else str(m["scales"][-1]))
        self.cmb_dn.clear()
        if m["dn"]:
            self.cmb_dn.addItems([str(d) for d in m["dn"]])
            self.cmb_dn.setEnabled(True)
        else:
            self.cmb_dn.addItems(["-1"])
            self.cmb_dn.setEnabled(False)

    def params(self):
        k, m = self.model_map[self.cmb_model.currentText()]
        tile = int(self.cmb_tile.currentText())
        dn = int(self.cmb_dn.currentText() or -1)
        threads = self.cmb_j.currentText() if self.kind == "video" and hasattr(self, "cmb_j") else None
        fast = bool(getattr(self, "chk_fast", None) and self.chk_fast.isChecked())
        return k, m, int(self.cmb_scale.currentText()), tile, dn, threads, fast

    def filters(self):
        c = 1 + self.sl["c"].value() / 100.0
        s = 1 + self.sl["s"].value() / 100.0
        b = self.sl["b"].value() / 100.0
        sh = self.sl["h"].value() / 100.0
        q = self.sl["q"].value() / 100.0
        parts = []
        if abs(c - 1) > 0.005 or abs(s - 1) > 0.005 or abs(abs(b)) > 0.002:
            parts.append(f"eq=contrast={round(c,3)}:saturation={round(s,3)}:brightness={round(b,3)}")
        if sh > 0.02:
            parts.append(f"unsharp=5:5:{round(sh,3)}:3:3:0")
        if q > 0.02:
            # 大半径 unsharp = 局部对比度（清晰度）
            parts.append(f"unsharp=11:11:{round(q,3)}:11:11:0")
        return ",".join(parts)

    # ---------- 文件 ----------
    def add_files(self):
        self._begin_modal()
        try:
            self._add_files()
        finally:
            self._end_modal()

    def _add_files(self):
        if self.kind == "image":
            f, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", "图片 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)")
        else:
            f, _ = QFileDialog.getOpenFileNames(self, "选择视频", "", "视频 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.m4v *.ts *.webm)")
        self.add_paths(f)

    def add_folder(self):
        self._begin_modal()
        try:
            self._add_folder()
        finally:
            self._end_modal()

    def _add_folder(self):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if not d:
            return
        allow = IMG_EXT if self.kind == "image" else VID_EXT
        files = []
        for root, _, fs in os.walk(d):
            for f in fs:
                if os.path.splitext(f)[1].lower() in allow:
                    files.append(os.path.join(root, f))
        self.add_paths(sorted(files))

    def add_paths(self, paths):
        allow = IMG_EXT if self.kind == "image" else VID_EXT
        first = -1
        for p in paths:
            if os.path.splitext(p)[1].lower() not in allow:
                continue
            if any(t["path"] == p for t in self.tasks):
                continue
            self.tasks.append({"path": p, "name": os.path.basename(p), "status": "等待", "pct": 0.0})
            item = QListWidgetItem(self.make_icon(p) if self.kind == "image" else QIcon(), os.path.basename(p))
            if self.kind == "video":
                item.setSizeHint(QSize(0, 28))
            self.list.addItem(item)
            if first < 0:
                first = self.list.count() - 1
        if first >= 0:
            self.list.setCurrentRow(first)

    def make_icon(self, path):
        os.makedirs(TMP, exist_ok=True)
        out = os.path.join(TMP, f"t_{abs(hash(path))}.png")
        if not os.path.exists(out):
            subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", path,
                            "-frames:v", "1", "-vf", "scale=300:-2", out],
                           capture_output=True, startupinfo=_si(), creationflags=CREATEFLAGS)
        pm = QPixmap(out)
        if pm.isNull():
            return QIcon()
        return QIcon(pm.scaled(150, 84, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def list_menu(self, pos):
        item = self.list.itemAt(pos)
        if item is not None and not item.isSelected():
            self.list.clearSelection()
            item.setSelected(True)
        m = QMenu(self)
        act = m.addAction("删除选中")
        act.triggered.connect(self.delete_selected)
        m.addSeparator()
        m.addAction("清空全部").triggered.connect(self.clear)
        m.exec_(self.list.mapToGlobal(pos))

    def delete_selected(self):
        if self.worker and self.worker.is_alive():
            QMessageBox.information(self, "提示", "正在处理中，先停止。")
            return
        items = self.list.selectedItems()
        if not items:
            return
        rows = sorted({self.list.row(it) for it in items}, reverse=True)
        for r in rows:
            if 0 <= r < len(self.tasks):
                self.list.takeItem(r)
                del self.tasks[r]
        if not self.tasks:
            self.lbl_preview.clear_image("预览区")
            self.lbl_info.setText("把文件拖进来就能在这里看到")
            if self.kind == "video":
                try:
                    self.mpv.stop(); self.mpv2.stop()
                    self._loaded = None; self._loaded2 = None
                    self.stack.setCurrentIndex(0)
                    if hasattr(self, "slider"):
                        self.slider.setValue(0)
                    self.lbl_time.setText("0:00 / 0:00")
                    self.set_play_icon("play")
                except Exception:
                    pass
            if self.kind == "video" and getattr(self, "mpv", None):
                self.mpv.stop()
                self._loaded = None
            return
        self.list.setCurrentRow(min(rows[-1], len(self.tasks) - 1))
        self.on_select(self.list.currentRow())

    def clear(self):
        if self.worker and self.worker.is_alive():
            QMessageBox.information(self, "提示", "正在处理中，先停止。")
            return
        self.tasks.clear()
        self.list.clear()
        self.lbl_preview.clear_image("预览区")
        if self.kind == "video":
            if self.mpv:
                self.mpv.stop()
            self.stack.setCurrentIndex(0)
        self.lbl_info.setText("把文件拖进来就能在这里看到")

    def _img_info_text(self, path):
        pm = QPixmap(path) if os.path.exists(path) else QPixmap()
        if pm.isNull():
            return ""
        return "%d×%d  %d KB" % (pm.width(), pm.height(),
                                 max(1, os.path.getsize(path) // 1024))

    def show_image(self, path):
        img = self._load_preview_image(path, 0, 2000)
        if img is None:
            self.lbl_preview.setText("无法读取这张图片")
            return
        self.stack.setCurrentIndex(0)
        self.lbl_preview.set_image(QPixmap.fromImage(img), self._img_info_text(path))

    def on_select(self, row):
        if row < 0 or row >= len(self.tasks):
            return
        t = self.tasks[row]
        self.lbl_info.setText(t["name"])
        if self.kind == "image":
            self.show_image(t["path"])
            self.refresh_view()
        else:
            if self.mpv:
                self.mpv.stop()
                self._last_pos = 0.0
                self._ended = False
                self._loaded = None
            self.fit_preview(t["path"])
            self.mode_pos = {0: 0.0, 1: 0.0, 2: 0.0}
            self._loaded2 = None
            self.slider.setValue(0)
            self.load_mode(0.0)
            QTimer.singleShot(700, self.update_overlays)

    def fit_preview(self, path):
        """按视频分辨率调整预览区画幅（对比模式不动）"""
        if getattr(self, "mode", 0) == 2:
            return
        fps, dur, w, h = probe_video(path)
        if w <= 0 or h <= 0:
            return
        avail = max(320, self.stack.width() - 20)
        want_h = int(avail * h / w)
        want_h = max(180, min(want_h, 460))
        self.stack.setFixedHeight(want_h)

    def current_task(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.tasks):
            return self.tasks[row]
        return None

    def find_result(self, t):
        """在自己输出目录里找该素材的超分结果（兼容各种命名）"""
        stem = os.path.splitext(t["name"])[0]
        d = self.out_dir
        if not os.path.isdir(d):
            return None
        ext = ".png" if self.kind == "image" else ".mp4"
        cands = []
        for f in os.listdir(d):
            low = f.lower()
            if not low.endswith(ext):
                continue
            if low.startswith(stem.lower()):
                cands.append(os.path.join(d, f))
        if not cands:
            pat = os.path.join(d, "*" + ext)
            cands = [f for f in glob.glob(pat) if stem.lower() in os.path.basename(f).lower()]
        if not cands:
            return None
        cands.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        return cands[0]

    def grab_frame(self, path, t, w=760):
        os.makedirs(TMP, exist_ok=True)
        out = os.path.join(TMP, "fr_%d_%d.png" % (abs(hash(path)), int(t * 10)))
        if os.path.exists(out):
            return QPixmap(out)
        cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error"]
        if t > 0.05:
            cmd += ["-ss", "%.2f" % t]
        cmd += ["-i", path, "-frames:v", "1", "-vf", "scale=%d:-2" % w, out]
        subprocess.run(cmd, capture_output=True, startupinfo=_si(), creationflags=CREATEFLAGS)
        return QPixmap(out) if os.path.exists(out) else QPixmap()

    def set_mode(self, i):
        if i == self.mode:
            return
        for pl in (getattr(self, "mpv", None), getattr(self, "mpv2", None)):
            try:
                if pl is not None and pl.attached:
                    pl.set_pause(True)
                    pl.seek(0)
            except Exception:
                pass
        self._paused = True
        self._ended = False
        self.mode = i
        for k, b in enumerate(self.btn_modes):
            b.setChecked(k == i)
        if hasattr(self, "slider"):
            self.slider.setValue(0)
        self.set_play_icon("play")
        self.load_mode(0.0, autoplay=True)
        QTimer.singleShot(500, self.update_overlays)

    def _load_preview_image(self, path, t=0.0, width=900):
        """后台生成预览图（QImage），带缓存"""
        if not path or not os.path.exists(path):
            return None
        key = (path, os.path.getmtime(path), round(t, 1), width)
        cache = getattr(self, "_img_cache", None)
        if cache is None:
            cache = self._img_cache = {}
        if key in cache:
            return cache[key]
        from PyQt5.QtGui import QImage
        ext = os.path.splitext(path)[1].lower()
        if ext in IMG_EXT and t <= 0.001:
            img = QImage(path)
            if not img.isNull() and img.width() > width:
                img = img.scaledToWidth(width, Qt.SmoothTransformation)
        else:
            os.makedirs(TMP, exist_ok=True)
            out = os.path.join(TMP, "pv_%d.png" % abs(hash(key)))
            cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error"]
            if t > 0.05:
                cmd += ["-ss", "%.2f" % t]
            cmd += ["-i", path, "-frames:v", "1", "-vf", "scale=%d:-2" % width, out]
            subprocess.run(cmd, capture_output=True, startupinfo=_si(), creationflags=CREATEFLAGS)
            img = QImage(out) if os.path.exists(out) else QImage()
        if img.isNull():
            return None
        cache[key] = img
        return img

    def refresh_view(self):
        t = self.current_task()
        self._view_token = getattr(self, "_view_token", 0) + 1
        token = self._view_token
        if t is None:
            self.stack.setCurrentIndex(0)
            self.lbl_preview.clear_image("预览区")
            return
        if self.mode == 0:
            if self.kind == "video":
                self.stack.setCurrentIndex(self.i_video)
                self._sync_hosts()
            else:
                self.show_image(t["path"])
            return
        if self.kind == "video":
            self.load_mode(0.0, autoplay=False)
            return
        if self.mode == 1:
            res = self.find_result(t)
            self.stack.setCurrentIndex(self.i_res)
            if not res:
                self.lbl_result.clear_image("还没有超分结果\n点「开始处理」后这里显示放大后的画面")
                return
            self.lbl_result.setText("加载中…")
            self._res_info = self._img_info_text(res)
            run_async(lambda: self._load_preview_image(res, 0, 2000),
                      lambda img, tk=token: self._show_result(img, tk))
        else:
            res = self.find_result(t)
            self.stack.setCurrentIndex(self.i_cmp)
            self.cmp.set_images(None, None)
            self.cmp._loading = True
            self.cmp.update()
            src = t["path"]
            run_async(lambda: (self._load_preview_image(src, 0, 900),
                               self._load_preview_image(res, 0, 900) if res else None),
                      lambda pair, tk=token: self._show_cmp(pair, tk))

    def tick(self):
        if self.kind != "video":
            return
        p = self._active_player()
        if p is None or not p.attached:
            return
        if getattr(self, "_ended", False):
            return
        pos = p.time()
        dur = p.dur()
        if dur > 0:
            if not self.slider.isSliderDown():
                self.slider.setMaximum(int(dur * 1000))
                self.slider.setValue(int(pos * 1000))
            self.lbl_time.setText(f"{fmt_t(pos)} / {fmt_t(dur)}")
            # 图标始终跟随 mpv 真实状态
            self.set_play_icon("play" if p.paused() else "pause")
            if pos >= dur - 0.12:
                self._ended = True
                self.set_play_icon("replay")
        if self.mode == 2 and self.mpv2.attached and not (
                hasattr(self, "_seek_timer") and self._seek_timer.isActive()) \
                and not self.mpv.paused():
            now = time.time()
            drift = self.mpv2.time() - pos
            ad = abs(drift)
            if ad > 0.35:
                # 差距过大：直接对齐两路，重置同步状态
                self.mpv.seek(pos)
                self.mpv2.seek(pos)
                self.mpv.set_speed(1.0)
                self.mpv2.set_speed(1.0)
                self._sync_state = 0
            elif ad > 0.06:
                # 进入追赶：只在开始时设一次速度，保持至少 1.5 秒
                if getattr(self, "_sync_state", 0) != 1:
                    self._sync_state = 1
                    self._sync_since = now
                    if drift > 0:
                        self.mpv.set_speed(1.05)
                        self.mpv2.set_speed(0.95)
                    else:
                        self.mpv.set_speed(0.95)
                        self.mpv2.set_speed(1.05)
                elif now - getattr(self, "_sync_since", now) > 2.0:
                    # 追了 2 秒还没追平，硬对齐一次
                    self.mpv.seek(pos)
                    self.mpv2.seek(pos)
                    self.mpv.set_speed(1.0)
                    self.mpv2.set_speed(1.0)
                    self._sync_state = 0
            else:
                # 已对齐：需要滞回，避免来回切换速度
                if getattr(self, "_sync_state", 0) == 1 and ad < 0.02:
                    self.mpv.set_speed(1.0)
                    self.mpv2.set_speed(1.0)
                    self._sync_state = 0

    def _osd_info(self, pl, path):
        try:
            w, h, fps, dur, fr = probe_info(path)
            if not w:
                return
            pl.set_osd("%d×%d  %.2f fps  %d 帧  %s" % (w, h, fps, fr, fmt_t(dur)))
        except Exception:
            pass

    def update_overlays(self):
        if self.kind != "video":
            return
        t = self.current_task()
        if t is None:
            return
        if self.mpv.attached and self._loaded:
            self._osd_info(self.mpv, self._loaded)
        if self.mpv2.attached and self._loaded2:
            self._osd_info(self.mpv2, self._loaded2)


    def _sync_hosts(self):
        """按模式决定左右两个画面区谁显示"""
        try:
            if self.mode == 2:
                self.vhost.show()
                self.vhost2.show()
                self.split.setSizes([500, 500])
            elif self.mode == 1:
                self.vhost.hide()
                self.vhost2.show()
                self.split.setSizes([0, 1000])
            else:
                self.vhost.show()
                self.vhost2.hide()
                self.split.setSizes([1000, 0])
        except Exception:
            pass

    def load_mode(self, start=0.0, autoplay=True):
        t = self.current_task()
        if t is None:
            self.refresh_view()
            return
        self._view_token = getattr(self, "_view_token", 0) + 1
        if self.kind != "video":
            self.refresh_view()
            return
        self.stack.setCurrentIndex(self.i_video)
        self._sync_hosts()
        res = self.find_result(t)
        self.btn_play.setEnabled(True)
        self._paused = not autoplay

        if self.mode == 0:
            if not self.mpv.attached:
                self.vhost.update()
                self.mpv.attach(self.vhost.winId())
            if self._loaded != t["path"]:
                self.mpv.load(t["path"])
                self._loaded = t["path"]
                self._osd_info(self.mpv, t["path"])
            self.mpv.set_mute(False)
            self.mpv.seek(start)
            self.mpv.set_pause(not autoplay)
        elif self.mode == 1:
            if not res:
                self.stack.setCurrentIndex(self.i_res)
                self.lbl_result.clear_image("还没有超分结果\n点「开始处理」后这里显示放大后的画面")
                self.btn_play.setEnabled(False)
                return
            self.stack.setCurrentIndex(self.i_video)
            if not self.mpv2.attached:
                self.vhost2.update()
                self.mpv2.attach(self.vhost2.winId())
                self.mpv2.set_mute(True)
            if self._loaded2 != res:
                self.mpv2.load(res)
                self._loaded2 = res
                self._osd_info(self.mpv2, res)
            self.mpv2.set_mute(False)
            self.mpv2.seek(start)
            self.mpv2.set_pause(not autoplay)
        else:
            if res:
                if not self.mpv.attached:
                    self.vhost.update()
                    self.mpv.attach(self.vhost.winId())
                if self._loaded != t["path"]:
                    self.mpv.load(t["path"])
                    self._loaded = t["path"]
                    self._osd_info(self.mpv, t["path"])
                if not self.mpv2.attached:
                    self.vhost2.update()
                    self.mpv2.attach(self.vhost2.winId())
                    self.mpv2.set_mute(True)
                if self._loaded2 != res:
                    self.mpv2.load(res)
                    self._loaded2 = res
                    self._osd_info(self.mpv2, res)
                self.mpv.set_mute(False)
                self.mpv2.set_mute(True)
                self.mpv.seek(start)
                self.mpv2.seek(start)
                self.mpv.set_pause(not autoplay)
                self.mpv2.set_pause(not autoplay)
            else:
                self.stack.setCurrentIndex(self.i_cmp)
                self.btn_play.setEnabled(False)
                self._hide_compare()
                self.schedule_cmp(start)
                return
        self.set_play_icon("pause" if autoplay else "play")
        QTimer.singleShot(600, self.update_overlays)

    def _active_player(self):
        if self.mode == 1:
            return getattr(self, "mpv2", None)
        return getattr(self, "mpv", None)

    def _place_compare(self):
        pass

    def _place_vwin(self):
        pass

    def _hide_compare(self):
        pass

    def _begin_modal(self):
        pass

    def _end_modal(self):
        try:
            if self.kind == "video":
                self._sync_hosts()
        except Exception:
            pass

    def _drag_split(self, press_x, cur_x):
        pass

    def _cmp_seek(self, sec, autoplay=True):
        try:
            self._sync_state = 0
            self.mpv.set_speed(1.0)
            self.mpv2.set_speed(1.0)
            self.mpv.seek(sec)
            self.mpv2.seek(sec)
            self.mpv.set_pause(not autoplay)
            self.mpv2.set_pause(not autoplay)
        except Exception:
            pass

    def schedule_cmp(self, tsec):
        self._cmp_time = tsec
        if not hasattr(self, "_cmp_timer"):
            self._cmp_timer = QTimer(self)
            self._cmp_timer.setSingleShot(True)
            self._cmp_timer.timeout.connect(lambda: self.update_cmp(self._cmp_time))
        self._cmp_timer.start(180)

    def update_cmp(self, tsec):
        task = self.current_task()
        if task is None or self.mode != 2:
            return
        self._view_token = getattr(self, "_view_token", 0) + 1
        token = self._view_token
        res = self.find_result(task)
        src = task["path"]
        self.cmp.set_images(None, None)
        self.cmp._loading = True
        self.cmp.update()
        run_async(lambda: (self._load_preview_image(src, tsec, 900),
                           self._load_preview_image(res, tsec, 900) if res else None),
                  lambda pair, tok=token: self._show_cmp(pair, tok))

    def _show_result(self, img, token):
        if token != getattr(self, "_view_token", 0):
            return
        if img is None:
            self.lbl_result.setText("结果读取失败")
            return
        self.lbl_result.set_image(QPixmap.fromImage(img), getattr(self, "_res_info", ""))
        self.lbl_result.setText("")

    def _show_cmp(self, pair, token):
        if token != getattr(self, "_view_token", 0):
            return
        self.cmp._loading = False
        if not pair:
            self.cmp.set_images(None, None)
            return
        left_img, right_img = pair
        left = QPixmap.fromImage(left_img) if left_img is not None else QPixmap()
        right = QPixmap.fromImage(right_img) if right_img is not None else QPixmap()
        task = self.current_task()
        li = ri = ""
        if task is not None:
            li = self._img_info_text(task["path"])
            res = self.find_result(task)
            ri = self._img_info_text(res) if res else ""
        self.cmp.set_images(left, right, li, ri)

    # ---------- 播放 ----------
    def set_play_icon(self, state):
        name = {"play": "ic_play.png", "pause": "ic_pause.png", "replay": "ic_replay.png"}[state]
        try:
            self.btn_play.setIcon(QIcon(os.path.join(BASE, name)))
        except Exception:
            pass

    def toggle_play(self):
        if self.kind != "video":
            return
        if self.mode == 1 and not self.mpv2.attached:
            return
        if self.mode == 2 and not (self.mpv2.attached and self.mpv.attached):
            return
        if getattr(self, "_ended", False):
            self._ended = False
            self._cmp_seek(0.0, True) if self.mode == 2 else None
            if self.mode != 2:
                p = self._active_player()
                p.seek(0)
                p.set_pause(False)
            self.set_play_icon("pause")
            self._paused = False
            return
        p = self._active_player()
        if p is None:
            return
        now_paused = p.paused()
        self._user_paused = not now_paused
        p.set_pause(not now_paused)
        if self.mode == 2:
            self.mpv2.set_pause(not now_paused)
            self.mpv.set_pause(not now_paused)
        self._paused = not now_paused
        self.set_play_icon("play" if now_paused else "pause")

    def start_mpv(self, path, start=0.0, autoplay=True):
        self._pending = path
        self._ended = False
        self._last_pos = start
        QTimer.singleShot(60, lambda: self._start_now(path, start, autoplay=autoplay))

    def _start_now(self, path, start=0.0, tries=0, autoplay=True):
        try:
            if self.kind != "video":
                return
            self._sync_hosts()
            self.vhost.update()
            QApplication.processEvents()
            if not self.mpv.attached:
                self.mpv.attach(self.vhost.winId())
            self.mpv.load(path)
            self._loaded = path
            self._osd_info(self.mpv, path)
            self.mpv.seek(start)
            self._paused = not autoplay
            self.mpv.set_pause(not autoplay)
            self.set_play_icon("pause" if autoplay else "play")
            self.slider.setValue(int(start * 1000))
            if not getattr(self, "_embed_checked", False):
                self._embed_checked = True
                QTimer.singleShot(1500, self._check_embed)
            QTimer.singleShot(600, self.update_overlays)
        except Exception:
            pass

    def seek(self, v):
        """拖动时只记位置，停下 90ms 才真正下发，防止 seek 风暴"""
        row = self.list.currentRow()
        if row < 0 or row >= len(self.tasks) or self.kind != "video":
            return
        self._pending_seek = v / 1000.0
        self.lbl_time.setText(f"{fmt_t(v / 1000.0)} / {fmt_t(self.mpv.dur())}")
        if not hasattr(self, "_seek_timer"):
            self._seek_timer = QTimer(self)
            self._seek_timer.setSingleShot(True)
            self._seek_timer.timeout.connect(self._apply_seek)
        self._seek_timer.start(90)

    def _apply_seek(self):
        sec = getattr(self, "_pending_seek", None)
        if sec is None:
            return
        self._pending_seek = None
        try:
            if self.mode == 2 and self.mpv.attached:
                self.mpv.seek(sec)
                if self.mpv2.attached:
                    QTimer.singleShot(120, lambda: self.mpv2.seek(sec))
            else:
                p = self._active_player()
                if p is not None and p.attached:
                    p.seek(sec)
            self._last_pos = sec
            self._ended = False
        except Exception:
            pass

    def _check_embed(self):
        try:
            import ctypes
            u = ctypes.WinDLL("user32")
            CW = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            found = []
            def cb(h, lp):
                b = ctypes.create_unicode_buffer(64)
                u.GetClassNameW(h, b, 64)
                if b.value == "mpv":
                    found.append(h)
                return True
            u.EnumChildWindows(int(self.vhost.winId()), CW(cb), 0)
            if not found:
                self.write("内嵌播放不可用，改用系统播放器打开")
                row = self.list.currentRow()
                if row >= 0:
                    os.startfile(self.tasks[row]["path"])
        except Exception:
            pass


    # ---------- 处理 ----------
    def open_out(self):
        d = self.out_dir
        try:
            os.makedirs(d, exist_ok=True)
            os.startfile(d)
        except Exception as e:
            QMessageBox.information(self, "打不开目录", "%s\n%s" % (d, e))

    def choose_out(self):
        self._begin_modal()
        try:
            self._choose_out()
        finally:
            self._end_modal()

    def _choose_out(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录",
                                             self.txt_out.text() if os.path.isdir(self.txt_out.text()) else "")
        if d:
            self.txt_out.setText(d)
            key = "out_video" if self.kind == "video" else "out_image"
            self.app.cfg[key] = d
            save_cfg(self.app.cfg)

    def write(self, s):
        self.log.append(s)

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.tasks:
            QMessageBox.information(self, "提示", "先添加文件。")
            return
        os.makedirs(self.out_dir, exist_ok=True)
        self.stop_flag = False
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.worker = threading.Thread(target=self.work, daemon=True)
        self.worker.start()

    def cancel(self):
        self.stop_flag = True
        if self.proc:
            try:
                self.proc.terminate()
            except Exception:
                pass

    def ui(self, fn):
        self.app.q.put(fn)

    def status(self, text):
        self.ui(lambda: self.lbl_now.setText(text))

    def work(self):
        total = len(self.tasks)
        for i, t in enumerate(list(self.tasks)):
            if self.stop_flag:
                break
            k, m, scale, tile, dn, threads, fast = self.params()
            try:
                if self.kind == "image":
                    self.do_image(t, i, total, k, m, scale, tile, dn)
                else:
                    self.do_video(t, i, total, k, m, scale, tile, dn, threads, fast)
            except Exception as e:
                msg = str(e)[:60]
                self.ui(lambda i=i, msg=msg: self.set_row(i, "失败：" + msg, 0, "#f87171"))
        self.ui(lambda: self.btn_start.setEnabled(True))
        self.ui(lambda: self.btn_stop.setEnabled(False))
        self.ui(lambda: self.write("全部结束。"))

    def set_row(self, i, status, pct, color=None):
        if i < len(self.tasks):
            self.tasks[i]["status"] = status
            self.tasks[i]["pct"] = pct
            it = self.list.item(i)
            if it:
                it.setText(f"{self.tasks[i]['name']}   {status} {pct:.0f}%")
                if color:
                    it.setForeground(QColor(color))
        self.prog.setValue(int(pct))
        self.lbl_all.setText(f"{pct:.0f}%")

    def do_image(self, t, i, total, ek, model, scale, tile, dn):
        stem = os.path.splitext(t["name"])[0]
        outp = unique_path(os.path.join(self.out_dir, f"{stem}_{scale}x.png"))
        tmp = unique_path(os.path.join(self.out_dir, f".{stem}.tmp.png"))
        cmd, cwd = build_cmd(ek, model, t["path"], tmp, scale, tile, dn)
        self.ui(lambda: self.write(f"▶ {t['name']}  [{model['label']} ×{scale}]"))
        self.ui(lambda: self.set_row(i, "增强中", 0))
        p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             startupinfo=_si(), creationflags=CREATEFLAGS)
        self.proc = p
        for raw in iter(p.stdout.readline, b""):
            if self.stop_flag:
                p.terminate(); break
            line = raw.decode("utf-8", "replace")
            if "%" in line:
                try:
                    pct = float(line.strip().split("%")[0].split()[-1])
                    self.ui(lambda pct=pct: self.set_row(i, "增强中", pct))
                except Exception:
                    pass
        p.wait()
        self.proc = None
        if p.returncode != 0 and not self.stop_flag:
            raise RuntimeError(f"引擎返回 {p.returncode}")
        if not os.path.exists(tmp):
            raise RuntimeError("没有输出文件")
        chain = self.filters()
        if chain:
            rc, _ = run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", tmp, "-vf", chain, outp])
            if rc == 0:
                os.remove(tmp)
            else:
                os.replace(tmp, outp)
        else:
            os.replace(tmp, outp)
        self.ui(lambda: self.set_row(i, "完成", 100, "#4ade80"))
        self.ui(lambda: self.write("  ✔ " + outp))

    def probe(self, path):
        rc, txt = run([FFMPEG, "-hide_banner", "-i", path])
        import re
        dur = 0.0
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", txt)
        if m:
            dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        m = re.search(r"(\d+(?:\.\d+)?)\s*fps", txt)
        return (float(m.group(1)) if m else 25.0), dur

    def do_video(self, t, i, total, ek, model, scale, tile, dn, threads=None, fast=False):
        os.makedirs(TMP, exist_ok=True)
        outp = unique_path(os.path.join(self.out_dir, f"{os.path.splitext(t['name'])[0]}_{scale}x.mp4"))
        work = tempfile.mkdtemp(prefix="job_", dir=TMP)
        frames, up = os.path.join(work, "in"), os.path.join(work, "out")
        os.makedirs(frames); os.makedirs(up)
        fps, dur = self.probe(t["path"])
        try:
            self.ui(lambda: self.set_row(i, "抽帧中", 0))
            fext = "jpg" if fast else "png"
            p = subprocess.Popen([FFMPEG, "-y", "-i", t["path"], "-fps_mode", "passthrough",
                                  "-qscale:v", "2" if fast else "1",
                                  os.path.join(frames, "%08d." + fext)],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 startupinfo=_si(), creationflags=CREATEFLAGS)
            self.proc = p
            import re
            for raw in iter(p.stdout.readline, b""):
                if self.stop_flag:
                    p.terminate(); break
                m = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", raw.decode("utf-8", "replace"))
                if m and dur > 0:
                    sec = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
                    pct = min(99.0, sec / dur * 100 * 0.15)
                    self.ui(lambda pct=pct: self.set_row(i, "抽帧中", pct))
                    self.status("拆帧中 %d%%（%s / %s）" % (
                        int(sec / dur * 100), fmt_t(sec), fmt_t(dur)))
            p.wait(); self.proc = None
            n = len(os.listdir(frames))
            if n == 0:
                raise RuntimeError("抽帧失败")
            cmd, cwd = build_cmd(ek, model, frames, up, scale, tile, dn,
                                 fmt=fext, threads=threads)
            p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 startupinfo=_si(), creationflags=CREATEFLAGS)
            self.proc = p
            import re as _re
            last = 0.0
            for raw in iter(p.stdout.readline, b""):
                if self.stop_flag:
                    p.terminate(); break
                try:
                    done = len(os.listdir(up))
                except Exception:
                    done = 0
                frac = min(1.0, done / max(1, n))
                pct = 15 + frac * 80
                last = pct
                self.ui(lambda pct=pct: self.set_row(i, "增强中", pct))
                self.status("超分中（%d/%d 帧）" % (done, n))
            p.wait(); self.proc = None
            if last < 90 and not self.stop_flag:
                self.ui(lambda: self.set_row(i, "增强中", 95))
                self.status("超分收尾中…")
            if p.returncode != 0 and not self.stop_flag:
                raise RuntimeError("增强失败")
            vf = self.filters()
            mode = self.cmb_fps.currentIndex() if getattr(self, "cmb_fps", None) else 0
            mult = 2
            try:
                mult = int(self.cmb_mult.currentText().replace("×", "")) if getattr(self, "cmb_mult", None) else 2
            except Exception:
                mult = 2
            dedup = bool(getattr(self, "chk_dedup", None) and self.chk_dedup.isChecked())
            src_frames, out_fps = up, fps
            if mode in (2, 3) and RIFE:
                model = "rife-anime" if mode == 2 else "rife-v4.6"
                cur_in = up
                ok_all = True
                for step in range(max(0, mult - 1)):
                    nxt = os.path.join(work, "interp%d" % step)
                    os.makedirs(nxt, exist_ok=True)
                    self.ui(lambda s=step: self.set_row(i, "AI 插帧中 %d/%d" % (s + 1, mult - 1), 92))
                    self.status("AI 插帧中（第 %d/%d 轮）" % (step + 1, mult - 1))
                    rcmd = [RIFE, "-i", cur_in, "-o", nxt,
                            "-m", os.path.join(os.path.dirname(RIFE), model)]
                    try:
                        need = len(os.listdir(cur_in)) * 2
                    except Exception:
                        need = 0
                    rp = subprocess.Popen(rcmd, cwd=os.path.dirname(RIFE),
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                          startupinfo=_si(), creationflags=CREATEFLAGS)
                    self.proc = rp
                    while rp.poll() is None:
                        if self.stop_flag:
                            rp.terminate(); break
                        try:
                            got = len(os.listdir(nxt))
                        except Exception:
                            got = 0
                        self.status("AI 插帧中（第 %d/%d 轮，%d/%d 帧）" % (
                            step + 1, mult - 1, got, need))
                        self.ui(lambda g=got, nd=need: self.set_row(
                            i, "AI 插帧中", 92 + (g / max(1, nd)) * 3))
                        time.sleep(0.4)
                    rp.wait(); self.proc = None
                    if rp.returncode == 0 and os.listdir(nxt):
                        cur_in = nxt
                    else:
                        ok_all = False
                        break
                if ok_all and cur_in != up:
                    src_frames, out_fps = cur_in, fps * mult
                    self.ui(lambda: self.write("  · AI 插帧完成（%s ×%d）" % (model, mult)))
                else:
                    self.ui(lambda: self.write("  · AI 插帧失败，保持原帧率"))
            elif mode == 1:
                mi = ("minterpolate=fps=%d:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
                      % max(30, int(fps * mult)))
                vf = (vf + "," + mi) if vf else mi
            if dedup:
                dd = ("mpdecimate,minterpolate=fps=%d:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
                      "tpad=stop_mode=clone:stop_duration=3" % max(1, round(out_fps)))
                vf = (vf + "," + dd) if vf else dd
                self.ui(lambda: self.write("  · 已启用重复帧替换（去重后用插值补回）"))
            cmd = [FFMPEG, "-y", "-framerate", f"{max(1, round(out_fps, 3))}",
                   "-i", os.path.join(src_frames, "%08d." + fext),
                   "-i", t["path"], "-map", "0:v:0", "-map", "1:a:0?"]
            if vf:
                cmd += ["-vf", vf]
            enc = (self.app.cfg.get("encoder") or "cpu")
            crf_v = self.cmb_crf.currentText()
            preset = self.app.cfg.get("preset", "veryfast")
            enc_args = []
            if enc == "nvenc":
                p_map = {"ultrafast": "p1", "veryfast": "p4", "medium": "p7"}
                enc_args = ["-c:v", "h264_nvenc", "-preset", p_map.get(preset, "p4"),
                            "-rc", "vbr", "-cq", crf_v, "-b:v", "0"]
            elif enc == "amf":
                q_map = {"ultrafast": "speed", "veryfast": "balanced", "medium": "quality"}
                enc_args = ["-c:v", "h264_amf", "-quality", q_map.get(preset, "balanced"),
                            "-rc", "cqp", "-qp_i", crf_v, "-qp_p", crf_v]
            elif enc == "qsv":
                enc_args = ["-c:v", "h264_qsv", "-global_quality", crf_v, "-preset", preset]
            else:
                enc_args = ["-c:v", "libx264", "-crf", crf_v, "-preset", preset,
                            "-threads", "0", "-x264-params", "lookahead-threads=1"]
            cmd += enc_args
            cmd += [
                    "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest"]
            if dedup and dur > 0:
                cmd += ["-t", "%.3f" % dur]
            cmd.append(outp)
            try:
                total_frames = len(os.listdir(src_frames))
            except Exception:
                total_frames = n * max(1, mult)
            if mode == 1:
                total_frames = max(n, int(round(dur * fps * mult)))
            pc = subprocess.Popen(cmd[:1] + ["-progress", "pipe:1", "-nostats"] + cmd[1:],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  startupinfo=_si(), creationflags=CREATEFLAGS)
            self.proc = pc
            import re as _re2
            for raw in iter(pc.stdout.readline, b""):
                if self.stop_flag:
                    pc.terminate(); break
                line = raw.decode("utf-8", "replace").strip()
                if line.startswith("frame="):
                    try:
                        fr = int(line.split("=", 1)[1])
                    except Exception:
                        continue
                    frac = min(1.0, fr / max(1, total_frames))
                    pct = 96 + frac * 3.5
                    self.ui(lambda pct=pct: self.set_row(i, "合成中", pct))
                    self.status("合成中（%d/%d 帧）" % (fr, total_frames))
                elif line.startswith("progress=end"):
                    break
            pc.wait(); self.proc = None
            if pc.returncode != 0:
                raise RuntimeError("合成失败")
            self.status("写出文件完成")
            if not os.path.exists(outp):
                self.ui(lambda: self.write("  ⚠ 未生成文件：" + outp))
            self.ui(lambda: self.set_row(i, "完成", 100, "#4ade80"))
            self.status("完成：" + os.path.basename(outp))
            self.ui(lambda: self.write("  ✔ " + outp))
        finally:
            self.proc = None
            shutil.rmtree(work, ignore_errors=True)


class CropDialog(QDialog):
    """在图上框选一块作为背景显示区域"""

    def __init__(self, img_path, rect, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择背景显示区域")
        self.resize(900, 620)
        self.pix = QPixmap(img_path)
        self.sel = list(rect) if rect else [0.0, 0.0, 1.0, 1.0]
        self._start = None
        self.setStyleSheet("QDialog{background:#141518;}")

    def _fit(self):
        if self.pix.isNull():
            return QRect(0, 0, 1, 1)
        w, h = self.width() - 40, self.height() - 90
        pw, ph = self.pix.width(), self.pix.height()
        k = min(w / pw, h / ph)
        nw, nh = int(pw * k), int(ph * k)
        return QRect((self.width() - nw) // 2, 40, nw, nh)

    def _to_norm(self, pt):
        r = self._fit()
        x = max(0.0, min(1.0, (pt.x() - r.x()) / max(1, r.width())))
        y = max(0.0, min(1.0, (pt.y() - r.y()) / max(1, r.height())))
        return x, y

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(20, 21, 24))
        if self.pix.isNull():
            return
        r = self._fit()
        p.drawPixmap(r, self.pix)
        x, y, w, h = self.sel
        sel = QRect(int(r.x() + x * r.width()), int(r.y() + y * r.height()),
                    max(4, int(w * r.width())), max(4, int(h * r.height())))
        p.fillRect(r, QColor(0, 0, 0, 130))
        p.drawPixmap(sel, self.pix, QRect(int(x * self.pix.width()), int(y * self.pix.height()),
                                          max(1, int(w * self.pix.width())),
                                          max(1, int(h * self.pix.height()))))
        p.setPen(QPen(QColor(255, 255, 255, 230), 2))
        p.drawRect(sel)
        p.setPen(QColor(220, 225, 230))
        p.drawText(20, 26, "按住鼠标拖出一块区域，作为背景显示的部分")

    def mousePressEvent(self, e):
        self._start = self._to_norm(e.pos())

    def mouseMoveEvent(self, e):
        if self._start and e.buttons() & Qt.LeftButton:
            x1, y1 = self._start
            x2, y2 = self._to_norm(e.pos())
            self.sel = [min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)]
            self.update()

    def mouseReleaseEvent(self, e):
        if self.sel[2] < 0.05 or self.sel[3] < 0.05:
            self.sel = [0.0, 0.0, 1.0, 1.0]
        self._start = None
        self.update()


class SettingsDialog(QDialog):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.setWindowTitle("设置")
        self.resize(820, 640)
        self.setStyleSheet(QSS + "QDialog { background: #15161a; }"
                                 "QTabWidget::pane { border:1px solid rgba(255,255,255,25);"
                                 " border-radius:10px; background: rgba(255,255,255,8); }"
                                 "QTabBar::tab { background: rgba(255,255,255,28); color:#e8e9ea;"
                                 " padding:7px 22px; border-radius:8px; margin-right:6px; }"
                                 "QTabBar::tab:selected { background: rgba(79,140,255,220); color:#ffffff; }"
                                 "QTabBar::tab:hover { background: rgba(255,255,255,45); }")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 12)

        tabs = QTabWidget()
        lay.addWidget(tabs, 1)

        # ---- 外观 ----
        w_app = QWidget()
        la = QVBoxLayout(w_app)
        la.setContentsMargins(18, 16, 18, 16)
        la.setSpacing(8)
        la.addWidget(QLabel("主题色"))
        row = QHBoxLayout()
        for c in ["#4f8cff", "#7c5cff", "#00b8a9", "#f59e0b", "#ef4444", "#22c55e", "#64748b"]:
            b = QPushButton()
            b.setFixedSize(40, 28)
            b.setStyleSheet(f"background: {c}; border-radius: 7px; border: none;")
            b.clicked.connect(lambda _, c=c: self.pick(c))
            row.addWidget(b)
        row.addStretch()
        row.addWidget(QPushButton("自定义…", clicked=self.custom_color))
        la.addLayout(row)
        self.lbl_color = QLabel(f"当前：{app.cfg.get('accent')}")
        self.lbl_color.setObjectName("hint")
        la.addWidget(self.lbl_color)

        la.addSpacing(6)
        la.addWidget(QLabel("自定义背景图"))
        row2 = QHBoxLayout()
        row2.addWidget(QPushButton("选择图片…", clicked=self.choose_bg))
        row2.addWidget(QPushButton("选择显示区域…", clicked=self.choose_crop))
        row2.addWidget(QPushButton("恢复默认背景", clicked=self.reset_bg))
        row2.addStretch()
        la.addLayout(row2)
        self.lbl_bg = QLabel(app.cfg.get("bg") or "未设置")
        self.lbl_bg.setObjectName("hint")
        la.addWidget(self.lbl_bg)
        self.lbl_crop = QLabel(self._crop_text())
        self.lbl_crop.setObjectName("hint")
        la.addWidget(self.lbl_crop)

        la.addSpacing(6)
        la.addWidget(QLabel("背景虚化"))
        self.sl_blur = QSlider(Qt.Horizontal)
        self.sl_blur.setRange(0, 30)
        self.sl_blur.setValue(int(app.cfg.get("blur", 0)))
        la.addWidget(self.sl_blur)
        la.addWidget(QLabel("背景压暗（照片想保持原色就留 0）"))
        self.sl_dim = QSlider(Qt.Horizontal)
        self.sl_dim.setRange(0, 85)
        self.sl_dim.setValue(int(app.cfg.get("dim", 0)))
        la.addWidget(self.sl_dim)
        la.addStretch()
        tabs.addTab(w_app, "外观")

        # ---- 性能 ----
        w_pf = QWidget()
        lp = QVBoxLayout(w_pf)
        lp.setContentsMargins(18, 16, 18, 16)
        lp.setSpacing(8)
        lp.addWidget(QLabel("视频编码器"))
        self.cmb_enc = QComboBox()
        self.cmb_enc.addItems(["CPU · libx264（最稳，通用）",
                               "NVIDIA · NVENC（N 卡硬件编码）",
                               "AMD · AMF（A 卡硬件编码）",
                               "Intel · QSV（核显硬件编码）"])
        enc_map = {"cpu": 0, "nvenc": 1, "amf": 2, "qsv": 3}
        default_enc = app.cfg.get("encoder")
        if not default_enc:
            default_enc = {"nvidia": "nvenc", "amd": "amf", "intel": "qsv"}.get(GPU_VENDOR, "cpu")
        self.cmb_enc.setCurrentIndex(enc_map.get(default_enc, 0))
        lp.addWidget(self.cmb_enc)
        tip = QLabel("硬件编码快 3~5 倍，同码率画质略低于 CPU；\n"
                     "编码失败会自动退回 CPU 编码。当前显卡：%s" % (GPU_NAME or "未知"))
        tip.setObjectName("hint")
        lp.addWidget(tip)

        lp.addSpacing(8)
        lp.addWidget(QLabel("编码预设（越快画质略降）"))
        self.cmb_preset = QComboBox()
        self.cmb_preset.addItems(["均衡 · veryfast（推荐）", "画质优先 · medium", "极速 · ultrafast"])
        _pm = {"veryfast": 0, "medium": 1, "ultrafast": 2}
        self.cmb_preset.setCurrentIndex(_pm.get(app.cfg.get("preset", "veryfast"), 0))
        lp.addWidget(self.cmb_preset)

        lp.addSpacing(8)
        lp.addWidget(QLabel("视频渲染模式（预览黑屏时切换）"))
        self.cmb_vout = QComboBox()
        self.cmb_vout.addItems(["direct3d9", "direct3d11", "directdraw", "opengl"])
        self.cmb_vout.setCurrentText(app.cfg.get("vout", "direct3d9"))
        lp.addWidget(self.cmb_vout)
        lp.addStretch()
        tabs.addTab(w_pf, "性能")

        # ---- 通用 ----
        w_up = QWidget()
        lu = QVBoxLayout(w_up)
        lu.setContentsMargins(18, 16, 18, 16)
        lu.setSpacing(8)
        lu.addWidget(QLabel("版本更新"))
        info = QLabel("更新由作者统一推送，客户端不可修改更新地址。" if UPDATE_URL
                      else "当前版本尚未开启在线更新。")
        info.setObjectName("hint")
        info.setWordWrap(True)
        lu.addWidget(info)
        rowu = QHBoxLayout()
        btn_chk = QPushButton("立即检查更新", clicked=lambda: app.check_update(True))
        btn_chk.setEnabled(bool(UPDATE_URL))
        rowu.addWidget(btn_chk)
        rowu.addStretch()
        lu.addLayout(rowu)
        lu.addStretch()
        lu.addWidget(QLabel("当前版本：%s" % APP_VERSION))
        tabs.addTab(w_up, "通用")

        # ---- 底部按钮 ----
        bar = QHBoxLayout()
        bar.addStretch()
        bar.addWidget(QPushButton("取消", clicked=self.reject))
        ok = QPushButton("保存")
        ok.setObjectName("accent")
        ok.clicked.connect(self.save)
        bar.addWidget(ok)
        lay.addLayout(bar)

    def _crop_text(self):
        c = self.app.cfg.get("bg_crop") or [0, 0, 1, 1]
        if list(c) == [0, 0, 1, 1] or list(c) == [0.0, 0.0, 1.0, 1.0]:
            return "当前区域：整张图"
        return "当前区域：左 %.0f%% 上 %.0f%% 宽 %.0f%% 高 %.0f%%" % (
            c[0] * 100, c[1] * 100, c[2] * 100, c[3] * 100)

    def pick(self, c):
        self.app.cfg["accent"] = c
        self.lbl_color.setText(f"当前：{c}")

    def custom_color(self):
        c = QColorDialog.getColor(QColor(self.app.cfg["accent"]), self, "选择主题色")
        if c.isValid():
            self.pick(c.name())

    def choose_bg(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择背景图片", "", "图片 (*.png *.jpg *.jpeg *.bmp *.webp)")
        if f:
            self.app.cfg["bg"] = f
            self.app.cfg["bg_crop"] = [0, 0, 1, 1]
            self.lbl_bg.setText(f)
            self.lbl_crop.setText("当前区域：整张图")

    def choose_crop(self):
        path = self.app.cfg.get("bg") or ""
        if not path or not os.path.exists(path):
            QMessageBox.information(self, "提示", "先选一张背景图片。")
            return
        dlg = CropDialog(path, self.app.cfg.get("bg_crop") or [0, 0, 1, 1], self)
        dlg.exec_()
        self.app.cfg["bg_crop"] = [round(v, 4) for v in dlg.sel]
        self.lbl_crop.setText(self._crop_text())

    def reset_bg(self):
        self.app.cfg["bg"] = ""
        self.app.cfg["bg_crop"] = [0, 0, 1, 1]
        self.app.cfg["blur"] = 0
        self.app.cfg["dim"] = 0
        self.lbl_bg.setText("未设置")
        self.lbl_crop.setText("当前区域：整张图")
        self.sl_blur.setValue(0)
        self.sl_dim.setValue(0)

    def save(self):
        self.app.cfg["blur"] = self.sl_blur.value()
        self.app.cfg["dim"] = self.sl_dim.value()
        self.app.cfg["vout"] = self.cmb_vout.currentText()
        self.app.cfg["encoder"] = ["cpu", "nvenc", "amf", "qsv"][self.cmb_enc.currentIndex()]
        self.app.cfg["preset"] = ["veryfast", "medium", "ultrafast"][self.cmb_preset.currentIndex()]
        save_cfg(self.app.cfg)
        self.app.restyle()
        self.app.render_bg(force=True)
        self.accept()


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        try:
            self.setWindowIcon(QIcon(os.path.join(BASE, "icon.png")))
        except Exception:
            pass
        self.resize(1200, 840)
        self.cfg = load_cfg()
        self.q = queue.Queue()
        os.makedirs(TMP, exist_ok=True)

        self.bg = QLabel(self)
        self.bg.setScaledContents(True)
        self.bg.lower()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        head = QHBoxLayout()
        t = QLabel(APP)
        t.setObjectName("title")
        try:
            ic = QPixmap(os.path.join(BASE, "icon.png"))
            if not ic.isNull():
                ilab = QLabel()
                ilab.setPixmap(ic.scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                head.addWidget(ilab)
        except Exception:
            pass
        head.addWidget(t)
        head.addStretch()
        b1 = QPushButton("使用说明")
        b1.clicked.connect(self.help)
        b2 = QPushButton("设置")
        b2.clicked.connect(lambda: SettingsDialog(self).exec_())
        head.addWidget(b1)
        head.addWidget(b2)
        root.addLayout(head)

        tabs = QHBoxLayout()
        self.tab_i = QPushButton("图片超分")
        self.tab_v = QPushButton("视频超分")
        for b in (self.tab_i, self.tab_v):
            b.setCheckable(True)
            b.setMinimumWidth(110)
            tabs.addWidget(b)
        tabs.addStretch()
        self.tab_i.setChecked(True)
        self.tab_i.clicked.connect(lambda: self.switch(0))
        self.tab_v.clicked.connect(lambda: self.switch(1))
        root.addLayout(tabs)

        self.stack = QStackedWidget()
        self.panel_i = Panel(self, "image")
        self.panel_v = Panel(self, "video")
        self.stack.addWidget(self.panel_i)
        self.stack.addWidget(self.panel_v)
        root.addWidget(self.stack, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.pump)
        self.timer.start(90)

        QTimer.singleShot(1500, self.check_update)

        self.raise_timer = QTimer(self)
        self.raise_timer.timeout.connect(self._keep_video_on_top)
        self.raise_timer.start(700)
        self.installEventFilter(self)
        self.restyle()
        QTimer.singleShot(120, lambda: self.render_bg(force=True))

    def closeEvent(self, e):
        for name in ("panel_i", "panel_v"):
            pnl = getattr(self, name, None)
            if pnl is None:
                continue
            try:
                if getattr(pnl, "mpv", None):
                    pnl.mpv.destroy()
            except Exception:
                pass
            try:
                vwin = getattr(pnl, "vwin", None)
                if vwin is not None:
                    vwin.hide()
                    vwin.deleteLater()
            except Exception:
                pass
        super().closeEvent(e)

    def check_update(self, manual=False):
        url = (UPDATE_URL or "").strip()
        if not url:
            if manual:
                QMessageBox.information(self, "检查更新", "还没设置更新地址。\n在「设置」里填一个 JSON 清单地址即可。")
            return

        def work():
            try:
                info = fetch_update(url)
            except Exception:
                info = None
            self.q.put(lambda: self.show_update(info, manual))
        threading.Thread(target=work, daemon=True).start()

    def show_update(self, info, manual=False):
        if not info:
            if manual:
                QMessageBox.information(self, "检查更新", "检查失败，请稍后再试或检查网络。")
            return
        new_v = str(info.get("version", "")).strip()
        if not new_v or vtuple(new_v) <= vtuple(APP_VERSION):
            if manual:
                QMessageBox.information(self, "检查更新", f"已经是最新版本（{APP_VERSION}）。")
            return
        notes = (info.get("notes") or "").replace("\n", "<br>")
        link = info.get("url") or ""
        box = QMessageBox(self)
        box.setWindowTitle("发现新版本")
        box.setTextFormat(Qt.RichText)
        box.setText(
            f"<div style='font-size:11pt;line-height:160%'>"
            f"<b>Zsharp {new_v}</b> 已发布<br>"
            f"<span style='color:#9aa0a8'>你当前的版本：{APP_VERSION}</span>"
            + (f"<br><br><b>更新内容</b><br>{notes}" if notes else "")
            + "</div>")
        box.setStyleSheet("QMessageBox { background:#1b1c1f; } QLabel{ color:#e8e9ea; }")
        b_now = box.addButton("立即更新", QMessageBox.AcceptRole)
        box.addButton("稍后", QMessageBox.RejectRole)
        box.exec_()
        if box.clickedButton() is b_now and link:
            import webbrowser
            webbrowser.open(link)

    def _keep_video_on_top(self):
        for name in ("panel_i", "panel_v"):
            pnl = getattr(self, name, None)
            if pnl is None or getattr(pnl, "mode", 0) != 0:
                continue
            vwin = getattr(pnl, "vwin", None)
            if vwin is not None and vwin.isVisible():
                try:
                    vwin.raise_()
                except Exception:
                    pass

    def _sync_vwin(self):
        try:
            for name in ("panel_i", "panel_v"):
                pnl = getattr(self, name, None)
                if pnl is None or pnl is not self.stack.currentWidget():
                    continue
                try:
                    if getattr(pnl, "mode", 0) == 2 and getattr(pnl, "mpv2", None) and pnl.mpv2.attached:
                        pnl._place_compare()
                    elif getattr(pnl, "mode", 0) == 0 and getattr(pnl, "vwin", None) and pnl.vwin.isVisible():
                        pnl._place_vwin()
                except Exception:
                    pass
        except Exception:
            pass

    def moveEvent(self, e):
        super().moveEvent(e)
        self._queue_sync()

    def _queue_sync(self):
        # 窗口拖动/缩放期间先把视频窗口收起来，稳定后再摆回去，避免反复重建渲染表面
        try:
            for name in ("panel_i", "panel_v"):
                pnl = getattr(self, name, None)
                if pnl is None:
                    continue
                for wn in ("vwin", "vwin2", "handle"):
                    wd = getattr(pnl, wn, None)
                    if wd is not None and wd.isVisible():
                        wd.hide()
        except Exception:
            pass
        if not hasattr(self, "_sync_timer"):
            self._sync_timer = QTimer(self)
            self._sync_timer.setSingleShot(True)
            self._sync_timer.timeout.connect(self._sync_vwin)
        self._sync_timer.start(220)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.bg.setGeometry(self.rect())
        self._queue_sync()
        self.bg.setGeometry(self.rect())
        if not hasattr(self, "_t"):
            self._t = QTimer(self)
            self._t.setSingleShot(True)
            self._t.timeout.connect(lambda: self.render_bg(force=True))
        self._t.start(400)

    def restyle(self):
        acc = self.cfg.get("accent", "#4f8cff")
        qss = QSS.replace("79,140,255", "%d,%d,%d" % (int(acc[1:3], 16), int(acc[3:5], 16), int(acc[5:7], 16)))
        qss = qss.replace("100,160,255", "%d,%d,%d" % (min(255, int(acc[1:3], 16) + 20),
                                                       min(255, int(acc[3:5], 16) + 20),
                                                       min(255, int(acc[5:7], 16) + 20)))
        self.setStyleSheet(qss)

    def render_bg(self, force=False):
        path = self.cfg.get("bg") or ""
        # 固定渲染尺寸：窗口缩放时由 QLabel 直接缩放，避免每次 resize 重跑 ffmpeg
        w, h = 1600, 1000
        if not path or not os.path.exists(path):
            self.bg.setStyleSheet("background: #1b1c1f;")
            self.bg.setPixmap(QPixmap())
            return
        out = os.path.join(TMP, "bg_static.png")
        if force or not os.path.exists(out):
            c = self.cfg.get("bg_crop") or [0, 0, 1, 1]
            vf = (f"crop=iw*{c[2]}:ih*{c[3]}:iw*{c[0]}:ih*{c[1]},"
                  f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}")
            blur = int(self.cfg.get("blur", 0))
            dim = int(self.cfg.get("dim", 0))
            if blur > 0:
                vf += f",gblur=sigma={blur}"
            if dim > 0:
                vf += f",eq=brightness=-{dim/100:.2f}"
            subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", path,
                            "-vf", vf, "-frames:v", "1", out],
                           capture_output=True, startupinfo=_si(), creationflags=CREATEFLAGS)
        pm = QPixmap(out)
        if not pm.isNull():
            self.bg.setPixmap(pm)
            self.bg.setGeometry(self.rect())
            self.bg.lower()

    def switch(self, i):
        self.stack.setCurrentIndex(i)
        for k, b in enumerate((self.tab_i, self.tab_v)):
            b.setChecked(k == i)
        try:
            if i == 0 and getattr(self.panel_v, "vwin", None):
                self.panel_v.vwin.hide()
            elif i == 1 and getattr(self.panel_v, "vwin", None) and self.panel_v.mpv.attached:
                self.panel_v._place_vwin()
        except Exception:
            pass

    def pump(self):
        try:
            while True:
                fn = self.q.get_nowait()
                fn()
        except queue.Empty:
            pass

    def help(self):
        for pnl in (self.panel_i, self.panel_v):
            pnl._begin_modal()
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle("使用说明")
            dlg.resize(1040, 620)
            dlg.setStyleSheet("QDialog{background:#141518;} QTextBrowser{background:transparent;"
                              "border:none; color:#e9ebee; font-size:12pt;}")
            lay = QVBoxLayout(dlg)
            lay.setContentsMargins(18, 14, 18, 12)

            tb = QTextBrowser()
            tb.setOpenExternalLinks(True)
            tb.setHtml("""
<style>
  body { color:#e9ebee; font-size:11.5pt; line-height:170%; }
  h2 { color:#ffffff; margin:0 0 6px 0; }
  b { color:#ffffff; }
  .k { color:#7fb2ff; }
  code { color:#9ee6a8; }
  td { padding:2px 14px 2px 0; }
</style>
<h2>Zsharp 使用说明</h2>
<p style='color:#b9bec6;margin:0 0 10px 0'>图片 / 视频超分 + 插帧，全部在本机显卡上跑，不上传任何文件。</p>

<table width="100%"><tr><td width="50%" valign="top">
<b>① 放入素材</b><br>
拖文件或文件夹进窗口，或点「＋ 添加」。<br>
列表里 <b>Ctrl 加选</b>、<b>Shift 区间选</b>，按 <b>Backspace / Delete</b> 删除选中项（不用清空全部）。<br><br>

<b>② 选模型</b><br>
· 动漫 / 视频 · 快速 —— 日常首选<br>
· 动漫 · 高质量 —— 静态图、壁纸<br>
· 真人 / 实拍 —— 照片、实拍视频<br>
· Real-CUGAN —— 线条锐、降噪强，老番<br>
· waifu2x —— 低清小图补细节<br>
· RealSR（DF2K）—— 实拍最稳，不油腻<br>
· RealSR（去 JPEG）—— 压烂的网图先用它<br><br>

<b>③ 调画面</b><br>
超分后发灰是正常的，把<b>对比度 +10%、饱和度 +5%</b> 拉回来；<br>
锐化别超 40；清晰度是“大半径”锐化，想要通透感加 30~50。
</td><td width="50%" valign="top">
<b>④ 插帧（视频）</b><br>
· <b>方式</b>：关闭 / 光流 / RIFE 动漫 / RIFE 通用<br>
· <b>倍数</b>：2× / 3× / 4×（倍数越高越慢）<br>
· <b>替换重复帧</b>：先去重再用插值补回，专治番剧 12fps 平移<br><br>

<b>⑤ 开始处理</b><br>
输出默认在程序目录 <code>output</code> 下，可改。<br>
处理中可随时「停止」，已完成的文件保留。<br>
同名文件自动加 (1)、(2) 不会覆盖。<br><br>

<b>⑥ 三种预览</b><br>
· 原素材 —— 播原片<br>
· 超分后 —— 播放大后的成片<br>
· 左右对比 —— 左原片右成片并排播，中间白线可拖<br><br>

<b>⑦ 性能建议</b><br>
N 卡：切块 512 + 线程 2:4:4 + 快速模式<br>
A 卡 / 核显：切块 256 + 线程 1:2:2<br>
显存不足报错时：切块降到 128
</td></tr></table>

<p style='color:#8890a0;margin-top:10px;font-size:10.5pt'>
显卡要求：NVIDIA / AMD / Intel 核显，支持 Vulkan 即可，<b>不需要 CUDA</b>。<br>
崩溃排查：把 <code>%TEMP%\\zsharp_crash.txt</code> 发给作者。<br>
更新：在「设置」里填更新清单地址，启动时会自动检查新版本。
</p>
""")
            lay.addWidget(tb, 1)

            row = QHBoxLayout()
            row.addStretch()
            btn = QPushButton("知道了")
            btn.setObjectName("accent")
            btn.clicked.connect(dlg.accept)
            row.addWidget(btn)
            lay.addLayout(row)
            dlg.exec_()
        finally:
            for pnl in (self.panel_i, self.panel_v):
                pnl._end_modal()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        imgs, vids = [], []
        for url in e.mimeData().urls():
            p = url.toLocalFile()
            if os.path.isdir(p):
                for root, _, fs in os.walk(p):
                    for f in fs:
                        q = os.path.join(root, f)
                        ext = os.path.splitext(f)[1].lower()
                        (imgs if ext in IMG_EXT else vids if ext in VID_EXT else []).append(q)
            elif os.path.isfile(p):
                ext = os.path.splitext(p)[1].lower()
                (imgs if ext in IMG_EXT else vids if ext in VID_EXT else []).append(p)
        if imgs:
            self.switch(0)
            self.panel_i.add_paths(sorted(imgs))
        if vids:
            if not imgs:
                self.switch(1)
            self.panel_v.add_paths(sorted(vids))


def _install_crash_log():
    import traceback, faulthandler
    log = os.path.join(tempfile.gettempdir(), "zsharp_crash.txt")

    def hook(exc_type, exc, tb):
        try:
            with open(log, "a", encoding="utf-8") as f:
                f.write("\n=== %s ===\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
                traceback.print_exception(exc_type, exc, tb, file=f)
        except Exception:
            pass
    sys.excepthook = hook
    try:
        f = open(log, "a", encoding="utf-8")
        faulthandler.enable(file=f, all_threads=True)
    except Exception:
        pass


def main():
    _install_crash_log()
    if "--selftest" in sys.argv:
        sample = os.path.join(BIN, "realesrgan", "input.jpg")
        out = os.path.join(tempfile.gettempdir(), "qt_selftest.png")
        rc, _ = run([ESRGAN, "-i", sample, "-o", out, "-n", "realesr-animevideov3", "-s", "2", "-f", "png"],
                    cwd=os.path.dirname(ESRGAN))
        ok = rc == 0 and os.path.exists(out)
        open(os.path.join(tempfile.gettempdir(), "qt_selftest.txt"), "w", encoding="utf-8").write(
            f"rc={rc} ok={ok} esrgan={ESRGAN} ffmpeg={FFMPEG}")
        sys.exit(0 if ok else 2)
    try:
        with open(os.path.join(tempfile.gettempdir(), "zsharp_boot.txt"), "w", encoding="utf-8") as f:
            f.write(f"BASE={BASE}\nBIN={BIN}\nLIBMPV={LIBMPV}\nESRGAN={ESRGAN}\nFFMPEG={FFMPEG}\n")
    except Exception:
        pass
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    try:
        app.setWindowIcon(QIcon(os.path.join(BASE, "icon.png")))
    except Exception:
        pass
    win = Main()
    win.show()
    paths = [a for a in sys.argv[1:] if os.path.exists(a)]
    imgs = [a for a in paths if os.path.splitext(a)[1].lower() in IMG_EXT]
    vids = [a for a in paths if os.path.splitext(a)[1].lower() in VID_EXT]
    if imgs:
        win.switch(0)
        win.panel_i.add_paths(imgs)
    if vids:
        win.switch(1)
        win.panel_v.add_paths(vids)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
