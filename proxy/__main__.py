"""Main module for HTTP proxy with CLI support."""

import argparse
import signal
import sys
from pathlib import Path

from proxy import __version__
from proxy.config import ProxyConfig, load_config
from proxy.logging_utils import logger
from proxy.server import ProxyServer


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ssproxy",
        description="A simple, chainable HTTP proxy with multithreading support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Run with default config (config.yaml)
  %(prog)s -p 8888                      # Run on port 8888
  %(prog)s --config /path/to/config.yml # Use custom config file
  %(prog)s --no-upstream                # Disable upstream proxy chain
  %(prog)s --upstream proxy.example.com:8080  # Set upstream proxy
  %(prog)s --plain                      # Disable colored output
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="config.yaml",
        help="Path to YAML configuration file (default: config.yaml)",
    )

    parser.add_argument(
        "--host",
        type=str,
        help="Host to bind to (overrides config)",
    )

    parser.add_argument(
        "-p",
        "--port",
        type=int,
        help="Port to bind to (overrides config)",
    )

    parser.add_argument(
        "--upstream",
        type=str,
        help="Upstream proxy in host:port format (overrides config)",
    )

    parser.add_argument(
        "--no-upstream",
        action="store_true",
        help="Disable upstream proxy (overrides config)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        help="Connection timeout in seconds (overrides config)",
    )

    parser.add_argument(
        "--max-connections",
        type=int,
        help="Maximum number of concurrent connections (overrides config)",
    )

    parser.add_argument(
        "--plain",
        action="store_true",
        help="Disable colored output",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable logging output",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    return parser


def apply_cli_overrides(config: ProxyConfig, args: argparse.Namespace) -> ProxyConfig:
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port
    if args.timeout:
        config.threads.timeout = args.timeout
    if args.max_connections:
        config.threads.max_connections = args.max_connections
    if args.no_upstream:
        config.upstream_proxy.enabled = False
    if args.upstream:
        try:
            host, port = args.upstream.rsplit(":", 1)
            config.upstream_proxy.enabled = True
            config.upstream_proxy.host = host
            config.upstream_proxy.port = int(port)
        except ValueError:
            print("Error: Invalid upstream format. Use host:port", file=sys.stderr)
            sys.exit(1)

    if args.plain:
        config.logging.colorful = False
    if args.quiet:
        config.logging.enabled = False

    return config


def main():
    parser = create_parser()
    args = parser.parse_args()

    if not Path(args.config).exists() and args.config == "config.yaml":
        print(
            "Warning: config.yaml not found, using defaults",
            file=sys.stderr,
        )

    config = load_config(args.config)
    config = apply_cli_overrides(config, args)

    server = ProxyServer(config)

    def signal_handler(signum, frame):
        print("\n")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
    except PermissionError:
        logger.error(f"Permission denied to bind to port {config.port}")
        sys.exit(1)
    except OSError as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
