"""Serial communication for robotic arm servo controller.

Protocol examples:
- Single: #000P1500T1000!
- Multi: {G0000#000P1602T1000!#001P2500T0000!#002P1500T1000!}

"#" and "!" are fixed tokens.
ID is 3 digits (0-254), PWM is 4 digits (500-2500), TIME is 4 digits (0-9999 ms).
"""

import threading
import time

try:
    import serial

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class SerialCommunicator:
    """Send servo PWM commands and optionally read responses."""

    def __init__(
        self,
        port="/dev/ttyUSB0",
        baudrate=115200,
        timeout=0.5,
        servo_ids=(0, 1, 2, 3),
        default_time_ms=150,
    ):
        if not SERIAL_AVAILABLE:
            raise RuntimeError("pyserial not available. Install: pip install pyserial")

        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.servo_ids = tuple(int(i) for i in servo_ids)
        self.default_time_ms = int(default_time_ms)
        self.conn = None
        self._error_flag = False
        self._last_response = ""
        self._last_command = ""
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

    @staticmethod
    def _format_id(servo_id: int) -> str:
        servo_id = int(servo_id)
        if not (0 <= servo_id <= 254):
            raise ValueError(f"servo_id out of range (0-254): {servo_id}")
        return f"{servo_id:03d}"

    @staticmethod
    def _format_pwm(pwm: int) -> str:
        pwm = int(pwm)
        pwm = max(500, min(2500, pwm))
        return f"{pwm:04d}"

    @staticmethod
    def _format_time_ms(time_ms: int) -> str:
        time_ms = int(time_ms)
        time_ms = max(0, min(9999, time_ms))
        return f"{time_ms:04d}"

    def build_single_command(self, servo_id: int, pwm: int, time_ms: int) -> str:
        """Build a single servo command like: #000P1500T1000!"""
        sid = self._format_id(servo_id)
        pwm_s = self._format_pwm(pwm)
        t_s = self._format_time_ms(time_ms)
        return f"#{sid}P{pwm_s}T{t_s}!"

    def build_group_command(self, commands: list[str]) -> str:
        """Build multi-servo command. If 2+ commands, wrap with {G0000...}."""
        if not commands:
            return ""
        if len(commands) == 1:
            return commands[0]
        return "{G0000" + "".join(commands) + "}"

    def _send_raw(self, command: str):
        if not self.conn or not self.conn.is_open:
            raise RuntimeError("Serial not connected")

        self._last_command = command
        payload = command.encode("ascii", errors="ignore")
        self.conn.write(payload)
        self.conn.flush()

    def send_and_read(self, x, y, z, a):
        """Send 4-channel PWM values and read response (if any).

        Notes:
        - This keeps the legacy method signature used by main.py.
        - x/y/z/a are treated as PWM values (500-2500).

        Returns: (success, response, command_string)
        """
        with self._lock:
            if not self.conn or not self.conn.is_open:
                return False, "Serial not connected", None

            try:
                time_ms = self.default_time_ms
                pwms = [x, y, z, a]

                commands = []
                for idx in range(min(len(self.servo_ids), len(pwms))):
                    servo_id = self.servo_ids[idx]
                    pwm = pwms[idx]
                    commands.append(self.build_single_command(servo_id, pwm, time_ms))

                group = self.build_group_command(commands)
                self._send_raw(group)

                time.sleep(0.02)
                response = ""
                if getattr(self.conn, "in_waiting", 0) > 0:
                    response = self.conn.read(self.conn.in_waiting).decode(
                        "utf-8", errors="ignore"
                    )
                self._last_response = response.strip()

                self._error_flag = False
                return True, (self._last_response or "No response"), group

            except serial.SerialException as e:
                self._error_flag = True
                return False, str(e), None
            except Exception as e:
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

    def get_last_command(self):
        return self._last_command

    def reset_all(self, pwm=1500, time_ms=1000):
        """Reset all configured servos to a given PWM (default 1500) in one command."""
        with self._lock:
            if not self.conn or not self.conn.is_open:
                return False, "Serial not connected", None

            try:
                commands = [
                    self.build_single_command(servo_id, pwm, time_ms)
                    for servo_id in self.servo_ids
                ]
                group = self.build_group_command(commands)
                self._send_raw(group)
                self._error_flag = False
                return True, "OK", group
            except serial.SerialException as e:
                self._error_flag = True
                return False, str(e), None
            except Exception as e:
                self._error_flag = True
                return False, str(e), None

    def is_connected(self):
        return self.conn is not None and self.conn.is_open

    def close(self):
        if self.conn and self.conn.is_open:
            self.conn.close()
            self.conn = None
