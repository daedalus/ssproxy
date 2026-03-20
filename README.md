# SSProxy

A simple, stupid, chainable HTTP proxy with multithreading support, written in Python.

## Features

- **Multithreaded** - Handles multiple concurrent connections
- **Chainable** - Can chain through upstream proxies (with Basic auth support)
- **HTTP CONNECT Support** - Tunnels HTTPS traffic through the proxy
- **YAML Configurable** - All settings can be configured via `config.yaml`
- **CLI Overrides** - Command-line arguments take precedence over config
- **Colorful Output** - Terminal-friendly colored logging for requests/responses

## Installation

```bash
pip install -e .
```

## Usage

### Command Line

```bash
# Run with default config (config.yaml)
ssproxy

# Run on custom port
ssproxy -p 8888

# Chain through upstream proxy
ssproxy --upstream proxy.example.com:8080

# Disable colored output
ssproxy --plain

# Show all options
ssproxy --help
```

### Configuration File

Create `config.yaml`:

```yaml
host: 127.0.0.1
port: 8080

upstream_proxy:
  enabled: false
  host: 127.0.0.1
  port: 8888
  auth:
    enabled: false
    username: ""
    password: ""

logging:
  enabled: true
  colorful: true
  show_request_body: false
  show_response_body: false

threads:
  max_connections: 100
  timeout: 30
```

### Programmatic Usage

```python
from proxy.config import ProxyConfig
from proxy.server import ProxyServer

config = ProxyConfig()
config.port = 8080

server = ProxyServer(config)
server.start()
```

## How It Works

```
Client <--> HTTP Proxy <--> Server
                |
                v
          Upstream Proxy (optional)
                |
                v
          Target Server
```

### HTTP Requests

Standard HTTP requests are forwarded directly to the target server:

```
GET http://example.com/path HTTP/1.1
Host: example.com
```

### CONNECT Tunneling

HTTPS traffic uses the CONNECT method to establish a tunnel:

```
CONNECT example.com:443 HTTP/1.1
Host: example.com:443
```

The proxy establishes a TCP tunnel, allowing encrypted traffic to pass through.

## CLI Options

| Option | Description |
|--------|-------------|
| `-c, --config` | Path to YAML config file |
| `--host` | Host to bind to |
| `-p, --port` | Port to bind to |
| `--upstream` | Upstream proxy (host:port) |
| `--no-upstream` | Disable upstream proxy |
| `--timeout` | Connection timeout (seconds) |
| `--max-connections` | Max concurrent connections |
| `--plain` | Disable colored output |
| `--quiet` | Disable logging |
| `--debug` | Enable debug logging |

## Testing

```bash
# Start proxy
ssproxy -p 8080

# Test with curl
curl http://httpbin.org/ip --proxy http://127.0.0.1:8080

# Test HTTPS tunneling
curl https://example.com --proxy http://127.0.0.1:8080
```

## Requirements

- Python 3.8+
- PyYAML

Examples:
  ssproxy                              # Run with default config (config.yaml)
  ssproxy -p 8888                  # Run on port 8888
  ssproxy --config /path/to/config.yml # Use custom config file
  ssproxy --no-upstream                # Disable upstream proxy chain
  ssproxy --upstream proxy.example.com:8080  # Set upstream proxy
  ssproxy --plain                      # Disable colored output
        """,
