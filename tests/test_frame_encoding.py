"""Manual tests for ASCII servo command formatting.

Protocol examples:
- Single: #000P1500T1000!
- Multi: {G0000#000P1602T1000!#001P2500T0000!#002P1500T1000!}
"""


def _format_id(servo_id: int) -> str:
    if not (0 <= servo_id <= 254):
        raise ValueError("servo_id out of range")
    return f"{servo_id:03d}"


def _format_pwm(pwm: int) -> str:
    pwm = max(500, min(2500, int(pwm)))
    return f"{pwm:04d}"


def _format_time_ms(time_ms: int) -> str:
    time_ms = max(0, min(9999, int(time_ms)))
    return f"{time_ms:04d}"


def build_single(servo_id: int, pwm: int, time_ms: int) -> str:
    return f"#{_format_id(servo_id)}P{_format_pwm(pwm)}T{_format_time_ms(time_ms)}!"


def build_group(commands: list[str]) -> str:
    if not commands:
        return ""
    if len(commands) == 1:
        return commands[0]
    return "{G0000" + "".join(commands) + "}"


def run_tests():
    """Run test cases to verify command formatting."""
    cases = [
        (0, 1500, 1000, "#000P1500T1000!"),
        (3, 800, 500, "#003P0800T0500!"),
        (254, 2500, 0, "#254P2500T0000!"),
        (1, 499, -1, "#001P0500T0000!"),
        (2, 99999, 12000, "#002P2500T9999!"),
    ]

    print("=" * 60)
    print("Servo ASCII Command Formatting Tests")
    print("=" * 60)

    all_passed = True

    for servo_id, pwm, time_ms, expected in cases:
        got = build_single(servo_id, pwm, time_ms)
        ok = got == expected
        print(f"\nTest: id={servo_id} pwm={pwm} t={time_ms}")
        print(f"Got:      {got}")
        print(f"Expected: {expected}")
        if ok:
            print("PASS")
        else:
            print("FAIL")
            all_passed = False

    group = build_group(
        [
            build_single(0, 1602, 1000),
            build_single(1, 2500, 0),
            build_single(2, 1500, 1000),
        ]
    )
    expected_group = "{G0000#000P1602T1000!#001P2500T0000!#002P1500T1000!}"
    print("\nGroup test:")
    print(f"Got:      {group}")
    print(f"Expected: {expected_group}")
    if group == expected_group:
        print("PASS")
    else:
        print("FAIL")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("All tests PASSED - Command formatting is correct!")
    else:
        print("Some tests FAILED - Check formatting implementation!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
