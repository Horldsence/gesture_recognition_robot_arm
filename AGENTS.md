# PROJECT KNOWLEDGE BASE

**Generated:** 2026-04-09
**Project:** gesture_recognition

## OVERVIEW

Raspberry Pi gesture recognition system controlling mechanical arm via MediaPipe hand detection + serial communication. Desktop tkinter GUI.

## STRUCTURE

```
gesture_recognition/
├── main.py              # Entry point, UI, PositionAccumulator (379 lines)
├── camera_handler.py    # PiCamera2 capture (48 lines)
├── gesture_detector.py  # MediaPipe hand detection + direction (138 lines)
├── serial_comm.py       # 11-byte frame protocol to arm (129 lines)
├── tests/               # Manual protocol tests (122 lines)
├── requirements.txt     # 6 deps (picamera2, mediapipe, opencv, pyserial)
└── README.md            # Hardware specs, protocol docs
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add gesture type | `gesture_detector.py:19-25` | Class constants |
| Modify UI | `main.py:93-189` | `_setup_ui()` |
| Change step size | `main.py:19` | `STEP_SIZE = 10` |
| Serial protocol | `serial_comm.py:48-71` | `_encode_frame()` |
| Coordinate limits | `serial_comm.py:50-53` | Clamp values |
| Test protocol | `tests/test_frame_encoding.py` | Run standalone |
| Camera settings | `camera_handler.py:15-16` | Width/height |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| GestureApp | class | main.py:73 | Main UI + orchestration |
| PositionAccumulator | class | main.py:16 | Track X/Y/Z/A, error state |
| GestureDetector | class | gesture_detector.py:16 | Hand detection, direction calc |
| CameraHandler | class | camera_handler.py:14 | PiCamera2 wrapper |
| SerialCommunicator | class | serial_comm.py:15 | Frame encoding, send/read |
| _encode_frame | method | serial_comm.py:48 | 11-byte frame builder |
| _detect_direction | method | gesture_detector.py:90 | Movement → gesture |
| _loop | method | main.py:298 | Main capture/process thread |

## CONVENTIONS

- **Flat structure**: All modules at root, no `__init__.py`
- **Ruff linter**: Default config (`.ruff_cache/` exists)
- **Manual tests**: No pytest, run `python3 tests/test_frame_encoding.py`
- **Chinese UI strings**: UI labels in Chinese (手势识别, 向前, 向后...)
- **Graceful degradation**: Serial failure logs warning, continues without serial
- **Thread-safe**: Serial uses `threading.Lock()`

## ANTI-PATTERNS (THIS PROJECT)

- **No explicit anti-patterns in comments**: Clean codebase, no TODO/FIXME/WARNING markers

## UNIQUE STYLES

- **Import guards**: `try/except ImportError` for optional deps (MediaPipe, PiCamera2, pyserial)
- **Error flag pattern**: `_error` bool in PositionAccumulator + SerialCommunicator stops accumulation on error
- **History smoothing**: GestureDetector uses 5-frame history for stable gesture detection
- **Coordinate clamping**: Inline in `_encode_frame()` (X: -500~500, Y: -500~500, Z: 0~1000, A: -180~180)

## SERIAL PROTOCOL

**11-byte frame:**
```
[0xAA][X_L][X_H][Y_L][Y_H][Z_L][Z_H][A_L][A_H][checksum][0x55]
```
- All values little-endian int16
- Checksum = sum(bytes 0-8) & 0xFF
- Response: `OK (x=X,y=Y,z=Z,a=A)\r\n` or `ERR:N\r\n`

## COMMANDS

```bash
# Install (requires Raspberry Pi for picamera2)
pip install -r requirements.txt

# Run main app
python3 main.py

# Test serial protocol
python3 tests/test_frame_encoding.py
```

## NOTES

- **Hardware lock**: PiCamera2 only works on Raspberry Pi
- **Serial port**: Default `/dev/ttyUSB0` (see `SerialCommunicator(port=...)`)
- **Gesture thresholds**: `movement_threshold=0.02`, `size_threshold=0.05` (gesture_detector.py:49-50)
- **Send interval**: 150ms (`send_interval=0.15` in main.py:87)
- **No package config**: Missing pyproject.toml, setup.py
- **No CI/CD**: Manual test execution only