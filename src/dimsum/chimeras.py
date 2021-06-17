import logging

import context
import crypto
import entity
import copy

log = logging.getLogger("dimsum")


class Chimera(entity.Entity, entity.IgnoreExtraConstructorArguments):
    def __init__(self, chimeras=None, **kwargs):
        super().__init__(**kwargs)
        self.chimeras = chimeras if chimeras else {}

    def make(self, ctor):
        key = ctor.__name__

        log.info("splitting chimera: %s", key)
        child = (
            ctor(chimera=self, **self.chimeras[key])
            if key in self.chimeras
            else ctor(chimera=self)
        )
        return child

    def update(self, child):
        key = child.__class__.__name__
        data = child.__dict__
        del data["chimera"]
        log.info("updating chimera: %s %s", key, data)
        self.chimeras[key] = copy.deepcopy(data)


class Spawned:
    def __init__(self, chimera: Chimera = None, **kwargs):
        super().__init__()
        assert chimera
        self.chimera: Chimera = chimera

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.save()

    def save(self):
        self.chimera.update(self)
