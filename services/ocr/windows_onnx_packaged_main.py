"""Explicit Windows ONNX frozen entrypoint; uses the existing readiness protocol."""

import multiprocessing

from windows_onnx_backend import configure_backend


def main() -> None:
    multiprocessing.freeze_support()
    configure_backend()
    from windows_packaged_main import main as run_server

    run_server()


if __name__ == "__main__":
    main()
