"""Windows frozen entrypoint; readiness is proof that this process bound loopback."""

from __future__ import annotations

import json
import multiprocessing
import os
from pathlib import Path

import uvicorn

from app.main import app


class WindowsServer(uvicorn.Server):
    async def startup(self, sockets=None) -> None:
        await super().startup(sockets=sockets)
        if self.started and os.environ.get("YOMIMADO_READY_FILE"):
            path = Path(os.environ["YOMIMADO_READY_FILE"])
            temporary = path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(
                    {
                        "pid": os.getpid(),
                        "instanceId": os.environ["YOMIMADO_SERVICE_INSTANCE"],
                        "port": self.config.port,
                    }
                ),
                encoding="utf-8",
            )
            temporary.replace(path)


def main() -> None:
    multiprocessing.freeze_support()
    WindowsServer(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=int(os.environ.get("YOMIMADO_OCR_PORT", "8766")),
            log_level="warning",
            access_log=False,
            loop="asyncio",
        )
    ).run()


if __name__ == "__main__":
    main()
