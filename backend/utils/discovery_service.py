"""
VisionNav UDP & LAN Auto-Discovery Service.
Allows Flutter mobile app on the same Wi-Fi network to automatically locate
and connect to the VisionNav backend server without manual IP/port configuration.
"""
import socket
import json
import time
import threading
from typing import Optional, List
from backend.utils.logger import get_logger

logger = get_logger("DiscoveryService")

DISCOVERY_PORT = 8002

class DiscoveryServer:
    def __init__(self, target_port: int = 8000):
        self.target_port = target_port
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._sock: Optional[socket.socket] = None

    def start(self, port: Optional[int] = None):
        if port is not None:
            self.target_port = port
        if self.running:
            return

        self.running = True
        self._thread = threading.Thread(target=self._run_loop, name="VisionNavDiscovery", daemon=True)
        self._thread.start()
        logger.info(f"Auto-Discovery Service active on UDP port {DISCOVERY_PORT} (Serving HTTP port {self.target_port})")

    def stop(self):
        self.running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
        logger.info("Auto-Discovery Service stopped.")

    def set_target_port(self, port: int):
        self.target_port = port

    def _get_local_ips(self) -> List[str]:
        ips = []
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                ips.append(ip)
        except Exception:
            pass
        return ips

    def _get_broadcast_targets(self) -> List[str]:
        targets = {"<broadcast>", "255.255.255.255", "10.0.2.255"}
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and "." in ip:
                prefix = ".".join(ip.split(".")[:3])
                targets.add(f"{prefix}.255")
        except Exception:
            pass
        return list(targets)

    def _run_loop(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            except Exception:
                pass
            self._sock.bind(("0.0.0.0", DISCOVERY_PORT))
            self._sock.settimeout(1.0)
        except Exception as e:
            logger.error(f"Could not bind UDP discovery server to port {DISCOVERY_PORT}: {e}")
            return

        last_broadcast = 0.0

        while self.running:
            now = time.time()
            local_ips = self._get_local_ips()
            primary_ip = local_ips[0] if local_ips else "localhost"

            payload_dict = {
                "service": "VisionNav",
                "status": "online",
                "name": "VisionNav Backend Server",
                "version": "1.0.0",
                "port": self.target_port,
                "ip": primary_ip
            }
            payload_bytes = json.dumps(payload_dict).encode("utf-8")

            # Broadcast beacon every 1.5 seconds to all broadcast targets
            if now - last_broadcast >= 1.5:
                broadcast_targets = self._get_broadcast_targets()
                for target in broadcast_targets:
                    try:
                        self._sock.sendto(payload_bytes, (target, DISCOVERY_PORT))
                    except Exception:
                        pass
                last_broadcast = now

            # Listen for discovery request packets from client app
            try:
                data, addr = self._sock.recvfrom(1024)
                if data:
                    text = data.decode("utf-8", errors="ignore")
                    if "VISIONNAV_DISCOVER" in text or "DISCOVER" in text:
                        self._sock.sendto(payload_bytes, addr)
            except socket.timeout:
                pass
            except Exception as e:
                if self.running:
                    logger.debug(f"Discovery server loop exception: {e}")

discovery_server = DiscoveryServer()
