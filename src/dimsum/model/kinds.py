import model.crypto as crypto


class Kind:
    def __init__(self, identity: crypto.Identity = None, **kwargs):
        super().__init__()
        assert identity
        self.identity: crypto.Identity = identity

    def same(self, other: "Kind") -> bool:
        assert other
        return self.identity.public == other.identity.public

    def __str__(self):
        return "kind<%s>" % (self.identity,)

    def __repr__(self):
        return str(self)
