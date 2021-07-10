from typing import Optional

from .crypto import Identity


class Kind:
    def __init__(self, identity: Optional[Identity] = None, **kwargs):
        super().__init__()
        assert identity
        self.identity: Identity = identity

    def same(self, other: "Kind") -> bool:
        assert other
        return self.identity.public == other.identity.public

    def __str__(self):
        return "kind<%s>" % (self.identity,)

    def __repr__(self):
        return str(self)
