"""Read-only inspection commands plus explicit registry initialization."""

import argparse
import json
import sys
from pathlib import Path

from .canonical import strict_json
from .errors import RegistryError
from .store import init_registry, verify_registry
from .summary import registry_summary


def main(argv=None):
    parser = argparse.ArgumentParser(prog="trader-registry")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "verify", "checkpoint", "summary"):
        command = commands.add_parser(name)
        command.add_argument("path")
        if name in ("verify", "summary"):
            command.add_argument("--checkpoint", required=name == "summary")
    args = parser.parse_args(argv)
    try:
        cp_file = getattr(args, "checkpoint", None)
        checkpoint = strict_json(Path(cp_file).read_text()) if cp_file else None
        if args.command == "init":
            output = init_registry(args.path)
        elif args.command == "summary":
            output = registry_summary(args.path, checkpoint)
        else:
            output = verify_registry(args.path, checkpoint)
        print(json.dumps(output, ensure_ascii=False, allow_nan=False))
        return 0
    except (RegistryError, OSError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "code": getattr(exc, "code", "REGISTRY_CHECKPOINT_MISMATCH"),
                    "detail": getattr(exc, "detail", str(exc)),
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
