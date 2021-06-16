import crypto


class Kind:
    def __init__(self, identity: crypto.Identity = None, **kwargs):
        self.identity: crypto.Identity = (
            identity if identity else crypto.generate_identity()
        )

    def same(self, other: "Kind") -> bool:
        if other is None:
            return False
        return self.identity.public == other.identity.public

    def __str__(self):
        return "kind<%s>" % (self.identity,)

    def __repr__(self):
        return str(self)
