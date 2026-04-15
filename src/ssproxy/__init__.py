"""SSProxy - A simple, chainable HTTP proxy with multithreading support."""

from typing import TYPE_CHECKING

from .config import (
    LoggingConfig,
    ProxyConfig,
    ThreadConfig,
    UpstreamAuth,
    UpstreamProxy,
    load_config,
    save_config,
)
from .logging_utils import logger as logger
from .server import ProxyServer

__version__ = "0.1.0.1"

__all__ = [
    "ProxyConfig",
    "UpstreamProxy",
    "UpstreamAuth",
    "LoggingConfig",
    "ThreadConfig",
    "load_config",
    "save_config",
    "ProxyServer",
    "logger",
]
