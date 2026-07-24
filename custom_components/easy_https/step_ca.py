"""step-ca server configuration and process manager for Easy HTTPS integration."""

import asyncio
import json
import logging
import os
import shutil
import subprocess
from typing import Optional, Dict, Any
from aiohttp import web
import ssl

_LOGGER = logging.getLogger(__name__)


class StepCAManager:
    """Manages the step-ca server process or embedded standalone fallback."""

    def __init__(self, config_dir: str, listen_address: str = ":8443", port: int = 8443):
        self.config_dir = config_dir
        self.listen_address = listen_address
        self.port = port
        self.process: Optional[asyncio.subprocess.Process] = None
        self.standalone_app: Optional[web.Application] = None
        self.standalone_runner: Optional[web.AppRunner] = None
        self.standalone_site: Optional[web.TCPSite] = None

    @property
    def step_ca_path(self) -> Optional[str]:
        """Find step-ca executable on the system PATH."""
        return shutil.which("step-ca")

    @property
    def is_running(self) -> bool:
        """Return True if the step-ca process or standalone server is currently running."""
        if self.process is not None and self.process.returncode is None:
            return True
        return self.standalone_site is not None

    def is_installed(self) -> bool:
        """Return True if step-ca binary is installed and executable."""
        return self.step_ca_path is not None

    def prepare_config(
        self,
        intermediate_cert_path: str,
        intermediate_key_path: str,
        root_cert_path: str,
    ) -> str:
        """Create step-ca ca.json configuration pointing to Secondary Intermediate CA."""
        os.makedirs(self.config_dir, exist_ok=True)
        config_path = os.path.join(self.config_dir, "ca.json")
        db_path = os.path.join(self.config_dir, "db")

        ca_config = {
            "root": root_cert_path,
            "crt": intermediate_cert_path,
            "key": intermediate_key_path,
            "address": self.listen_address,
            "dnsNames": ["localhost", "127.0.0.1"],
            "logger": {"format": "text"},
            "db": {
                "type": "badgerv2",
                "dataSource": db_path,
            },
            "authority": {
                "type": "stepca",
                "provisioners": [
                    {
                        "type": "ACME",
                        "name": "acme",
                        "options": {
                            "x509": {
                                "minDur": "24h",
                                "maxDur": "2160h",
                                "defaultDur": "2160h"
                            }
                        }
                    }
                ]
            },
            "tls": {
                "cipherSuites": [
                    "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
                    "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
                    "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256"
                ],
                "minVersion": 1.2,
                "maxVersion": 1.3
            }
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(ca_config, f, indent=2)

        _LOGGER.info("step-ca configuration written to %s", config_path)
        return config_path

    async def async_start(
        self,
        config_path: str,
        intermediate_cert_path: str = "",
        intermediate_key_path: str = "",
    ) -> bool:
        """
        Start step-ca server. If step-ca binary is not present,
        fallback to starting a standalone embedded CA server daemon on port 8443.
        """
        binary = self.step_ca_path

        if binary:
            if self.process and self.process.returncode is None:
                _LOGGER.info("step-ca server binary is already running (PID: %s)", self.process.pid)
                return True

            cmd = [binary, config_path, "--password-file", "/dev/null"]
            _LOGGER.info("Starting native step-ca binary: %s", " ".join(cmd))

            try:
                self.process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )
            except Exception as err:
                _LOGGER.error("Failed to start step-ca binary, attempting standalone fallback: %s", err)
            else:
                # step-ca validates its config on startup; give it a moment to fail fast
                await asyncio.sleep(1)
                if self.process.returncode is None:
                    asyncio.get_running_loop().create_task(self._drain_stderr(self.process))
                    _LOGGER.info("step-ca server binary started with PID %s", self.process.pid)
                    return True
                stderr = await self.process.stderr.read()
                _LOGGER.error(
                    "step-ca exited immediately (code %s): %s — attempting standalone fallback",
                    self.process.returncode,
                    stderr.decode(errors="replace").strip(),
                )
                self.process = None

        # Standalone fallback mode
        _LOGGER.info("Starting standalone embedded CA server on port %s...", self.port)
        return await self._start_standalone_server(intermediate_cert_path, intermediate_key_path)

    async def _drain_stderr(self, process: asyncio.subprocess.Process) -> None:
        """Consume step-ca stderr so the pipe never fills, logging output at debug level."""
        try:
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                _LOGGER.debug("step-ca: %s", line.decode(errors="replace").rstrip())
        except Exception:
            pass

    async def _start_standalone_server(
        self, intermediate_cert_path: str, intermediate_key_path: str
    ) -> bool:
        """Start an embedded asyncio standalone CA server."""
        if self.standalone_site:
            _LOGGER.info("Standalone CA server is already running.")
            return True

        if not os.path.exists(intermediate_cert_path) or not os.path.exists(intermediate_key_path):
            _LOGGER.error("Cannot start standalone CA server: missing intermediate cert or key.")
            return False

        app = web.Application()

        async def handle_root_ca(request: web.Request) -> web.Response:
            """Provide CA certificate info endpoint for standalone clients."""
            with open(intermediate_cert_path, "r", encoding="utf-8") as f:
                content = f.read()
            return web.Response(text=content, content_type="application/x-pem-file")

        async def handle_acme_directory(request: web.Request) -> web.Response:
            """Provide ACME directory placeholder for standalone clients."""
            base_url = f"https://{request.host}"
            directory = {
                "newNonce": f"{base_url}/acme/new-nonce",
                "newAccount": f"{base_url}/acme/new-account",
                "newOrder": f"{base_url}/acme/new-order",
                "revokeCert": f"{base_url}/acme/revoke-cert",
                "keyChange": f"{base_url}/acme/key-change",
            }
            return web.json_response(directory)

        app.router.add_get("/ca/intermediate.crt", handle_root_ca)
        app.router.add_get("/acme/directory", handle_acme_directory)

        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(certfile=intermediate_cert_path, keyfile=intermediate_key_path)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=self.port, ssl_context=ssl_ctx)
        await site.start()

        self.standalone_app = app
        self.standalone_runner = runner
        self.standalone_site = site
        _LOGGER.info("Standalone CA server running on https://0.0.0.0:%s", self.port)
        return True

    async def async_stop(self) -> None:
        """Stop step-ca server process or standalone server gracefully."""
        if self.process:
            if self.process.returncode is None:
                _LOGGER.info("Stopping step-ca process (PID: %s)...", self.process.pid)
                self.process.terminate()
                try:
                    async with asyncio.timeout(5):
                        await self.process.wait()
                except asyncio.TimeoutError:
                    _LOGGER.warning("step-ca did not terminate gracefully, killing process.")
                    self.process.kill()
            self.process = None

        if self.standalone_site:
            _LOGGER.info("Stopping standalone CA server...")
            await self.standalone_runner.cleanup()
            self.standalone_site = None
            self.standalone_runner = None
            self.standalone_app = None
