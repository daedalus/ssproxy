"""HTTP Proxy Handler - handles HTTP requests and CONNECT tunneling."""

import select
import socket
from dataclasses import dataclass
from typing import Optional, Tuple

from proxy.config import ProxyConfig
from proxy.logging_utils import logger


@dataclass
class ProxyHandler:
    client_socket: socket.socket
    client_addr: Tuple[str, int]
    config: ProxyConfig

    def handle(self):
        try:
            request_data = self._receive_request()
            if not request_data:
                return

            request_line = request_data.split(b"\r\n")[0].decode("utf-8", errors="ignore")
            parts = request_line.split(" ")

            if len(parts) < 2:
                self._send_error(400, "Bad Request")
                return

            method = parts[0]
            path = parts[1]

            if method == "CONNECT":
                self._handle_connect(path)
            elif method in ("GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"):
                self._handle_http_request(method, path, request_data)
            else:
                self._send_error(405, "Method Not Allowed")
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self._send_error(500, "Internal Server Error")
        finally:
            try:
                self.client_socket.close()
            except Exception:
                pass

    def _receive_request(self) -> bytes:
        data = b""
        try:
            while True:
                chunk = self.client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\r\n\r\n" in data:
                    break
        except socket.timeout:
            pass
        except Exception as e:
            logger.debug(f"Error receiving request: {e}")
        return data

    def _handle_connect(self, path: str):
        try:
            host, port_str = path.split(":")
            port = int(port_str)
        except (ValueError, IndexError):
            self._send_error(400, "Invalid CONNECT request")
            return

        logger.log_connect(host, port, self.client_addr[0])

        if self.config.upstream_proxy.enabled:
            self._tunnel_through_upstream(host, port)
        else:
            self._direct_tunnel(host, port)

    def _direct_tunnel(self, host: str, port: int):
        try:
            server_socket = socket.create_connection(
                (host, port), timeout=self.config.threads.timeout
            )
        except Exception as e:
            logger.error(f"Failed to connect to {host}:{port}: {e}")
            self._send_error(502, "Bad Gateway")
            return

        self._send_response(200, "Connection Established")

        logger.log_connect_success(host, port, self.client_addr[0])

        self._tunnel_data(self.client_socket, server_socket, host, port)

    def _tunnel_through_upstream(self, host: str, port: int):
        upstream = self.config.upstream_proxy
        server_socket = None
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.settimeout(self.config.threads.timeout)
            server_socket.connect((upstream.host, upstream.port))

            if upstream.auth.enabled:
                auth_string = f"{upstream.auth.username}:{upstream.auth.password}"
                import base64

                credentials = base64.b64encode(auth_string.encode()).decode()
                connect_request = (
                    f"CONNECT {host}:{port} HTTP/1.1\r\n"
                    f"Host: {host}:{port}\r\n"
                    f"Proxy-Authorization: Basic {credentials}\r\n"
                    f"\r\n"
                )
            else:
                connect_request = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n"

            server_socket.sendall(connect_request.encode())

            response = b""
            while b"\r\n\r\n" not in response:
                chunk = server_socket.recv(4096)
                if not chunk:
                    break
                response += chunk

            if b"200" not in response.split(b"\r\n")[0]:
                logger.error(f"Upstream proxy rejected connection: {response}")
                self._send_error(502, "Bad Gateway")
                server_socket.close()
                return

            self._send_response(200, "Connection Established")

            logger.log_connect_success(host, port, self.client_addr[0])

            self._tunnel_data(self.client_socket, server_socket, host, port)

        except Exception as e:
            logger.error(f"Tunnel through upstream failed: {e}")
            self._send_error(502, "Bad Gateway")
            if server_socket is not None:
                server_socket.close()

    def _tunnel_data(
        self,
        client: socket.socket,
        server: socket.socket,
        target_host: str,
        target_port: int,
    ):
        try:
            while True:
                r, _, _ = select.select([client, server], [], [], 30)
                if not r:
                    break

                for sock in r:
                    try:
                        data = sock.recv(8192)
                        if not data:
                            return

                        if sock is client:
                            server.sendall(data)
                        else:
                            client.sendall(data)
                    except Exception:
                        return
        except Exception:
            pass
        finally:
            try:
                client.close()
            except Exception:
                pass
            try:
                server.close()
            except Exception:
                pass

    def _handle_http_request(self, method: str, path: str, request_data: bytes):
        headers_end = request_data.find(b"\r\n\r\n")
        headers = request_data[:headers_end].decode("utf-8", errors="ignore")
        body = request_data[headers_end + 4 :] if headers_end != -1 else b""

        logger.log_request_line(method, path, self.client_addr[0])

        if self.config.logging.show_request_body and body:
            logger.request(f"Body ({len(body)} bytes): {body[:200]}")

        if self.config.upstream_proxy.enabled:
            self._forward_to_upstream(method, path, request_data)
        else:
            self._forward_direct(method, path, headers, body)

    def _extract_host(self, request_line: str) -> Optional[str]:
        parts = request_line.split(" ")
        if len(parts) < 3:
            return None

        url = parts[1]
        if url.startswith("http://"):
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return parsed.netloc or parsed.hostname
        return None

    def _forward_direct(self, method: str, path: str, headers: str, body: bytes):
        host = self._parse_host_from_headers(headers)
        if not host:
            self._send_error(400, "Host header missing")
            return

        try:
            host, port = self._split_host_port(host)
        except ValueError:
            self._send_error(400, "Invalid host")
            return

        server_socket = None
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.settimeout(self.config.threads.timeout)
            server_socket.connect((host, port))

            from urllib.parse import urlparse

            parsed = urlparse(path)
            if parsed.path:
                request_path = parsed.path
                if parsed.query:
                    request_path += "?" + parsed.query
            else:
                request_path = "/"

            modified_headers = self._remove_proxy_headers(headers)
            request_lines = modified_headers.split("\r\n")

            has_connection_header = any(h.lower().startswith("connection:") for h in request_lines)
            if not has_connection_header:
                request_lines.append("Connection: close")

            request_lines[0] = f"{method} {request_path} HTTP/1.1"
            modified_request = "\r\n".join(request_lines).encode()

            server_socket.sendall(modified_request + b"\r\n" + body)

            self._relay_response(server_socket, host, port)

        except socket.timeout:
            logger.error(f"Connection to {host}:{port} timed out")
            self._send_error(504, "Gateway Timeout")
        except Exception as e:
            logger.error(f"Forward direct failed: {e}")
            self._send_error(502, "Bad Gateway")
        finally:
            if server_socket:
                server_socket.close()

    def _forward_to_upstream(self, method: str, path: str, request_data: bytes):
        upstream = self.config.upstream_proxy

        server_socket = None
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            server_socket.settimeout(self.config.threads.timeout)

            server_socket.connect((upstream.host, upstream.port))

            headers_end = request_data.find(b"\r\n\r\n")
            headers = request_data[:headers_end].decode("utf-8", errors="ignore")
            body = request_data[headers_end + 4 :] if headers_end != -1 else b""

            modified_headers = self._remove_proxy_headers(headers)
            request_lines = modified_headers.split("\r\n")

            url = self._get_url_from_request_line(request_lines[0], headers)
            request_lines[0] = f"{method} {url} HTTP/1.1"

            has_connection_header = any(h.lower().startswith("connection:") for h in request_lines)
            if not has_connection_header:
                request_lines.append("Connection: close")

            if upstream.auth.enabled:
                import base64

                auth_string = f"{upstream.auth.username}:{upstream.auth.password}"
                credentials = base64.b64encode(auth_string.encode()).decode()
                for i, line in enumerate(request_lines):
                    if line.lower().startswith("proxy-authorization:"):
                        del request_lines[i]
                        break
                request_lines.insert(1, f"Proxy-Authorization: Basic {credentials}")

            full_request = "\r\n".join(request_lines).encode() + b"\r\n\r\n" + body
            server_socket.sendall(full_request)

            self._relay_response(server_socket, upstream.host, upstream.port)

        except socket.timeout:
            logger.error("Upstream proxy connection timed out")
            self._send_error(504, "Gateway Timeout")
        except Exception as e:
            logger.error(f"Forward to upstream failed: {e}")
            self._send_error(502, "Bad Gateway")
        finally:
            if server_socket:
                server_socket.close()

    def _parse_host_from_headers(self, headers: str) -> Optional[str]:
        for line in headers.split("\r\n"):
            if line.lower().startswith("host:"):
                return line.split(":", 1)[1].strip()
        return None

    def _split_host_port(self, host: str) -> Tuple[str, int]:
        if ":" in host:
            parts = host.rsplit(":", 1)
            return parts[0], int(parts[1])
        return host, 80

    def _remove_proxy_headers(self, headers: str) -> str:
        result = []
        for line in headers.split("\r\n"):
            lower_line = line.lower()
            if not any(h in lower_line for h in ["proxy-", "connection:", "keep-alive"]):
                result.append(line)
        return "\r\n".join(result)

    def _get_url_from_request_line(self, request_line: str, headers: str) -> str:
        parts = request_line.split(" ")
        if len(parts) >= 2:
            url = parts[1]
            if url.startswith("http://") or url.startswith("https://"):
                return url
        host = self._parse_host_from_headers(headers)
        if host:
            return f"http://{host}{parts[1] if len(parts) >= 2 else '/'}"
        return "/"

    def _relay_response(self, server_socket: socket.socket, host: str, port: int):
        headers_logged = False
        try:
            response_data = b""
            while True:
                try:
                    chunk = server_socket.recv(8192)
                    if not chunk:
                        break
                    response_data += chunk
                    self.client_socket.sendall(chunk)

                    if not headers_logged and b"\r\n\r\n" in response_data:
                        header_end = response_data.find(b"\r\n\r\n")
                        first_line = (
                            response_data[:header_end]
                            .split(b"\r\n")[0]
                            .decode("utf-8", errors="ignore")
                        )
                        parts = first_line.split(" ")
                        if len(parts) >= 2:
                            try:
                                status_code = int(parts[1])
                                logger.log_response_line(
                                    status_code,
                                    parts[2] if len(parts) > 2 else "",
                                    self.client_addr[0],
                                )
                                headers_logged = True
                            except ValueError:
                                pass
                except socket.timeout:
                    break
        except Exception as e:
            logger.debug(f"Error relaying response: {e}")

    def _send_response(self, status_code: int, reason: str):
        response = f"HTTP/1.1 {status_code} {reason}\r\n\r\n"
        try:
            self.client_socket.sendall(response.encode())
        except Exception:
            pass

    def _send_error(self, status_code: int, reason: str):
        response = f"HTTP/1.1 {status_code} {reason}\r\n"
        response += "Content-Length: 0\r\n"
        response += "Connection: close\r\n\r\n"
        try:
            self.client_socket.sendall(response.encode())
        except Exception:
            pass
        logger.log_response_line(status_code, reason, self.client_addr[0])
