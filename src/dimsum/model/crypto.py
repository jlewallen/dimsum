import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def get_private_key(encoded_private):
    return ed25519.Ed25519PrivateKey.from_private_bytes(
        base64.b64decode(encoded_private.encode("utf-8"))
    )


def get_public_from_private_bytes(encoded_private):
    loaded_private_key = get_private_key(encoded_private)
    public_key = loaded_private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(public_bytes).decode("utf-8")


class Identity:
    def __init__(self, public=None, private=None, signature=None, **kwargs):
        # TODO apply Acls here for reads?
        self.private = private
        self.public = public if public else get_public_from_private_bytes(self.private)
        self.signature = signature

    def private_key(self):
        return get_private_key(self.private)

    def sign(self, other: "Identity") -> "Identity":
        private_key = self.private_key()
        signature_bytes = private_key.sign(other.public.encode("utf-8"))
        signature = base64.b64encode(signature_bytes).decode("utf-8")
        return Identity(private=other.private, public=other.public, signature=signature)

    def __str__(self):
        return "identity<%s>" % (self.public,)

    def __repr__(self):
        return str(self)


def generate_identity() -> Identity:
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    encoded_private = base64.b64encode(private_bytes).decode("utf-8")

    encoded_public = get_public_from_private_bytes(encoded_private)

    return Identity(public=encoded_public, private=encoded_private)


def generate_identity_from(other: Identity):
    return other.sign(generate_identity())


def generate(creator=None) -> Identity:
    if creator:
        return creator.sign(generate_identity())
    return generate_identity()
