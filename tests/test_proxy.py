import pytest
import socket
import threading
import time


class MockServer:
    def __init__(self, port):
        self.port = port
        self.server = None
        self.thread = None
        self.last_request = None
        self.response = b"HTTP/1.1 200 OK\r\nContent-Length: 11\r\n\r\nHello Proxy"

    def start(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("127.0.0.1", self.port))
        self.server.listen(1)
        self.server.settimeout(5)
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    def _run(self):
        try:
            conn, _ = self.server.accept()
            self.last_request = conn.recv(4096)
            conn.sendall(self.response)
            conn.close()
        except socket.timeout:
            pass
        finally:
            self.server.close()

    def stop(self):
        if self.thread:
            self.thread.join(timeout=2)


@pytest.fixture
def mock_server():
    server = MockServer(18888)
    server.start()
    yield server
    server.stop()


@pytest.fixture
def proxy_server():
    from proxy.config import ProxyConfig
    from proxy.server import ProxyServer
    from proxy.logging_utils import logger

    logger.enabled = False

    config = ProxyConfig()
    config.port = 19999
    config.logging.enabled = False

    server = ProxyServer(config)
    thread = threading.Thread(target=server.start)
    thread.start()
    time.sleep(0.2)

    yield server

    server.running = False
    thread.join(timeout=2)


