# SSProxy

> A simple, chainable HTTP proxy with multithreading support.

[![PyPI](https://img.shields.io/pypi/v/ssproxy.svg)](https://pypi.org/project/ssproxy/)
[![Python](https://img.shields.io/pypi/pyversions/ssproxy.svg)](https://pypi.org/project/ssproxy/)
[![Coverage](https://codecov.io/gh/example/ssproxy/branch/main/graph/badge.svg)](https://codecov.io/gh/example/ssproxy)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Features

- **Multithreaded** - Handles multiple concurrent connections
- **Chainable** - Can chain through upstream proxies (with Basic auth support)
- **HTTP CONNECT Support** - Tunnels HTTPS traffic through the proxy
- **YAML Configurable** - All settings can be configured via `config.yaml`
- **CLI Overrides** - Command-line arguments take precedence over config
- **Colorful Output** - Terminal-friendly colored logging for requests/responses

## Install

```bash
pip install ssproxy
```

## Usage

```python
from ssproxy import ProxyConfig, ProxyServer

config = ProxyConfig()
config.port = 8080

server = ProxyServer(config)
server.start()
```

## CLI

```bash
ssproxy --help
```

## API

- `ProxyConfig` - Main configuration class
- `ProxyServer` - Main server class with start()/stop() methods
- `UpstreamProxy` - Upstream proxy configuration
- `UpstreamAuth` - Authentication credentials
- `LoggingConfig` - Logging configuration
- `ThreadConfig` - Thread pool configuration
- `ACLConfig` - Access control list configuration
- `load_config()` - Load configuration from YAML file

## Development

```bash
git clone https://github.com/example/ssproxy.git
cd ssproxy
pip install -e ".[test]"

# run tests
pytest

# format
ruff format src/ tests/

# lint
ruff check src/ tests/

# type check
mypy src/
```
