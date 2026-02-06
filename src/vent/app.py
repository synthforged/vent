import math
import threading
from ctypes import CDLL

# Preload layer-shell before gi imports
CDLL("libgtk4-layer-shell.so")

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio

gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gtk4LayerShell as LayerShell

from .state import State
from .audio import Recorder, NUM_BARS
from .transcriber import transcribe
from .output import output_text

FPS = 30
TIMER_MS = 1000 // FPS

# Colors
BG = (0.90, 0.90, 0.92, 0.80)
BG_PAUSED = (0.92, 0.57, 0.07, 0.85)  # warm amber
FG = (0.10, 0.10, 0.12, 0.9)
FG_RECORDING = (0.72, 0.12, 0.12, 0.9)  # deep crimson
FG_TRANSCRIBING = (0.04, 0.45, 0.22, 0.9)  # deep emerald


class VentApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="forged.vent.overlay", flags=Gio.ApplicationFlags.FLAGS_NONE)
        self._state = State.IDLE
        self._recorder = Recorder()
        self._timer_id: int | None = None
        self._dot_frame = 0
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        win = Gtk.Window(application=self)
        win.set_decorated(False)

        # Layer shell: bottom-center, 100px from bottom
        LayerShell.init_for_window(win)
        LayerShell.set_layer(win, LayerShell.Layer.OVERLAY)
        LayerShell.set_namespace(win, "vent")
        LayerShell.set_anchor(win, LayerShell.Edge.BOTTOM, True)
        LayerShell.set_margin(win, LayerShell.Edge.BOTTOM, 50)
        LayerShell.set_exclusive_zone(win, 0)
        LayerShell.set_keyboard_mode(win, LayerShell.KeyboardMode.ON_DEMAND)

        # Drawing area as the pill — all rendering done in cairo
        self._canvas = Gtk.DrawingArea()
        self._canvas.set_content_width(72)
        self._canvas.set_content_height(24)
        self._canvas.set_draw_func(self._draw)
        self._canvas.set_focusable(True)

        # Left-click: start/stop recording
        click = Gtk.GestureClick()
        click.set_button(1)
        click.connect("pressed", lambda g, n, x, y: self._on_click())
        self._canvas.add_controller(click)

        # Right-click: pause/resume while recording
        rclick = Gtk.GestureClick()
        rclick.set_button(3)
        rclick.connect("pressed", lambda g, n, x, y: self._on_right_click())
        self._canvas.add_controller(rclick)

        # Keyboard shortcuts
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key)
        win.add_controller(key_ctrl)

        win.set_child(self._canvas)
        win.present()

    def _on_key(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_q:
            self.quit()
            return True
        return False

    def _set_state(self, new_state: State):
        self._state = new_state
        if new_state == State.TRANSCRIBING:
            self._dot_frame = 0
        self._canvas.queue_draw()

    def _on_click(self):
        if self._state == State.IDLE:
            if not self._recorder.start():
                return
            self._set_state(State.RECORDING)
            self._timer_id = GLib.timeout_add(TIMER_MS, self._tick)
        elif self._state in (State.RECORDING, State.PAUSED):
            audio = self._recorder.stop()
            self._set_state(State.TRANSCRIBING)
            thread = threading.Thread(target=self._transcribe_worker, args=(audio,), daemon=True)
            thread.start()
        # Ignore clicks during TRANSCRIBING

    def _on_right_click(self):
        if self._state == State.RECORDING:
            self._recorder.pause()
            self._set_state(State.PAUSED)
        elif self._state == State.PAUSED:
            self._recorder.resume()
            self._set_state(State.RECORDING)

    def _transcribe_worker(self, audio):
        text = transcribe(audio)
        GLib.idle_add(self._on_transcription_done, text)

    def _on_transcription_done(self, text: str):
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        if text:
            output_text(text)
        self._set_state(State.IDLE)
        return False

    def _tick(self) -> bool:
        if self._state == State.TRANSCRIBING:
            self._dot_frame += 1
        self._canvas.queue_draw()
        return True

    def _draw(self, area, cr, width, height):
        # Draw pill background
        r = min(12, height / 2)
        self._rounded_rect(cr, 0, 0, width, height, r)
        cr.set_source_rgba(*(BG_PAUSED if self._state == State.PAUSED else BG))
        cr.fill()

        # Draw state content
        if self._state == State.IDLE:
            self._draw_idle_dot(cr, width, height)
        elif self._state == State.RECORDING:
            self._draw_bars(cr, width, height)
        elif self._state == State.PAUSED:
            self._draw_pause_icon(cr, width, height)
        elif self._state == State.TRANSCRIBING:
            self._draw_pulsing_dots(cr, width, height)

    def _draw_idle_dot(self, cr, w, h):
        cr.set_source_rgba(*FG)
        cr.arc(w / 2, h / 2, 4, 0, 2 * math.pi)
        cr.fill()

    def _draw_pause_icon(self, cr, w, h):
        cr.set_source_rgba(*FG)
        bar_w, bar_h = 3, 10
        gap = 5
        x0 = (w - 2 * bar_w - gap) / 2
        y0 = (h - bar_h) / 2
        cr.rectangle(x0, y0, bar_w, bar_h)
        cr.fill()
        cr.rectangle(x0 + bar_w + gap, y0, bar_w, bar_h)
        cr.fill()

    def _draw_bars(self, cr, w, h):
        levels = self._recorder.get_levels()
        bar_w = 4
        gap = 3
        total_w = NUM_BARS * bar_w + (NUM_BARS - 1) * gap
        x0 = (w - total_w) / 2
        max_h = h - 6
        cr.set_source_rgba(*FG_RECORDING)
        for i, level in enumerate(levels):
            bar_h = max(3, level * max_h)
            x = x0 + i * (bar_w + gap)
            y = (h - bar_h) / 2
            self._rounded_rect(cr, x, y, bar_w, bar_h, 2)
            cr.fill()

    def _draw_pulsing_dots(self, cr, w, h):
        n_dots = 3
        gap = 10
        total_w = n_dots * 6 + (n_dots - 1) * gap
        x0 = (w - total_w) / 2
        for i in range(n_dots):
            phase = (self._dot_frame / FPS * 2 + i * 0.4) % 1.0
            alpha = 0.6 + 0.4 * abs(math.sin(phase * math.pi))
            cr.set_source_rgba(FG_TRANSCRIBING[0], FG_TRANSCRIBING[1], FG_TRANSCRIBING[2], alpha)
            cx = x0 + i * (6 + gap) + 3
            cr.arc(cx, h / 2, 3, 0, 2 * math.pi)
            cr.fill()

    @staticmethod
    def _rounded_rect(cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()


def run():
    app = VentApp()
    app.run(None)