class TestConfig:
    def test_proxy_config_defaults(self):
        from proxy.config import ProxyConfig

        config = ProxyConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 8080
        assert config.upstream_proxy.enabled is False
        assert config.threads.max_connections == 100
        assert config.threads.timeout == 30

    def test_upstream_proxy_config(self):
        from proxy.config import UpstreamProxy, UpstreamAuth

        auth = UpstreamAuth(username="user", password="pass")
        upstream = UpstreamProxy(
            enabled=True,
            host="proxy.example.com",
            port=8080,
            auth=auth
        )

        assert upstream.enabled is True
        assert upstream.host == "proxy.example.com"
        assert upstream.port == 8080
        assert upstream.auth.username == "user"
        assert upstream.auth.password == "pass"

    def test_load_config_file(self, tmp_path):
        from proxy.config import load_config

        config_content = """
host: 0.0.0.0
port: 8888
upstream_proxy:
  enabled: true
  host: upstream.proxy.com
  port: 3128
threads:
  max_connections: 50
  timeout: 60
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        config = load_config(str(config_file))

        assert config.host == "0.0.0.0"
        assert config.port == 8888
        assert config.upstream_proxy.enabled is True
        assert config.upstream_proxy.host == "upstream.proxy.com"
        assert config.threads.max_connections == 50
        assert config.threads.timeout == 60

    def test_load_missing_config_returns_defaults(self):
        from proxy.config import load_config

        config = load_config("/nonexistent/path.yaml")
        assert config.host == "127.0.0.1"
        assert config.port == 8080


class TestProxyHandler:
    def test_basic_http_request(self, proxy_server, mock_server):
        client = socket.socket()
        client.connect(("127.0.0.1", 19999))
        
        request = (
            b"GET http://127.0.0.1:18888/test HTTP/1.1\r\n"
            b"Host: 127.0.0.1:18888\r\n"
            b"\r\n"
        )
        client.sendall(request)
        
        response = client.recv(4096)
        client.close()
        
        assert b"200 OK" in response
        assert b"Hello Proxy" in response

    def test_http_request_with_body(self, proxy_server, mock_server):
        client = socket.socket()
        client.connect(("127.0.0.1", 19999))
        
        request = (
            b"POST http://127.0.0.1:18888/data HTTP/1.1\r\n"
            b"Host: 127.0.0.1:18888\r\n"
            b"Content-Length: 11\r\n"
            b"\r\n"
            b"Hello World"
        )
        client.sendall(request)
        
        response = client.recv(4096)
        client.close()
        
        assert b"200 OK" in response

    def test_proxy_returns_502_on_connection_failure(self):
        from proxy.config import ProxyConfig
        from proxy.server import ProxyServer
        from proxy.logging_utils import logger

        logger.enabled = False

        config = ProxyConfig()
        config.port = 19998
        config.logging.enabled = False
        config.upstream_proxy.enabled = True
        config.upstream_proxy.host = "127.0.0.1"
        config.upstream_proxy.port = 59999

        server = ProxyServer(config)
        thread = threading.Thread(target=server.start)
        thread.start()
        time.sleep(0.2)

        try:
            client = socket.socket()
            client.connect(("127.0.0.1", 19998))
            
            request = (
                b"GET http://example.com/ HTTP/1.1\r\n"
                b"Host: example.com\r\n"
                b"\r\n"
            )
            client.settimeout(5)
            client.sendall(request)
            
            response = client.recv(4096)
            client.close()
            
            assert b"502" in response
        finally:
            server.running = False
            thread.join(timeout=2)


class TestLogging:
    def test_colored_logger_output(self, capsys):
        from proxy.logging_utils import ColoredLogger

        logger = ColoredLogger(enabled=True, colorful=True)
        logger.info("Test message")
        
        captured = capsys.readouterr()
        assert "INFO" in captured.out
        assert "Test message" in captured.out

    def test_logger_disabled(self, capsys):
        from proxy.logging_utils import ColoredLogger

        logger = ColoredLogger(enabled=False)
        logger.info("Should not appear")
        
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_logger_plain_mode(self, capsys):
        from proxy.logging_utils import ColoredLogger

        logger = ColoredLogger(enabled=True, colorful=False)
        logger.info("Plain message")
        
        captured = capsys.readouterr()
        assert "INFO" in captured.out
        assert "Plain message" in captured.out

    def test_cli_help(self):
        import pytest
        from proxy.__main__ import create_parser

        parser = create_parser()
        
        with pytest.raises(SystemExit) as excinfo:
            parser.parse_args(["--help"])
        
        assert excinfo.value.code == 0

    def test_cli_port_override(self):
        import argparse
        from proxy.__main__ import apply_cli_overrides
        from proxy.config import ProxyConfig

        config = ProxyConfig()
        args = argparse.Namespace(
            config="config.yaml",
            host=None,
            port=8888,
            upstream=None,
            no_upstream=False,
            timeout=None,
            max_connections=None,
            plain=False,
            quiet=False,
            debug=False
        )
        
        config = apply_cli_overrides(config, args)
        
        assert config.port == 8888

    def test_cli_upstream_format(self):
        import argparse
        from proxy.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(["--upstream", "proxy.example.com:8080"])
        
        assert args.upstream == "proxy.example.com:8080"


class TestProxyServer:
    def test_server_start_stop(self):
        from proxy.config import ProxyConfig
        from proxy.server import ProxyServer
        from proxy.logging_utils import logger

        logger.enabled = False

        config = ProxyConfig()
        config.port = 19997
        config.logging.enabled = False

        server = ProxyServer(config)
        thread = threading.Thread(target=server.start)
        thread.start()
        
        time.sleep(0.3)
        assert server.running is True
        
        server.running = False
        thread.join(timeout=2)
        assert server.running is False

    def test_server_binds_to_port(self):
        from proxy.config import ProxyConfig
        from proxy.server import ProxyServer
        from proxy.logging_utils import logger

        logger.enabled = False

        config = ProxyConfig()
        config.port = 19996
        config.logging.enabled = False

        server = ProxyServer(config)
        thread = threading.Thread(target=server.start)
        thread.start()
        
        time.sleep(0.3)
        
        test_socket = socket.socket()
        try:
            test_socket.connect(("127.0.0.1", 19996))
            connected = True
        except:
            connected = False
        finally:
            test_socket.close()
        
        server.running = False
        thread.join(timeout=2)
        
        assert connected is True
