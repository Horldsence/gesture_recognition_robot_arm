"""Gesture Recognition System - Robotic Arm Control with Accumulator."""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
from datetime import datetime
import cv2
from PIL import Image, ImageTk

from camera_handler import CameraHandler
from gesture_detector import GestureDetector
from serial_comm import SerialCommunicator


class PositionAccumulator:
    """Accumulate position based on gestures. Stop on serial error."""

    STEP_SIZE = 10

    def __init__(self):
        self.x = 0
        self.y = 0
        self.z = 500
        self.a = 0
        self._error = False

    def update(self, gesture):
        """Update position based on gesture. Skip if error."""
        if self._error:
            return False

        changed = False

        if gesture == GestureDetector.FORWARD:
            self.z = max(0, self.z - self.STEP_SIZE)
            changed = True
        elif gesture == GestureDetector.BACKWARD:
            self.z = min(1000, self.z + self.STEP_SIZE)
            changed = True
        elif gesture == GestureDetector.LEFT:
            self.x = max(-500, self.x - self.STEP_SIZE)
            changed = True
        elif gesture == GestureDetector.RIGHT:
            self.x = min(500, self.x + self.STEP_SIZE)
            changed = True
        elif gesture == GestureDetector.UP:
            self.y = min(500, self.y + self.STEP_SIZE)
            changed = True
        elif gesture == GestureDetector.DOWN:
            self.y = max(-500, self.y - self.STEP_SIZE)
            changed = True

        return changed

    def set_error(self, has_error):
        self._error = has_error

    def has_error(self):
        return self._error

    def reset(self):
        self.x = 0
        self.y = 0
        self.z = 500
        self.a = 0
        self._error = False

    def get(self):
        return self.x, self.y, self.z, self.a


class GestureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("手势识别 - 机械臂控制")
        self.root.geometry("950x700")

        self.camera = None
        self.detector = None
        self.serial = None
        self.accumulator = PositionAccumulator()

        self.running = False
        self.thread = None
        self.last_send_time = 0
        self.send_interval = 0.15

        self._setup_ui()
        self._log("系统初始化完成")
        self._log("点击 '开始' 启动摄像头")

    def _setup_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main = ttk.Frame(self.root, padding="10")
        main.grid(row=0, column=0, sticky="nwes")
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(1, weight=1)

        ttk.Label(
            main, text="手势识别系统 - 机械臂控制", font=("Helvetica", 14, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)

        cam_frame = ttk.LabelFrame(main, text="摄像头画面", padding="5")
        cam_frame.grid(row=1, column=0, padx=(0, 10), sticky="nwes")
        cam_frame.columnconfigure(0, weight=1)
        cam_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(cam_frame, width=640, height=480, bg="black")
        self.canvas.grid(row=0, column=0, sticky="nwes")

        self.status = ttk.Label(cam_frame, text="状态: 已停止")
        self.status.grid(row=1, column=0, pady=(5, 0), sticky=tk.W)

        gesture_frame = ttk.LabelFrame(cam_frame, text="当前手势", padding="5")
        gesture_frame.grid(row=2, column=0, pady=(5, 0), sticky=tk.W)

        self.gesture_label = ttk.Label(gesture_frame, text="--", font=("Helvetica", 12))
        self.gesture_label.grid(row=0, column=0)

        right = ttk.Frame(main)
        right.grid(row=1, column=1, sticky="nwes")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        ctrl = ttk.LabelFrame(right, text="控制", padding="10")
        ctrl.grid(row=0, column=0, pady=(0, 10), sticky="we")
        ctrl.columnconfigure(0, weight=1)
        ctrl.columnconfigure(1, weight=1)
        ctrl.columnconfigure(2, weight=1)

        self.start_btn = ttk.Button(ctrl, text="开始", command=self._start)
        self.start_btn.grid(row=0, column=0, padx=2, sticky="we")

        self.stop_btn = ttk.Button(
            ctrl, text="停止", command=self._stop, state=tk.DISABLED
        )
        self.stop_btn.grid(row=0, column=1, padx=2, sticky="we")

        ttk.Button(ctrl, text="复位", command=self._reset).grid(
            row=0, column=2, padx=2, sticky="we"
        )

        pos_frame = ttk.LabelFrame(right, text="位置 (累加)", padding="10")
        pos_frame.grid(row=1, column=0, pady=(0, 10), sticky="we")

        self.pos_labels = {}
        for i, (name, key, rng) in enumerate(
            [
                ("X", "x", "-500~500"),
                ("Y", "y", "-500~500"),
                ("Z", "z", "0~1000"),
                ("A", "a", "-180~180"),
            ]
        ):
            ttk.Label(pos_frame, text=f"{name}:").grid(row=i, column=0, sticky=tk.W)
            self.pos_labels[key] = ttk.Label(
                pos_frame, text="0", width=8, font=("Consolas", 10)
            )
            self.pos_labels[key].grid(row=i, column=1, sticky=tk.W, padx=(5, 0))
            ttk.Label(pos_frame, text=rng, foreground="gray").grid(
                row=i, column=2, sticky=tk.W, padx=(5, 0)
            )

        err_frame = ttk.Frame(pos_frame)
        err_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky=tk.W)

        self.error_label = ttk.Label(
            err_frame, text="", foreground="red", font=("Helvetica", 10, "bold")
        )
        self.error_label.grid(row=0, column=0)

        log_frame = ttk.LabelFrame(right, text="日志", padding="5")
        log_frame.grid(row=2, column=0, sticky="nwes")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, width=38, height=20, font=("Consolas", 9)
        )
        self.log_text.grid(row=0, column=0, sticky="nwes")
        self.log_text.config(state=tk.DISABLED)

        ttk.Button(right, text="清除日志", command=self._clear_log).grid(
            row=3, column=0, pady=(10, 0), sticky="we"
        )

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _update_pos(self, x, y, z, a):
        self.pos_labels["x"].config(text=str(x))
        self.pos_labels["y"].config(text=str(y))
        self.pos_labels["z"].config(text=str(z))
        self.pos_labels["a"].config(text=str(a))

    def _update_gesture(self, gesture):
        names = {
            GestureDetector.FORWARD: "向前 ↑",
            GestureDetector.BACKWARD: "向后 ↓",
            GestureDetector.LEFT: "向左 ←",
            GestureDetector.RIGHT: "向右 →",
            GestureDetector.UP: "向上 ↑",
            GestureDetector.DOWN: "向下 ↓",
            GestureDetector.NONE: "--",
        }
        self.gesture_label.config(text=names.get(gesture, "--"))

    def _update_error(self, has_error, msg=""):
        if has_error:
            self.error_label.config(text="⚠ 错误! 已停止累加")
            self.status.config(text="状态: 错误", foreground="red")
        else:
            self.error_label.config(text="")
            self.status.config(text="状态: 运行中", foreground="green")

    def _start(self):
        try:
            self._log("初始化组件...")

            self.camera = CameraHandler()
            self.camera.start()
            self._log("摄像头: 640x480")

            self.detector = GestureDetector()
            self._log("手势检测: MediaPipe")

            try:
                self.serial = SerialCommunicator()
                self._log("串口: /dev/tty0 @ 115200")
            except RuntimeError as e:
                self._log(f"警告: 串口失败 - {e}")
                self.serial = None

            self.accumulator.reset()
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.status.config(text="状态: 运行中", foreground="green")
            self._log("启动成功")

        except RuntimeError as e:
            self._log(f"错误: {e}")
            self._cleanup()

    def _stop(self):
        self._log("停止...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self._cleanup()

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status.config(text="状态: 已停止", foreground="black")
        self.gesture_label.config(text="--")
        self._update_error(False)
        self.canvas.delete("all")
        self.canvas.create_text(
            320, 240, text="已停止", fill="white", font=("Helvetica", 18)
        )
        self._log("已停止")

    def _reset(self):
        self.accumulator.reset()
        self._update_pos(0, 0, 500, 0)
        self._update_error(False)
        self._log("位置已复位")
        if self.serial:
            self.serial.clear_error()

    def _cleanup(self):
        if self.camera:
            self.camera.stop()
            self.camera = None
        if self.detector:
            self.detector.close()
            self.detector = None
        if self.serial:
            self.serial.close()
            self.serial = None

    def _loop(self):
        while self.running:
            try:
                if not self.camera or not self.detector:
                    time.sleep(0.1)
                    continue

                frame = self.camera.capture_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue

                frame, gesture, center, size = self.detector.process_frame(frame)

                self.root.after(0, lambda g=gesture: self._update_gesture(g))

                changed = self.accumulator.update(gesture)

                if changed:
                    x, y, z, a = self.accumulator.get()
                    self.root.after(0, lambda: self._update_pos(x, y, z, a))

                    now = time.time()
                    if now - self.last_send_time >= self.send_interval:
                        self.last_send_time = now
                        self._send_position(x, y, z, a)

                self.root.after(0, lambda f=frame: self._display(f))
                time.sleep(0.05)

            except Exception as e:
                self.root.after(0, lambda: self._log(f"错误: {e}"))
                time.sleep(0.1)

    def _send_position(self, x, y, z, a):
        if not self.serial:
            self.root.after(0, lambda: self._log(f"检测: X={x} Y={y} Z={z} A={a}"))
            return

        success, resp, frame_hex = self.serial.send_and_read(x, y, z, a)

        if success:
            self.accumulator.set_error(False)
            self.root.after(0, lambda: self._update_error(False))
            self.root.after(
                0, lambda: self._log(f"发送: X={x} Y={y} Z={z} A={a} | {resp}")
            )
        else:
            self.accumulator.set_error(True)
            self.root.after(0, lambda: self._update_error(True, resp))
            self.root.after(0, lambda: self._log(f"错误: {resp} | 停止累加"))

    def _display(self, frame):
        if frame is None:
            return
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
            if w > 1 and h > 1:
                img = img.resize((w, h), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            self.canvas._photo = photo
        except Exception:
            pass

    def on_close(self):
        self._stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = GestureApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
