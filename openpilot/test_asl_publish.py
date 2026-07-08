#!/usr/bin/env python3
import sys
import termios
import tty
import time
from queue import Queue, Empty
from threading import Thread

import cereal.messaging as messaging

RATE_HZ = 10

DIGITS = {
    '0': ["██████", "██  ██", "██  ██", "██  ██", "██████"],
    '1': ["████  ", "  ██  ", "  ██  ", "  ██  ", "██████"],
    '2': ["██████", "    ██", "██████", "██    ", "██████"],
    '3': ["██████", "    ██", "██████", "    ██", "██████"],
    '4': ["██  ██", "██  ██", "██████", "    ██", "    ██"],
    '5': ["██████", "██    ", "██████", "    ██", "██████"],
    '6': ["██████", "██    ", "██████", "██  ██", "██████"],
    '7': ["██████", "    ██", "    ██", "    ██", "    ██"],
    '8': ["██████", "██  ██", "██████", "██  ██", "██████"],
    '9': ["██████", "██  ██", "██████", "    ██", "██████"],
    '-': ["      ", "      ", "██████", "      ", "      "],
}

DIGIT_HEIGHT = 5


def render_big_number(n: int) -> list[str]:
    s = str(n)
    rows = ["" for _ in range(DIGIT_HEIGHT)]
    for i, ch in enumerate(s):
        glyph = DIGITS.get(ch, DIGITS['-'])
        for r in range(DIGIT_HEIGHT):
            rows[r] += glyph[r]
            if i != len(s) - 1:
                rows[r] += " "
    return rows


def build_box(title: str, content_lines: list[str], min_width: int = 0) -> list[str]:
    inner_width = max([len(title)] + [len(line) for line in content_lines] + [min_width])
    top = "┏" + "━" * (inner_width + 2) + "┓"
    header = "┃ " + title.ljust(inner_width) + " ┃"
    sep = "┠" + "─" * (inner_width + 2) + "┨"
    body = ["┃ " + line.ljust(inner_width) + " ┃" for line in content_lines]
    bottom = "┗" + "━" * (inner_width + 2) + "┛"
    return [top, header, sep] + body + [bottom]


def build_number_box(title: str, speed: int, min_width: int = 0) -> list[str]:
    big_rows = render_big_number(speed)
    number_width = len(big_rows[0]) if big_rows else 0
    inner_width = max(len(title), number_width, min_width)

    top = "┏" + "━" * (inner_width + 2) + "┓"
    header = "┃ " + title.ljust(inner_width) + " ┃"
    sep = "┠" + "─" * (inner_width + 2) + "┨"

    body = []
    for row in big_rows:
        padded = row.center(inner_width)
        body.append("┃ " + padded + " ┃")

    bottom = "┗" + "━" * (inner_width + 2) + "┛"
    return [top, header, sep] + body + [bottom]


def combine_side_by_side(left: list[str], right: list[str], gap: int = 4) -> str:
    left_width = len(left[0]) if left else 0
    right_width = len(right[0]) if right else 0
    height = max(len(left), len(right))

    left_padded = left + [" " * left_width] * (height - len(left))
    right_padded = right + [" " * right_width] * (height - len(right))

    return "\n".join(
        l + " " * gap + r for l, r in zip(left_padded, right_padded)
    )


def render_ui(speed: int) -> str:
    left_box = build_box(
        "Test ASL Publisher",
        [
            "Commands:",
            "    [+] - Increments the published ASL speed by 1",
            "    [-] - Decrements the published ASL speed by 1",
            "    [q] - Gracefully quits the ASL Publisher",
            "",
        ],
    )
    right_box = build_number_box("Current ASL speed", speed, min_width=12)
    return combine_side_by_side(left_box, right_box)


def draw_screen(speed: int):
    sys.stdout.write("\033[H\033[J")
    sys.stdout.write(render_ui(speed) + "\n")
    sys.stdout.flush()


def keyboard_poll_thread(q: Queue):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            ch = sys.stdin.read(1)
            q.put(ch)
            if ch == 'q':
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class ASLController:
    def __init__(self):
        self.speed = 0
        self.pm = messaging.PubMaster(['advisorySpeedLimit'])

    def _publish_asl_message(self):
        msg = messaging.new_message('advisorySpeedLimit')
        msg.advisorySpeedLimit.speed = self.speed
        msg.valid = True
        msg.advisorySpeedLimit.valid = True
        self.pm.send('advisorySpeedLimit', msg)

    def _adjust_asl(self, amt: int):
        if self.speed + amt >= 0:
            self.speed += amt

    def _quit_test(self):
        sys.stdout.write("\033[?25h")
        sys.stdout.write("\n[info] User requested test quit. Come to a stop safely!\n")
        sys.exit()


def main():
    testASL = ASLController()

    q: Queue = Queue()
    t = Thread(target=keyboard_poll_thread, args=(q,), daemon=True)
    t.start()

    INPUT_MAP = {
        '+': lambda: testASL._adjust_asl(1),
        '-': lambda: testASL._adjust_asl(-1),
        'q': lambda: testASL._quit_test(),
    }

    sys.stdout.write("\033[?25l")
    draw_screen(testASL.speed)
    testASL._publish_asl_message()

    period = 1.0 / RATE_HZ
    next_publish = time.monotonic()

    try:
        while True:
            redraw = False
            try:
                ch = q.get_nowait()
                if ch in INPUT_MAP:
                    INPUT_MAP[ch]()
                    testASL._publish_asl_message()
                    redraw = True
            except Empty:
                pass

            now = time.monotonic()
            if now >= next_publish:
                testASL._publish_asl_message()
                next_publish = now + period

            if redraw:
                draw_screen(testASL.speed)

            time.sleep(0.01)
    finally:
        sys.stdout.write("\033[?25h")


if __name__ == "__main__":
    main()
