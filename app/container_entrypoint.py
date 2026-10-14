import importlib
import os
import sys
from pathlib import Path


def _posix_call(function: str, *args: object) -> None:
    getattr(os, function)(*args)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(2)
    data = Path("/data")
    data.mkdir(parents=True, exist_ok=True)
    pwd = importlib.import_module("pwd")
    account = pwd.getpwnam("appuser")
    _posix_call("chown", data, account.pw_uid, account.pw_gid)
    _posix_call("setgid", account.pw_gid)
    _posix_call("setuid", account.pw_uid)
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
