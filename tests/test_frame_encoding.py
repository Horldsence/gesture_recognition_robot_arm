"""
Test script to verify data frame encoding correctness.
Run this to validate the serial communication protocol.
"""

import struct


def encode_frame_test(x, y, z, a):
    """
    Encode position data into 11-byte frame format.
    Returns bytes object for verification.
    """
    x = max(-500, min(500, int(x)))
    y = max(-500, min(500, int(y)))
    z = max(0, min(1000, int(z)))
    a = max(-180, min(180, int(a)))

    x_bytes = struct.pack("<h", x)
    y_bytes = struct.pack("<h", y)
    z_bytes = struct.pack("<h", z)
    a_bytes = struct.pack("<h", a)

    frame = bytearray(9)
    frame[0] = 0xAA
    frame[1] = x_bytes[0]
    frame[2] = x_bytes[1]
    frame[3] = y_bytes[0]
    frame[4] = y_bytes[1]
    frame[5] = z_bytes[0]
    frame[6] = z_bytes[1]
    frame[7] = a_bytes[0]
    frame[8] = a_bytes[1]

    checksum = sum(frame[0:9]) & 0xFF
    frame.append(checksum)
    frame.append(0x55)

    return bytes(frame)


def decode_frame(frame):
    """Decode frame to verify values."""
    if len(frame) != 11:
        return None, "Invalid frame length"

    if frame[0] != 0xAA:
        return None, "Invalid header"

    if frame[10] != 0x55:
        return None, "Invalid tail"

    checksum_calc = sum(frame[0:9]) & 0xFF
    if frame[9] != checksum_calc:
        return (
            None,
            f"Checksum mismatch: expected {checksum_calc:02X}, got {frame[9]:02X}",
        )

    x = struct.unpack("<h", frame[1:3])[0]
    y = struct.unpack("<h", frame[3:5])[0]
    z = struct.unpack("<h", frame[5:7])[0]
    a = struct.unpack("<h", frame[7:9])[0]

    return (x, y, z, a), "Valid"


def run_tests():
    """Run test cases to verify encoding."""
    test_cases = [
        (100, 200, 300, 45),
        (-500, -500, 0, -180),
        (500, 500, 1000, 180),
        (0, 0, 500, 0),
        (123, -456, 789, -90),
    ]

    print("=" * 60)
    print("Data Frame Encoding Verification Tests")
    print("=" * 60)
    print(f"Frame format: 11 bytes total")
    print(f"  Byte 0: Header (0xAA)")
    print(f"  Bytes 1-2: X (little-endian int16)")
    print(f"  Bytes 3-4: Y (little-endian int16)")
    print(f"  Bytes 5-6: Z (little-endian int16)")
    print(f"  Bytes 7-8: A (little-endian int16)")
    print(f"  Byte 9: Checksum")
    print(f"  Byte 10: Tail (0x55)")
    print("=" * 60)

    all_passed = True

    for x, y, z, a in test_cases:
        frame = encode_frame_test(x, y, z, a)
        decoded, status = decode_frame(frame)

        frame_hex = " ".join([f"{b:02X}" for b in frame])

        print(f"\nTest: X={x}, Y={y}, Z={z}, A={a}")
        print(f"Frame: {frame_hex}")

        if decoded is None:
            print(f"FAIL: {status}")
            all_passed = False
        else:
            dx, dy, dz, da = decoded
            if dx == x and dy == y and dz == z and da == a:
                print(f"PASS: Decoded values match input")
            else:
                print(f"FAIL: Decoded mismatch - X={dx}, Y={dy}, Z={dz}, A={da}")
                all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("All tests PASSED - Frame encoding is correct!")
    else:
        print("Some tests FAILED - Check implementation!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
