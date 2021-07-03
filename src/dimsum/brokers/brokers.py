from typing import Optional, TextIO, List, Dict, Any, TYPE_CHECKING

import os
import re
import logging
import json
import types
import dataclasses
import ipaddress
import signal
import pathlib
import threading
import multiprocessing
import queue

import watchgod

HANDLED_SIGNALS = (
    signal.SIGINT,  # Unix signal 2. Sent by Ctrl+C.
    signal.SIGTERM,  # Unix signal 15. Sent by `kill <pid>`.
)


log = logging.getLogger("dimsum.broker")


@dataclasses.dataclass(frozen=True)
class ProcessConfig:
    key: str
    target: Optional[Any] = None
    kwargs: Optional[Dict[str, Any]] = None
    watching: Optional[List[str]] = None


if TYPE_CHECKING:
    DirEntry = os.DirEntry[str]


class CustomWatcher(watchgod.DefaultWatcher):
    ignore_dotted_file_regex = r"^\/?(?:\w+\/)*(\.\w+)"
    ignored: List[str] = []

    def __init__(self, root_path: str) -> None:
        for t in self.ignored_file_regexes:
            self.ignored.append(t)
        self.ignored.append(self.ignore_dotted_file_regex)
        self._ignored = tuple(re.compile(r) for r in self.ignored)
        super().__init__(root_path)

    def should_watch_file(self, entry: "DirEntry") -> bool:
        return not any(r.search(entry.name) for r in self._ignored)


class Child(threading.Thread):
    def __init__(
        self, pool: Optional["Pool"] = None, config: Optional[ProcessConfig] = None
    ):
        super().__init__()
        assert pool
        assert config
        self.pool = pool
        self.config = config
        self.process = None
        self.exiting = threading.Event()

        watching = self.config.watching or []
        watch_dirs = {
            pathlib.Path(watch_dir).resolve()
            for watch_dir in watching
            if pathlib.Path(watch_dir).is_dir()
        }
        watch_dirs_set = set(watch_dirs)

        # remove directories that already have a parent watched, so
        # that we don't have duplicated change events
        for watch_dir in watch_dirs:
            for compare_dir in watch_dirs:
                if compare_dir is watch_dir:
                    continue
                if compare_dir in watch_dir.parents:
                    watch_dirs_set.remove(watch_dir)

        log.info("%s: watching: %s", config.key, watch_dirs_set)

        self.watch_dir_set = watch_dirs_set
        self.watchers = []
        for w in watch_dirs_set:
            self.watchers.append(CustomWatcher(str(w)))

    def run(self):
        self.process = self.pool.spawn(self.config)
        self.process.start()

        while not self.exiting.wait(0.25):
            if self.needs_restarting():
                self.restart()

        self.process.terminate()
        self.process.join()

    def restart(self):
        if self.process:
            self.process.terminate()
            self.process.join()

        self.process = self.pool.spawn(self.config)
        self.process.start()

    def needs_restarting(self) -> bool:
        for watcher in self.watchers:
            change = watcher.check()
            if change != set():
                message = "detected file change in '%s'"
                log.warning(message, [c[1] for c in change])
                return True

        return False

    def stop(self):
        self.exiting.set()


class Pool:
    def __init__(self):
        super().__init__()
        self.procs = {}
        self.mp = multiprocessing.get_context("spawn")
        self.queue = self.mp.Queue()
        self.signaled = threading.Event()
        log.info("%d: process-pool", os.getpid())

    def __enter__(self):
        # for sig in HANDLED_SIGNALS:
        #    signal.signal(sig, self.signal_handler)
        return self

    def __exit__(self, type, value, traceback):
        log.info("%d: stopping", os.getpid())
        self.stop()
        return False

    def signal_handler(self, sig: signal.Signals, frame: types.FrameType) -> None:
        log.info("%d: signaled", os.getpid())
        self.signaled.set()

    def spawn(self, config: ProcessConfig) -> multiprocessing.Process:
        log.info("%d: spawn '%s' kwargs=%s", os.getpid(), config.key, config.kwargs)
        kwargs: Dict[str, Any] = {}
        kwargs.update(**config.kwargs)  # type:ignore
        kwargs.update(dict(queue=self.queue))
        return self.mp.Process(target=config.target, kwargs=kwargs, daemon=True)

    def service(self):
        try:
            work = self.queue.get(block=False)
            log.info("work: %s", work)
        except queue.Empty:
            pass

    def remove(self, key: str):
        if key in self.procs:
            log.info("stopping %s", key)
            self.procs[key].stop()
            del self.procs[key]

    def provision(self, config: Optional[ProcessConfig] = None):
        assert config
        assert config.key not in self.procs
        p = Child(pool=self, config=config)
        self.procs[config.key] = p
        p.start()
        return None

    def stop(self):
        for key, p in self.procs.items():
            log.info("%d: joining '%s'", os.getpid(), key)
            p.stop()
        self.procs = {}
