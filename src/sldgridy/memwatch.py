"""Memory watch: finds out where the program is when it suddenly takes huge amounts of
memory. Pure Python, Linux only (reads /proc), does nothing elsewhere.

A background thread checks the resident memory every second. From ``first_gb`` on it
writes the Python stacks of all threads to the crash log (again after every further
``step_gb``). At ``limit`` it writes a last report and ends the program, before the
system starts swapping and the kernel kills it anyway (the desktop stays usable; the
automatic backup is offered on the next start).
"""

import faulthandler
import os
import threading
import time
from typing import TextIO

GB = 1024**3


def rss_bytes() -> int | None:
    try:
        with open("/proc/self/statm", encoding="ascii") as f:
            return int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError):
        return None


def total_memory() -> int | None:
    try:
        with open("/proc/meminfo", encoding="ascii") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def default_limit() -> int:
    """Half the RAM, at least 4 GB."""
    total = total_memory() or 8 * GB
    return max(4 * GB, total // 2)


def report(log: TextIO, used: int, note: str) -> None:
    log.write(f"--- Speicher {used / GB:.1f} GB: {note}\n")
    log.flush()
    faulthandler.dump_traceback(log, all_threads=True)
    log.flush()


def start(log: TextIO, first_gb: float = 2.0, step_gb: float = 2.0, limit: int | None = None):
    """Start the watch thread; returns it (None where /proc is missing)."""
    if rss_bytes() is None:
        return None
    hard = limit if limit is not None else default_limit()

    def run() -> None:
        next_report = first_gb * GB
        while True:
            time.sleep(1.0)
            used = rss_bytes()
            if used is None:
                continue
            if used >= hard:
                report(log, used, "Grenze erreicht, Programm wird beendet")
                os._exit(70)
            if used >= next_report:
                report(log, used, "ungewöhnlich hoch")
                next_report = used + step_gb * GB

    thread = threading.Thread(target=run, name="memwatch", daemon=True)
    thread.start()
    return thread
