import collections
import ctypes
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import av
import numpy as np
import sounddevice as sd
from PIL import Image, ImageTk

AUDIO_RATE = 48000
QUEUE_MAX = 400

BG = "#0a0c11"
PANEL = "#11141c"
RAISED = "#181d29"
HOVERC = "#242c40"
TRACK = "#252c42"
TEXT = "#eef1f8"
MUTED = "#8b93a8"
DIM = "#59617a"
ACC1 = "#8b7cff"
ACC2 = "#4dd6ff"
FONT = "Segoe UI"


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def mix(c1, c2, t):
    a, b = _rgb(c1), _rgb(c2)
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def round_rect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def _i_play(cv, x, y, s, c, level=0):
    cv.create_polygon(x - s * .42, y - s * .56, x + s * .52, y,
                      x - s * .42, y + s * .56, fill=c)


def _i_pause(cv, x, y, s, c, level=0):
    cv.create_rectangle(x - s * .38, y - s * .52, x - s * .08, y + s * .52, fill=c)
    cv.create_rectangle(x + s * .08, y - s * .52, x + s * .38, y + s * .52, fill=c)


def _i_stop(cv, x, y, s, c, level=0):
    round_rect(cv, x - s * .36, y - s * .36, x + s * .36, y + s * .36, 4, fill=c)


def _i_open(cv, x, y, s, c, level=0):
    cv.create_polygon(x - s * .50, y - s * .26, x - s * .16, y - s * .26,
                      x - s * .02, y - s * .10, x + s * .50, y - s * .10,
                      x + s * .50, y + s * .34, x - s * .50, y + s * .34, fill=c)


def _i_vol(cv, x, y, s, c, level=0.0):
    cv.create_polygon(x - s * .48, y - s * .14, x - s * .22, y - s * .14,
                      x - s * .04, y - s * .36, x - s * .04, y + s * .36,
                      x - s * .22, y + s * .14, x - s * .48, y + s * .14, fill=c)
    if level <= 0.001:
        cv.create_line(x + s * .12, y - s * .18, x + s * .40, y + s * .18,
                       fill=c, width=2, capstyle="round")
        cv.create_line(x + s * .40, y - s * .18, x + s * .12, y + s * .18,
                       fill=c, width=2, capstyle="round")
    else:
        r = s * (.28 + .28 * clamp(level, 0, 1))
        cv.create_arc((x + s * .00 - r * .55, y - r, x + s * .00 + r * .95, y + r),
                      start=-52, extent=104, style="arc", outline=c, width=2)
        if level > 0.55:
            r2 = r * 1.45
            cv.create_arc((x + s * .00 - r2 * .55, y - r2, x + s * .00 + r2 * .95, y + r2),
                          start=-52, extent=104, style="arc", outline=c, width=2)


def _i_fs(cv, x, y, s, c, level=0):
    d, l = s * .44, s * .26
    for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        px, py = x + dx * d, y + dy * d
        cv.create_line(px - dx * l, py, px, py, fill=c, width=2, capstyle="round")
        cv.create_line(px, py, px, py - dy * l, fill=c, width=2, capstyle="round")


ICONS = {"play": _i_play, "pause": _i_pause, "stop": _i_stop,
         "open": _i_open, "vol": _i_vol, "fs": _i_fs}


