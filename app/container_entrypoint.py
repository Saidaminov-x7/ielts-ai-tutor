import os
import pwd
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(2)
    data = Path("/data")
    data.mkdir(parents=True, exist_ok=True)
    account = pwd.getpwnam("appuser")
    os.chown(data, account.pw_uid, account.pw_gid)
    os.setgid(account.pw_gid)
    os.setuid(account.pw_uid)
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
