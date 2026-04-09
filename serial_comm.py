"""Serial communication with response handling."""

import struct
import threading
import time

try:
    import serial

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class SerialCommunicator:
    """Send position data and read responses from mechanical arm."""

    FRAME_SIZE = 11

    def __init__(self, port="/dev/tty0", baudrate=115200, timeout=0.5):
        if not SERIAL_AVAILABLE:
            raise RuntimeError("pyserial not available. Install: pip install pyserial")

        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.conn = None
        self._error_flag = False
        self._last_response = ""
        self._lock = threading.Lock()

        self._open()

    def _open(self):
        try:
            self.conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
            time.sleep(0.1)
        except serial.SerialException as e:
            raise RuntimeError(f"Failed to open {self.port}: {e}")

    def _encode_frame(self, x, y, z, a):
        """Encode 11-byte frame: [0xAA][X_L][X_H][Y_L][Y_H][Z_L][Z_H][A_L][A_H][checksum][0x55]"""
        x = max(-500, min(500, int(x)))
        y = max(-500, min(500, int(y)))
        z = max(0, min(1000, int(z)))
        a = max(-180, min(180, int(a)))

        xb = struct.pack("<h", x)
        yb = struct.pack("<h", y)
        zb = struct.pack("<h", z)
        ab = struct.pack("<h", a)

        frame = bytearray(9)
        frame[0] = 0xAA
        frame[1:3] = xb
        frame[3:5] = yb
        frame[5:7] = zb
        frame[7:9] = ab

        checksum = sum(frame) & 0xFF
        frame.append(checksum)
        frame.append(0x55)

        return bytes(frame)

    def send_and_read(self, x, y, z, a):
        """Send position and read response.

        Returns: (success, response, frame_hex)
        """
        with self._lock:
            if not self.conn or not self.conn.is_open:
                return False, "Serial not connected", None

            try:
                frame = self._encode_frame(x, y, z, a)
                self.conn.write(frame)
                self.conn.flush()

                frame_hex = " ".join(f"{b:02X}" for b in frame)

                time.sleep(0.05)

                if self.conn.in_waiting > 0:
                    response = self.conn.read(self.conn.in_waiting).decode(
                        "utf-8", errors="ignore"
                    )
                    self._last_response = response.strip()

                    if "ERR:" in response:
                        self._error_flag = True
                        return False, self._last_response, frame_hex
                    elif "OK" in response:
                        self._error_flag = False
                        return True, self._last_response, frame_hex
                    else:
                        return True, self._last_response, frame_hex

                return True, "No response", frame_hex

            except serial.SerialException as e:
                self._error_flag = True
                return False, str(e), None

    def has_error(self):
        """Check if last command caused error."""
        return self._error_flag

    def clear_error(self):
        """Clear error flag."""
        self._error_flag = False

    def get_last_response(self):
        return self._last_response

    def is_connected(self):
        return self.conn is not None and self.conn.is_open

    def close(self):
        if self.conn and self.conn.is_open:
            self.conn.close()
            self.conn = None