class GlowButton(tk.Canvas):
    def __init__(self, master, icon, size=38, command=None, base=PANEL):
        super().__init__(master, width=size, height=size, bg=base,
                         highlightthickness=0, cursor="hand2")
        self.icon = icon
        self.size = size
        self.base = base
        self.command = command
        self.level = 0.0
        self._h = 0.0
        self._press = False
        self._target = 0.0
        self._job = None
        self.bind("<Enter>", lambda e: self._to(1.0))
        self.bind("<Leave>", lambda e: self._to(0.0))
        self.bind("<ButtonPress-1>", self._down)
        self.bind("<ButtonRelease-1>", self._up)
        self.redraw()

    def set_icon(self, icon):
        self.icon = icon
        self.redraw()

    def set_level(self, lv):
        self.level = lv
        self.redraw()

    def _to(self, t):
        self._target = t
        if self._job is None:
            self._step()

    def _step(self):
        d = self._target - self._h
        if abs(d) < 0.03:
            self._h = self._target
            self._job = None
            self.redraw()
            return
        self._h += d * 0.3
        self.redraw()
        self._job = self.after(15, self._step)

    def _down(self, _e):
        self._press = True
        self.redraw()

    def _up(self, _e):
        if self._press and self.command:
            self.command()
        self._press = False
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.size
        glow = max(self._h, 0.35 if self._press else 0)
        round_rect(self, 2, 2, w - 2, w - 2, 10,
                   fill=mix(self.base, HOVERC, glow), outline="")
        col = mix(TEXT, ACC2, self._h * 0.85)
        ICONS[self.icon](self, w / 2, w / 2 + (1 if self._press else 0),
                         w * 0.34, col, self.level)


