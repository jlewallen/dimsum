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


def generate_identity():
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    encoded_private = base64.b64encode(private_bytes).decode("utf-8")

    encoded_public = get_public_from_private_bytes(encoded_private)

    return Identity(public=encoded_public, private=encoded_private)


class Identity:
    def __init__(self, **kwargs):
        self.private = kwargs["private"]

        if "public" in kwargs:
            self.public = kwargs["public"]
        else:
            self.public = get_public_from_private_bytes(self.private)

        if "signature" in kwargs:
            self.signature = kwargs["signature"]
        else:
            self.signature = None

    def saved(self):
        return {"private": self.private, "signature": self.signature}

    def private_key(self):
        return get_private_key(self.private)

    def sign(self, other: "Identity"):
        private_key = self.private_key()
        signature_bytes = private_key.sign(other.public.encode("utf-8"))
        signature = base64.b64encode(signature_bytes).decode("utf-8")
        return Identity(private=other.private, public=other.public, signature=signature)


def generate_identity_from(other: Identity):
    return other.sign(generate_identity())


def test():
    keys = generate_identity()
    print(keys.public)
    print(keys.private)
