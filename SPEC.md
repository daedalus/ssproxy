# SPEC.md — SSProxy

## Purpose
A simple, chainable HTTP proxy with multithreading support, written in Python. It can handle concurrent client connections, forward HTTP requests to target servers or through upstream proxies, and establish CONNECT tunnels for HTTPS traffic.

## Scope
- **In Scope:**
  - HTTP proxy server with multithreading
  - Chainable upstream proxy support with Basic authentication
  - HTTP CONNECT tunneling for HTTPS
  - YAML configuration file support
  - CLI argument overrides for all settings
  - Colored logging output
  - Configurable connection limits and timeouts
  - Access Control Lists (ACLs) with CIDR and FQDN support

- **Not in Scope:**
  - HTTPS inspection/decryption
  - Proxy authentication for clients
  - SOCKS proxy support
  - HTTP/2 support
  - Caching functionality

## Public API / Interface

### CLI Commands
- `ssproxy` — Start the proxy server with config file (default: config.yaml)
- `ssproxy -p <port>` — Run on custom port
- `ssproxy --upstream host:port` — Chain through upstream proxy
- `ssproxy --plain` — Disable colored output
- `ssproxy --help` — Show all options

### Python API

#### `proxy.config.ProxyConfig`
Main configuration class for the proxy server.
- `host: str` — Host to bind to (default: "127.0.0.1")
- `port: int` — Port to bind to (default: 8080)
- `upstream_proxy: UpstreamProxy` — Upstream proxy configuration
- `logging: LoggingConfig` — Logging configuration
- `threads: ThreadConfig` — Thread pool configuration

#### `proxy.config.UpstreamProxy`
- `enabled: bool` — Whether upstream proxy is enabled
- `host: str` — Upstream proxy host
- `port: int` — Upstream proxy port
- `auth: UpstreamAuth` — Authentication credentials

#### `proxy.config.UpstreamAuth`
- `enabled: bool` — Whether auth is enabled
- `username: str` — Username for Basic auth
- `password: str` — Password for Basic auth

#### `proxy.config.LoggingConfig`
- `enabled: bool` — Whether logging is enabled
- `colorful: bool` — Whether to use colored output
- `show_request_body: bool` — Whether to log request bodies
- `show_response_body: bool` — Whether to log response bodies

#### `proxy.config.ThreadConfig`
- `max_connections: int` — Maximum concurrent connections (default: 100)
- `timeout: int` — Connection timeout in seconds (default: 30)

#### `proxy.acl.ACLConfig`
- `enabled: bool` — Whether ACL is enabled (default: false)
- `default_action: ACLAction` — Default action when no rule matches (default: deny)
- `rules: list[ACLRule]` — List of ACL rules
- `check(client_ip, target_host) -> ACLAction` — Check if request is allowed

#### `proxy.acl.ACLRule`
- `action: ACLAction` — Action to take (allow or deny)
- `rule_type: ACLRuleType` — Type of rule (cidr or fqdn)
- `value: str` — The CIDR network or FQDN pattern
- `matches(client_ip, target_host) -> bool` — Check if rule matches

#### `proxy.config.load_config(path: Optional[str]) -> ProxyConfig`
Load configuration from a YAML file. Returns default config if file not found.

#### `proxy.server.ProxyServer`
Main server class.
- `__init__(self, config: Optional[ProxyConfig] = None)` — Initialize with config
- `start()` — Start the proxy server
- `stop()` — Stop the proxy server
- `running: bool` — Whether the server is currently running

#### `proxy.logging_utils.logger`
Global logger instance.
- `info()`, `debug()`, `error()`, `success()` — Logging methods
- `log_request_line()`, `log_response_line()`, `log_connect()` — Specialized logging
- `enabled: bool` — Toggle logging on/off
- `colorful: bool` — Toggle colored output

## Data Formats

### Configuration File (YAML)
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

acl:
  enabled: false
  default_action: deny
  rules:
    - action: allow
      type: cidr
      value: 192.168.1.0/24
    - action: allow
      type: fqdn
      value: "*.example.com"
    - action: deny
      type: cidr
      value: 10.0.0.0/8
```

### HTTP Request (Client → Proxy)
Standard HTTP/1.1 requests with absolute URLs:
```
GET http://example.com/path HTTP/1.1
Host: example.com
```

### CONNECT Tunnel (HTTPS)
```
CONNECT example.com:443 HTTP/1.1
Host: example.com:443
```

## Edge Cases
1. **Missing config file** — Should use defaults and warn user
2. **Invalid upstream proxy format** — CLI should error with usage message
3. **Connection to target server fails** — Return 502 Bad Gateway
4. **Upstream proxy rejects connection** — Return 502 with error log
5. **Malformed HTTP request** — Return 400 Bad Request
6. **Missing Host header** — Return 400 Bad Request
7. **Unsupported HTTP method** — Return 405 Method Not Allowed
8. **Port binding fails (permission denied)** — Exit with error message
9. **Client disconnects mid-request** — Clean up resources gracefully
10. **Timeout during tunnel** — Close connections and return 504 Gateway Timeout
11. **ACL denies client IP** — Return 403 Forbidden
12. **Invalid CIDR notation** — Raise ValueError during config loading
13. **Invalid FQDN wildcard pattern** — Valid wildcard patterns like `*.example.com`

## Performance & Constraints
- Maximum concurrent connections: configurable (default 100)
- Connection timeout: configurable (default 30 seconds)
- Requires Python 3.11+ (for modern typing features)
- Dependencies: PyYAML>=6.0
- No external runtime dependencies for core functionality

## Version
`__version__ = "0.1.0.1"`