class Slider(tk.Canvas):
    def __init__(self, master, width=140, height=24, thick=4, command=None,
                 preview=None, base=PANEL):
        super().__init__(master, width=width, height=height, bg=base,
                         highlightthickness=0, cursor="hand2")
        self.thick = thick
        self.command = command
        self.preview = preview
        self.frac = 0.0
        self.hov = False
        self.drag = False
        self.enabled = True
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Enter>", lambda e: self._hov(True))
        self.bind("<Leave>", lambda e: self._hov(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._motion)
        self.bind("<ButtonRelease-1>", self._release)
        self.redraw()

    def set_frac(self, f):
        f = clamp(f, 0.0, 1.0)
        if not self.drag and abs(f - self.frac) > 1e-4:
            self.frac = f
            self.redraw()

    def set_enabled(self, en):
        self.enabled = en
        self.configure(cursor="hand2" if en else "arrow")
        self.redraw()

    def _hov(self, h):
        self.hov = h
        self.redraw()

    def _pos(self, e):
        w = self.winfo_width()
        pad = 10
        return clamp((e.x - pad) / max(w - pad * 2, 1), 0.0, 1.0)

    def _press(self, e):
        if not self.enabled:
            return
        self.drag = True
        self.frac = self._pos(e)
        if self.preview:
            self.preview(self.frac)
        self.redraw()

    def _motion(self, e):
        if not self.drag or not self.enabled:
            return
        self.frac = self._pos(e)
        if self.preview:
            self.preview(self.frac)
        self.redraw()

    def _release(self, _e):
        if not self.drag:
            return
        self.drag = False
        self.redraw()
        if self.enabled and self.command:
            self.command(self.frac)

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 20:
            return
        cy = h / 2
        pad = 10
        hot = self.hov or self.drag
        th = self.thick + (5 if hot else 0)
        x = pad + self.frac * (w - pad * 2)
        track = TRACK if self.enabled else mix(TRACK, BG, 0.4)
        round_rect(self, pad, cy - th / 2, w - pad, cy + th / 2, th / 2,
                   fill=track, outline="")
        n = max(16, int((x - pad) / 4))
        for i in range(n):
            t0 = i / n
            xa = pad + t0 * (x - pad)
            xb = pad + (i + 1) / n * (x - pad)
            col = mix(ACC1, ACC2, t0) if self.enabled else DIM
            self.create_rectangle(xa, cy - th / 2, xb + 0.5, cy + th / 2,
                                  fill=col, outline="")
        r = (8 if hot else 5) if self.enabled else 4
        col = TEXT if self.enabled else DIM
        self.create_oval(x - r, cy - r, x + r, cy + r,
                         fill=col, outline=mix(col, BG, 0.35))


class Player:
    def __init__(self, root):
        self.root = root
        root.title("HEVC Player")
        root.geometry("1024x640")
        root.minsize(760, 480)
        root.configure(bg=BG)

        self.container = None
        self.vstream = None
        self.astream = None
        self.duration = 0.0
        self.frame_dur = 1.0 / 30.0
        self.vfallback = 0.0

        self.gen = 0
        self.demux_thread = None
        self.eof = threading.Event()
        self.stopping = threading.Event()

        self.video_q = collections.deque()
        self.abuf = collections.deque()
        self.apos = 0
        self.buffered_samples = 0
        self.played_samples = 0
        self.seek_offset = 0.0
        self.skip_until = 0.0
        self.pending_show = False

        self.playing = False
        self.paused = False
        self.ended = False
        self.volume = 0.8
        self.last_vol = 0.8
        self.audio_ok = True

        self.current_frame = None
        self.photo = None
        self.img_id = None
        self.last_pump = time.monotonic()
        self.wall_t = 0.0

        self.osd_items = []
        self.osd_job = None
        self.hide_job = None
        self.click_job = None

        self.canvas = tk.Canvas(root, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda e: self._render_current())
        self.canvas.bind("<Button-1>", self._canvas_click)
        self.canvas.bind("<Double-Button-1>", self._canvas_double)

        self.chip = tk.Label(self.canvas, text="", bg="#141926", fg=ACC2,
                             font=(FONT, 9, "bold"), padx=12, pady=5)

        bar = tk.Frame(root, bg=PANEL)
        self.bar_frame = bar
        self.bar_hidden = False

        rowA = tk.Frame(bar, bg=PANEL)
        rowA.pack(fill=tk.X, padx=14, pady=(10, 0))
        self.lbl_cur = tk.Label(rowA, text="0:00", bg=PANEL, fg=TEXT,
                                font=(FONT, 10, "bold"), width=5, anchor="w")
        self.lbl_cur.pack(side=tk.LEFT)
        self.seek = Slider(rowA, height=26, thick=4, base=PANEL,
                           command=self._seek_release, preview=self._seek_preview)
        self.seek.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.seek.set_enabled(False)
        self.lbl_dur = tk.Label(rowA, text="0:00", bg=PANEL, fg=MUTED,
                                font=(FONT, 10), width=5, anchor="e")
        self.lbl_dur.pack(side=tk.LEFT)

        rowB = tk.Frame(bar, bg=PANEL)
        rowB.pack(fill=tk.X, padx=10, pady=(2, 12))
        self.btn_open = GlowButton(rowB, "open", 38, self.open_dialog)
        self.btn_open.pack(side=tk.LEFT, padx=(4, 6))
        self.btn_play = GlowButton(rowB, "play", 46, self.toggle_play,
                                   base=mix(PANEL, ACC1, 0.30))
        self.btn_play.pack(side=tk.LEFT, padx=6)
        self.btn_stop = GlowButton(rowB, "stop", 38, self.stop)
        self.btn_stop.pack(side=tk.LEFT, padx=6)

        spacer = tk.Frame(rowB, bg=PANEL)
        spacer.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.btn_vol = GlowButton(rowB, "vol", 36, self.toggle_mute, base=PANEL)
        self.btn_vol.set_level(self.volume)
        self.btn_vol.pack(side=tk.LEFT, padx=(0, 2))
        self.vols = Slider(rowB, width=110, height=24, thick=4, base=PANEL,
                           command=self._vol_release, preview=self._vol_live)
        self.vols.set_frac(self.volume)
        self.vols.pack(side=tk.LEFT, padx=(2, 10))
        self.btn_fs = GlowButton(rowB, "fs", 36, self.toggle_fullscreen)
        self.btn_fs.pack(side=tk.LEFT, padx=(0, 4))

        bar.pack(fill=tk.X)

        root.bind("<space>", lambda e: self.toggle_play())
        root.bind("<Left>", lambda e: self.nudge(-10))
        root.bind("<Right>", lambda e: self.nudge(10))
        root.bind("<Up>", lambda e: self.vol_nudge(0.05))
        root.bind("<Down>", lambda e: self.vol_nudge(-0.05))
        root.bind("<f>", lambda e: self.toggle_fullscreen())
        root.bind("<o>", lambda e: self.open_dialog())
        root.bind("<Escape>", lambda e: self.exit_fullscreen())
        root.bind("<q>", lambda e: self.quit())
        root.bind_all("<MouseWheel>", self._wheel)
        root.bind("<Motion>", self._activity)
        root.protocol("WM_DELETE_WINDOW", self.quit)

        try:
            root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
            for attr, val in ((20, 1), (33, 2)):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(ctypes.c_int(val)), 4)
        except Exception:
            pass

        try:
            self.stream = sd.OutputStream(samplerate=AUDIO_RATE, channels=2,
                                          dtype="float32", blocksize=0,
                                          callback=self._audio_cb)
            self.stream.start()
        except Exception:
            self.stream = None
            self.audio_ok = False

        self.root.after(15, self._pump)

        if len(sys.argv) > 1:
            self.root.after(50, lambda: self.open_file(sys.argv[1]))

    def open_dialog(self):
        path = filedialog.askopenfilename(
            title="Open video",
            filetypes=[("Media files", "*.mp4 *.mkv *.mov *.m4v *.ts *.hevc *.h265 *.avi *.webm"),
                       ("All files", "*.*")])
        if path:
            self.open_file(path)

    def open_file(self, path):
        self._teardown_media()
        try:
            container = av.open(path)
        except Exception as e:
            messagebox.showerror("HEVC Player", f"Could not open file:\n{e}")
            return

        v = next((s for s in container.streams.video), None)
        a = next((s for s in container.streams.audio), None)
        if v is None and a is None:
            messagebox.showerror("HEVC Player", "No playable streams found.")
            container.close()
            return

        if v is not None:
            try:
                v.thread_type = "AUTO"
            except Exception:
                pass
            if v.duration and v.time_base:
                self.duration = float(v.duration * v.time_base)
            try:
                self.frame_dur = 1.0 / float(v.average_rate)
            except Exception:
                self.frame_dur = 1.0 / 30.0
        elif container.duration:
            self.duration = container.duration / 1_000_000

        self.container = container
        self.vstream = v
        self.astream = a
        self.vfallback = 0.0
        self.eof.clear()
        self.video_q.clear()
        self.abuf.clear()
        self.apos = 0
        self.buffered_samples = 0
        self.played_samples = 0
        self.seek_offset = 0.0
        self.skip_until = 0.0
        self.wall_t = 0.0
        self.current_frame = None
        self.ended = False
        self.paused = False
        self.playing = True
        self.last_pump = time.monotonic()

        self.seek.set_enabled(self.duration > 0)
        self.lbl_dur.configure(text=self.fmt(self.duration))
        self.lbl_cur.configure(text="0:00")

        name = path.replace("\\", "/").rsplit("/", 1)[-1]
        self.root.title(f"HEVC Player  -  {name}")
        badge = ""
        if v is not None:
            fps = ""
            try:
                fps = f"  ·  {float(v.average_rate):.2f} fps"
            except Exception:
                pass
            badge = f"{v.codec_context.name.upper()}  ·  {v.width}×{v.height}{fps}"
        elif a is not None:
            badge = f"{a.codec_context.name.upper()}  ·  AUDIO"
        self.chip.configure(text=badge)
        if badge:
            self.chip.place(relx=1.0, y=14, x=-14, anchor="ne")
        else:
            self.chip.place_forget()

        self.btn_play.set_icon("pause")
        self._start_demux()
        self._activity()

    def _teardown_media(self):
        self.gen += 1
        t = self.demux_thread
        if t is not None and t.is_alive():
            t.join(timeout=1.0)
        if self.container is not None:
            try:
                self.container.close()
            except Exception:
                pass
        self.container = None
        self.vstream = None
        self.astream = None
        self.video_q.clear()
        self.abuf.clear()
        self.apos = 0
        self.buffered_samples = 0
        self.played_samples = 0
        self.current_frame = None

    def _start_demux(self):
        self.gen += 1
        self.eof.clear()
        self.demux_thread = threading.Thread(target=self._demux_loop,
                                             args=(self.gen,), daemon=True)
        self.demux_thread.start()

    def _demux_loop(self, gen):
        try:
            streams = [s for s in (self.vstream, self.astream) if s is not None]
            resamp = None
            if self.astream is not None and self.audio_ok:
                resamp = av.AudioResampler(format="s16", layout="stereo",
                                           rate=AUDIO_RATE)
            for frame in self.container.decode(*streams):
                if gen != self.gen or self.stopping.is_set():
                    return
                if isinstance(frame, av.VideoFrame):
                    pts = frame.time
                    if pts is None:
                        pts = self.vfallback
                        self.vfallback += self.frame_dur
                    self._put(self.video_q, (pts, frame), gen)
                elif isinstance(frame, av.AudioFrame) and resamp is not None:
                    out = resamp.resample(frame)
                    if isinstance(out, av.AudioFrame):
                        out = [out]
                    for af in out:
                        data = af.to_ndarray().reshape(-1).astype(np.float32) / 32768.0
                        self._put_audio(data.reshape(-1, 2), gen)
        except Exception:
            pass
        finally:
            if gen == self.gen:
                self.eof.set()

    def _put(self, q, item, gen):
        while len(q) >= QUEUE_MAX:
            if gen != self.gen or self.stopping.is_set():
                return
            time.sleep(0.01)
        q.append(item)

    def _put_audio(self, pcm, gen):
        while self.buffered_samples > AUDIO_RATE * 2:
            if gen != self.gen or self.stopping.is_set():
                return
            time.sleep(0.01)
        self.abuf.append(pcm)
        self.buffered_samples += len(pcm)

    def _audio_cb(self, outdata, frames, t_info, status):
        if self.paused or self.stopping.is_set() or not self.playing:
            outdata.fill(0)
            return
        filled = 0
        while filled < frames:
            if not self.abuf:
                break
            chunk = self.abuf[0]
            n = min(len(chunk) - self.apos, frames - filled)
            outdata[filled:filled + n] = chunk[self.apos:self.apos + n] * self.volume
            self.apos += n
            filled += n
            self.played_samples += n
            self.buffered_samples -= n
            if self.apos >= len(chunk):
                self.abuf.popleft()
                self.apos = 0
        if filled < frames:
            outdata[filled:] = 0

    def _clock(self):
        if self.astream is not None and self.audio_ok:
            return self.played_samples / AUDIO_RATE + self.seek_offset
        return self.wall_t

    def _pump(self):
        if self.stopping.is_set():
            return
        now = time.monotonic()
        dt = now - self.last_pump
        self.last_pump = now
        if self.playing and not self.paused:
            self.wall_t += dt
        self._drain_video()
        self._update_bar()
        if (self.playing and not self.paused and self.eof.is_set()
                and not self.video_q and self.buffered_samples <= 0):
            self.playing = False
            self.ended = True
            self.btn_play.set_icon("play")
            self._activity()
        self.root.after(15, self._pump)

    def _drain_video(self):
        if self.vstream is None:
            return
        if self.pending_show:
            while self.video_q:
                ft, fr = self.video_q[0]
                if ft < self.skip_until - 0.02:
                    self.video_q.popleft()
                    continue
                self.current_frame = fr
                self.video_q.popleft()
                self.pending_show = False
                self._render_current()
                break
            return
        if not (self.playing and not self.paused):
            return
        clock = self._clock()
        shown = False
        while self.video_q:
            ft, fr = self.video_q[0]
            if ft <= clock + 0.005:
                self.video_q.popleft()
                self.current_frame = fr
                shown = True
            else:
                break
        if shown:
            self._render_current()

    def _render_current(self):
        if self.current_frame is None:
            return
        cw = max(self.canvas.winfo_width(), 64)
        ch = max(self.canvas.winfo_height(), 64)
        try:
            arr = self.current_frame.to_ndarray(format="rgb24")
        except Exception:
            return
        pil = Image.fromarray(arr)
        iw, ih = pil.size
        s = min(cw / iw, ch / ih)
        nw, nh = max(1, int(iw * s)), max(1, int(ih * s))
        if (nw, nh) != (iw, ih):
            pil = pil.resize((nw, nh), Image.BILINEAR)
        self.photo = ImageTk.PhotoImage(pil)
        if self.img_id is None:
            self.img_id = self.canvas.create_image(cw // 2, ch // 2, image=self.photo)
        else:
            self.canvas.itemconfig(self.img_id, image=self.photo)
            self.canvas.coords(self.img_id, cw // 2, ch // 2)
        self.canvas.tag_lower(self.img_id)

    def _update_bar(self):
        if self.duration <= 0 or self.seek.drag:
            return
        t = clamp(self._clock(), 0.0, self.duration)
        self.seek.set_frac(t / self.duration)
        self.lbl_cur.configure(text=self.fmt(t))

    @staticmethod
    def fmt(t):
        t = max(int(t), 0)
        return f"{t // 60}:{t % 60:02d}"

    def toggle_play(self):
        if self.container is None:
            self.open_dialog()
            return
        if self.ended:
            self.ended = False
            self.seek(0.0)
            self.playing = True
            self.paused = False
            self.last_pump = time.monotonic()
            self.btn_play.set_icon("pause")
        else:
            self.paused = not self.paused
            self.btn_play.set_icon("play" if self.paused else "pause")
            self._osd(glyph="play" if self.paused else "pause")
        self._activity()

    def _canvas_click(self, _e):
        if self.container is None or self.click_job is not None:
            return
        self.click_job = self.root.after(230, self._click_fire)

    def _canvas_double(self, _e):
        if self.click_job is not None:
            try:
                self.root.after_cancel(self.click_job)
            except Exception:
                pass
            self.click_job = None
        self.toggle_fullscreen()

    def _click_fire(self):
        self.click_job = None
        self.toggle_play()

    def stop(self):
        if self.container is None:
            return
        self.playing = False
        self.paused = False
        self.ended = False
        self.btn_play.set_icon("play")
        self.seek_time(0.0)

    def nudge(self, d):
        if self.container is None or self.duration <= 0:
            return
        self.ended = False
        self.seek_time(clamp(self._clock() + d, 0.0, self.duration))
        self._osd(text=f"{'+' if d >= 0 else ''}{int(d)}s")

    def vol_nudge(self, d):
        self.set_volume(self.volume + d, osd=True)

    def set_volume(self, v, osd=False):
        self.volume = clamp(v, 0.0, 1.0)
        self.vols.set_frac(self.volume)
        self.btn_vol.set_level(self.volume)
        if self.volume > 0.001:
            self.last_vol = self.volume
        if osd:
            self._osd(text=f"{int(round(self.volume * 100))}%")

    def toggle_mute(self):
        if self.volume > 0.001:
            self.set_volume(0.0, osd=True)
        else:
            self.set_volume(self.last_vol if self.last_vol > 0.05 else 0.6, osd=True)

    def seek_time(self, t):
        if self.container is None:
            return
        t = clamp(t, 0.0, max(self.duration, 0.0))
        self.gen += 1
        th = self.demux_thread
        if th is not None and th.is_alive():
            th.join(timeout=0.5)
        if self.stream is not None:
            self.stream.stop()
        self.video_q.clear()
        self.abuf.clear()
        self.apos = 0
        self.buffered_samples = 0
        self.played_samples = 0
        self.seek_offset = t
        self.skip_until = t
        self.wall_t = t
        self.vfallback = t
        self.eof.clear()
        self.pending_show = True
        try:
            self.container.seek(int(t * 1_000_000), backward=True)
        except Exception:
            pass
        if self.stream is not None:
            self.stream.start()
        self._start_demux()
        self.lbl_cur.configure(text=self.fmt(t))
        self._activity()

    def _seek_preview(self, frac):
        if self.duration <= 0:
            return
        t = frac * self.duration
        self.lbl_cur.configure(text=self.fmt(t))

    def _seek_release(self, frac):
        if self.duration <= 0:
            return
        self.seek_time(frac * self.duration)

    def _vol_live(self, frac):
        self.set_volume(frac)

    def _vol_release(self, frac):
        self.set_volume(frac, osd=True)

    def toggle_fullscreen(self):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))
        self._activity()

    def exit_fullscreen(self):
        self.root.attributes("-fullscreen", False)
        self._activity()

    def _activity(self, _e=None):
        if self.hide_job is not None:
            try:
                self.root.after_cancel(self.hide_job)
            except Exception:
                pass
            self.hide_job = None
        fs = bool(self.root.attributes("-fullscreen"))
        self.bar_pack()
        self.root.configure(cursor="")
        if fs and self.playing and not self.paused:
            self.hide_job = self.root.after(2200, self._hide_controls)

    def bar_visible(self):
        return not self.bar_hidden

    def bar_pack(self):
        if not self.bar_hidden:
            return
        self.bar_hidden = False
        try:
            self.bar_frame.pack(fill=tk.X)
        except Exception:
            pass

    def _hide_controls(self):
        self.hide_job = None
        if (bool(self.root.attributes("-fullscreen")) and self.playing
                and not self.paused):
            try:
                self.bar_frame.pack_forget()
                self.bar_hidden = True
            except Exception:
                pass
            self.root.configure(cursor="none")

    def _wheel(self, e):
        self.vol_nudge(0.05 if e.delta > 0 else -0.05)

    def _osd_cancel(self):
        if self.osd_job is not None:
            try:
                self.root.after_cancel(self.osd_job)
            except Exception:
                pass
            self.osd_job = None
        for it in self.osd_items:
            try:
                self.canvas.delete(it)
            except Exception:
                pass
        self.osd_items = []

    def _osd(self, text=None, glyph=None):
        cv = self.canvas
        self._osd_cancel()
        cw = max(cv.winfo_width(), 64)
        ch = max(cv.winfo_height(), 64)
        cx, cy = cw // 2, ch // 2
        r = int(min(cw, ch) * 0.09)
        ring = cv.create_oval(cx - r, cy - r, cx + r, cy + r,
                              outline=ACC2, width=3)
        parts = [ring]
        if glyph == "play":
            g = cv.create_polygon(cx - r * .35, cy - r * .52, cx + r * .48, cy,
                                  cx - r * .35, cy + r * .52, fill=TEXT)
            parts.append(g)
        elif glyph == "pause":
            g1 = cv.create_rectangle(cx - r * .42, cy - r * .5, cx - r * .1,
                                     cy + r * .5, fill=TEXT)
            g2 = cv.create_rectangle(cx + r * .1, cy - r * .5, cx + r * .42,
                                     cy + r * .5, fill=TEXT)
            parts += [g1, g2]
        elif text is not None:
            g = cv.create_text(cx, cy, text=text, fill=TEXT,
                               font=(FONT, 20, "bold"))
            parts.append(g)
        else:
            return
        self.osd_items = parts
        steps = 12

        def fade(k):
            t = k / steps
            ring_col = mix(ACC2, BG, t)
            txt_col = mix(TEXT, BG, t)
            cv.itemconfig(ring, outline=ring_col)
            for p in parts[1:]:
                try:
                    cv.itemconfig(p, fill=txt_col)
                except Exception:
                    pass
            if k < steps:
                self.osd_job = cv.after(28, lambda: fade(k + 1))
            else:
                self._osd_cancel()

        self.osd_job = cv.after(350, lambda: fade(1))

    def quit(self):
        self.stopping.set()
        self.gen += 1
        if self.stream is not None:
            try:
                self.stream.close()
            except Exception:
                pass
        if self.container is not None:
            try:
                self.container.close()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    Player(root)
    root.mainloop()


if __name__ == "__main__":
    main()
