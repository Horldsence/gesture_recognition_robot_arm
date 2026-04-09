"""MediaPipe gesture detection with directional control."""

import cv2
import numpy as np
import math
import time

try:
    import mediapipe as mp

    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False


class GestureDetector:
    """Detect hand gestures: forward/backward/left/right/up/down."""

    FORWARD = "forward"
    BACKWARD = "backward"
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    NONE = "none"

    def __init__(self, detection_confidence=0.6, tracking_confidence=0.5):
        if not MEDIAPIPE_AVAILABLE:
            raise RuntimeError(
                "mediapipe not available. Install: pip install mediapipe"
            )

        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )

        self.prev_center = None
        self.prev_palm_size = None
        self.prev_time = time.time()
        self.history = []
        self.history_size = 5
        self.movement_threshold = 0.02
        self.size_threshold = 0.05

    def process_frame(self, frame):
        """Detect hand and determine directional gesture.

        Returns: (frame, gesture, center_pos, palm_size)
        """
        if frame is None:
            return None, self.NONE, None, None

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        gesture = self.NONE
        center = None
        palm_size = None

        if results.multi_hand_landmarks:
            for hand in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    frame,
                    hand,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_styles.get_default_hand_landmarks_style(),
                    self.mp_styles.get_default_hand_connections_style(),
                )

                landmarks = hand.landmark
                wrist = landmarks[0]
                middle_mcp = landmarks[9]

                center = ((wrist.x + middle_mcp.x) / 2, (wrist.y + middle_mcp.y) / 2)
                palm_size = math.sqrt(
                    (middle_mcp.x - wrist.x) ** 2 + (middle_mcp.y - wrist.y) ** 2
                )

                gesture = self._detect_direction(center, palm_size)

        return frame, gesture, center, palm_size

    def _detect_direction(self, center, palm_size):
        """Detect directional gesture based on movement."""
        current_time = time.time()
        dt = current_time - self.prev_time

        if dt < 0.1:
            return self.NONE

        if self.prev_center is None or self.prev_palm_size is None:
            self.prev_center = center
            self.prev_palm_size = palm_size
            self.prev_time = current_time
            return self.NONE

        dx = center[0] - self.prev_center[0]
        dy = center[1] - self.prev_center[1]
        size_change = palm_size - self.prev_palm_size

        self.history.append((dx, dy, size_change, dt))
        if len(self.history) > self.history_size:
            self.history.pop(0)

        avg_dx = sum(h[0] for h in self.history) / len(self.history)
        avg_dy = sum(h[1] for h in self.history) / len(self.history)
        avg_size = sum(h[2] for h in self.history) / len(self.history)

        self.prev_center = center
        self.prev_palm_size = palm_size
        self.prev_time = current_time

        if avg_size > self.size_threshold:
            return self.BACKWARD
        if avg_size < -self.size_threshold:
            return self.FORWARD

        abs_x = abs(avg_dx)
        abs_y = abs(avg_dy)

        if abs_x > abs_y and abs_x > self.movement_threshold:
            return self.LEFT if avg_dx < 0 else self.RIGHT

        if abs_y > abs_x and abs_y > self.movement_threshold:
            return self.UP if avg_dy < 0 else self.DOWN

        return self.NONE

    def close(self):
        if hasattr(self, "hands"):
            self.hands.close()
