"""Colorful logging utilities for HTTP proxy."""

import sys
from datetime import datetime
from enum import Enum


class Color(Enum):
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


class LogLevel(Enum):
    DEBUG = ("DEBUG", Color.DIM, Color.DIM)
    INFO = ("INFO", Color.CYAN, Color.BOLD)
    REQUEST = ("REQUEST", Color.BLUE, Color.BOLD)
    RESPONSE = ("RESPONSE", Color.GREEN, Color.BOLD)
    WARNING = ("WARN", Color.YELLOW, Color.BOLD)
    ERROR = ("ERROR", Color.RED, Color.BOLD)
    SUCCESS = ("OK", Color.GREEN, Color.BOLD)


class ColoredLogger:
    def __init__(self, enabled: bool = True, colorful: bool = True) -> None:
        self.enabled = enabled
        self.colorful = colorful

    def _format(
        self,
        level: LogLevel,
        message: str,
        show_timestamp: bool = True,
        show_color_label: bool = True,
    ) -> str:
        parts = []

        if show_timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            parts.append(f"{Color.DIM.value}{timestamp}{Color.RESET.value}")

        if show_color_label:
            _, text_color, style = level.value
            label = level.value[0]
            if self.colorful:
                color_str = f"{style.value}{text_color.value}{label}{Color.RESET.value}"
                parts.append(f"[{color_str}]")
            else:
                parts.append(f"[{label}]")

        parts.append(message)
        return " ".join(parts)

    def _print(self, level: LogLevel, message: str, **kwargs: bool) -> None:
        if not self.enabled:
            return
        formatted = self._format(level, message, **kwargs)
        print(formatted, file=sys.stdout)

    def debug(self, message: str) -> None:
        self._print(LogLevel.DEBUG, message)

    def info(self, message: str) -> None:
        self._print(LogLevel.INFO, message)

    def request(self, message: str) -> None:
        self._print(LogLevel.REQUEST, message, show_color_label=False)
        print(f"  {message}", file=sys.stdout)

    def response(self, message: str) -> None:
        self._print(LogLevel.RESPONSE, message, show_color_label=False)
        print(f"  {message}", file=sys.stdout)

    def warning(self, message: str) -> None:
        self._print(LogLevel.WARNING, message)

    def error(self, message: str) -> None:
        self._print(LogLevel.ERROR, message)

    def success(self, message: str) -> None:
        self._print(LogLevel.SUCCESS, message)

    def log_request_line(self, method: str, url: str, client_addr: str) -> None:
        if not self.enabled:
            return
        if self.colorful:
            print(
                f"{Color.DIM.value}{datetime.now().strftime('%H:%M:%S.%f')[:-3]}{Color.RESET.value} "
                f"[{Color.BLUE.value}{Color.BOLD.value}REQ{Color.RESET.value}] "
                f"{Color.CYAN.value}{client_addr}{Color.RESET.value} --> "
                f"{Color.YELLOW.value}{method}{Color.RESET.value} {Color.WHITE.value}{url}{Color.RESET.value}"
            )
        else:
            print(
                f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} [REQ] {client_addr} --> {method} {url}"
            )

    def log_response_line(
        self, status_code: int, reason: str, client_addr: str
    ) -> None:
        if not self.enabled:
            return
        if status_code < 300:
            color = Color.GREEN
        elif status_code < 400:
            color = Color.YELLOW
        elif status_code < 500:
            color = Color.RED
        else:
            color = Color.RED

        if self.colorful:
            print(
                f"{Color.DIM.value}{datetime.now().strftime('%H:%M:%S.%f')[:-3]}{Color.RESET.value} "
                f"[{Color.GREEN.value}{Color.BOLD.value}RES{Color.RESET.value}] "
                f"{Color.CYAN.value}{client_addr}{Color.RESET.value} <-- "
                f"{color.value}{status_code}{Color.RESET.value} {reason}"
            )
        else:
            print(
                f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} [RES] {client_addr} <-- {status_code} {reason}"
            )

    def log_connect(self, host: str, port: int, client_addr: str) -> None:
        if not self.enabled:
            return
        if self.colorful:
            print(
                f"{Color.DIM.value}{datetime.now().strftime('%H:%M:%S.%f')[:-3]}{Color.RESET.value} "
                f"[{Color.MAGENTA.value}{Color.BOLD.value}CON{Color.RESET.value}] "
                f"{Color.CYAN.value}{client_addr}{Color.RESET.value} -- "
                f"Establishing tunnel to {Color.YELLOW.value}{host}:{port}{Color.RESET.value}"
            )
        else:
            print(
                f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} [CON] {client_addr} -- Establishing tunnel to {host}:{port}"
            )

    def log_connect_success(self, host: str, port: int, client_addr: str) -> None:
        if not self.enabled:
            return
        if self.colorful:
            print(
                f"{Color.DIM.value}{datetime.now().strftime('%H:%M:%S.%f')[:-3]}{Color.RESET.value} "
                f"[{Color.GREEN.value}{Color.BOLD.value}TUN{Color.RESET.value}] "
                f"{Color.CYAN.value}{client_addr}{Color.RESET.value} == "
                f"Tunnel established to {Color.YELLOW.value}{host}:{port}{Color.RESET.value}"
            )
        else:
            print(
                f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} [TUN] {client_addr} == Tunnel established to {host}:{port}"
            )


logger = ColoredLogger()
