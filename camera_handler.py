"""PiCamera2 capture module for Raspberry Pi."""

import numpy as np
import cv2

try:
    from picamera2 import Picamera2

    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False


class CameraHandler:
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        self.camera = None
        self._running = False

    def start(self):
        if not PICAMERA2_AVAILABLE:
            raise RuntimeError(
                "picamera2 not available. Install: pip install picamera2"
            )

        self.camera = Picamera2()
        config = self.camera.create_preview_configuration(
            main={"format": "RGB888", "size": (self.width, self.height)}
        )
        self.camera.configure(config)
        self.camera.start()
        self._running = True

    def capture_frame(self):
        if not self._running or self.camera is None:
            return None
        frame_rgb = self.camera.capture_array()
        return cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

    def stop(self):
        if self.camera:
            self.camera.stop()
            self.camera = None
        self._running = False

    def is_running(self):
        return self._running
