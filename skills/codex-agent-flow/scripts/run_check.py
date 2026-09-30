#!/usr/bin/env python3
"""Run an explicitly supplied local check, preserving full logs and bounded output."""
import argparse
from collections import deque
import datetime as dt
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time


def stop_group(proc):
    # Kill only the process group this wrapper created, including surviving children.
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    time.sleep(0.2)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def excerpt(path):
    errors, seen, tail = [], set(), deque(maxlen=12)
    pattern = re.compile(r'error|failed|panic|traceback|fatal', re.I)
    with path.open(errors='replace') as stream:
        # Bounded reads also handle a process emitting one enormous line.
        while chunk := stream.readline(4096):
            line = chunk.rstrip()[:240]
            tail.append(line)
            if len(errors) < 8 and pattern.search(line) and line not in seen:
                errors.append(line)
                seen.add(line)
    return errors, list(tail)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cwd', type=Path, default=Path.cwd())
    parser.add_argument('--timeout', type=float, required=True,
                        help='Seconds; choose for this local check, not hardware')
    parser.add_argument('--log-dir', type=Path,
                        help='Parent directory; each invocation creates a unique subdirectory')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or args.timeout <= 0 or not args.cwd.is_dir():
        parser.error('Supply a command, positive timeout, and existing cwd')
    if args.log_dir:
        args.log_dir.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='codex-flow-', dir=args.log_dir))
    log = folder / 'output.log'
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    start = time.monotonic()
    rc, status, proc = 127, 'ERROR', None
    try:
        with log.open('wb') as output:
            proc = subprocess.Popen(command, cwd=args.cwd, stdout=output,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            try:
                rc = proc.wait(timeout=args.timeout)
                status = 'PASS' if rc == 0 else 'FAIL'
            except subprocess.TimeoutExpired:
                stop_group(proc)
                rc, status = 124, 'TIMEOUT'
            except KeyboardInterrupt:
                stop_group(proc)
                rc, status = 130, 'INTERRUPTED'
    except OSError as exc:
        with log.open('a') as output:
            output.write(str(exc) + '\n')
    report = dict(status=status, exit_code=rc, command=command,
                  cwd=str(args.cwd.resolve()), started_at=started,
                  elapsed_seconds=round(time.monotonic() - start, 3), log=str(log))
    (folder / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f"{status} exit={rc} elapsed={report['elapsed_seconds']}s")
    print(f'log: {log}\nresult: {folder / "result.json"}')
    if rc != 0:
        errors, tail = excerpt(log)
        print('-- error excerpts --')
        print('\n'.join(errors))
        print('-- tail --')
        print('\n'.join(tail))
    return rc if rc >= 0 else 128 - rc


if __name__ == '__main__':
    raise SystemExit(main())
