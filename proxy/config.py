"""Configuration management for HTTP proxy."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class UpstreamAuth:
    enabled: bool = False
    username: str = ""
    password: str = ""

    def to_dict(self):
        return {
            "enabled": self.enabled,
            "username": self.username,
            "password": self.password,
        }


@dataclass
class UpstreamProxy:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8888
    auth: UpstreamAuth = field(default_factory=UpstreamAuth)

    def to_dict(self):
        return {
            "enabled": self.enabled,
            "host": self.host,
            "port": self.port,
            "auth": self.auth.to_dict(),
        }


@dataclass
class LoggingConfig:
    enabled: bool = True
    colorful: bool = True
    show_request_body: bool = False
    show_response_body: bool = False

    def to_dict(self):
        return {
            "enabled": self.enabled,
            "colorful": self.colorful,
            "show_request_body": self.show_request_body,
            "show_response_body": self.show_response_body,
        }


@dataclass
class ThreadConfig:
    max_connections: int = 100
    timeout: int = 30

    def to_dict(self):
        return {
            "max_connections": self.max_connections,
            "timeout": self.timeout,
        }


@dataclass
class ProxyConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    upstream_proxy: UpstreamProxy = field(default_factory=UpstreamProxy)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    threads: ThreadConfig = field(default_factory=ThreadConfig)

    def to_dict(self):
        return {
            "host": self.host,
            "port": self.port,
            "upstream_proxy": self.upstream_proxy.to_dict(),
            "logging": self.logging.to_dict(),
            "threads": self.threads.to_dict(),
        }


def load_config(config_path: Optional[str] = None) -> ProxyConfig:
    if config_path is None:
        config_path = os.environ.get("PROXY_CONFIG", "config.yaml")

    config_file = Path(config_path)

    if not config_file.exists():
        return ProxyConfig()

    with open(config_file, "r") as f:
        data = yaml.safe_load(f) or {}

    upstream_auth_data = data.get("upstream_proxy", {}).get("auth", {})
    upstream_auth = UpstreamAuth(
        enabled=upstream_auth_data.get("enabled", False),
        username=upstream_auth_data.get("username", ""),
        password=upstream_auth_data.get("password", ""),
    )

    upstream_proxy_data = data.get("upstream_proxy", {})
    upstream_proxy = UpstreamProxy(
        enabled=upstream_proxy_data.get("enabled", False),
        host=upstream_proxy_data.get("host", "127.0.0.1"),
        port=upstream_proxy_data.get("port", 8888),
        auth=upstream_auth,
    )

    logging_data = data.get("logging", {})
    logging_config = LoggingConfig(
        enabled=logging_data.get("enabled", True),
        colorful=logging_data.get("colorful", True),
        show_request_body=logging_data.get("show_request_body", False),
        show_response_body=logging_data.get("show_response_body", False),
    )

    threads_data = data.get("threads", {})
    threads_config = ThreadConfig(
        max_connections=threads_data.get("max_connections", 100),
        timeout=threads_data.get("timeout", 30),
    )

    return ProxyConfig(
        host=data.get("host", "127.0.0.1"),
        port=data.get("port", 8080),
        upstream_proxy=upstream_proxy,
        logging=logging_config,
        threads=threads_config,
    )


def save_config(config: ProxyConfig, config_path: str):
    with open(config_path, "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)
