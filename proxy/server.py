"""HTTP Proxy Server with multithreading support."""

import socket
import threading
from typing import Optional

from proxy.config import ProxyConfig
from proxy.logging_utils import logger
from proxy.proxy_handler import ProxyHandler


class ProxyServer:
    def __init__(self, config: Optional[ProxyConfig] = None):
        self.config = config or ProxyConfig()
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.threads: list = []

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.settimeout(1)

        try:
            self.server_socket.bind((self.config.host, self.config.port))
            self.server_socket.listen(self.config.threads.max_connections)
        except OSError as e:
            logger.error(f"Failed to bind to {self.config.host}:{self.config.port}: {e}")
            raise

        self.running = True
        logger.info(
            f"Proxy server starting on {self.config.host}:{self.config.port}"
        )
        logger.info(
            f"Max connections: {self.config.threads.max_connections}, "
            f"Timeout: {self.config.threads.timeout}s"
        )

        if self.config.upstream_proxy.enabled:
            logger.info(
                f"Upstream proxy: {self.config.upstream_proxy.host}:{self.config.upstream_proxy.port}"
            )
        else:
            logger.info("Direct connection (no upstream proxy)")

        self._accept_loop()

    def stop(self):
        logger.info("Stopping proxy server...")
        self.running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

        for thread in self.threads:
            thread.join(timeout=1)

        logger.success("Proxy server stopped")

    def _accept_loop(self):
        while self.running:
            try:
                client_socket, client_addr = self.server_socket.accept()
                client_socket.settimeout(self.config.threads.timeout)

                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_addr),
                    daemon=True,
                )
                thread.start()
                self.threads.append(thread)

                self._cleanup_threads()

            except socket.timeout:
                continue
            except OSError:
                if self.running:
                    logger.error("Socket error during accept")
                break
            except Exception as e:
                if self.running:
                    logger.error(f"Error in accept loop: {e}")

    def _handle_client(self, client_socket: socket.socket, client_addr):
        handler = ProxyHandler(client_socket, client_addr, self.config)
        handler.handle()

    def _cleanup_threads(self):
        self.threads = [t for t in self.threads if t.is_alive()]
