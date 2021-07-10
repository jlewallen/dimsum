import logging

from model import Entity

log = logging.getLogger("dimsum.proxying")


def create(entity: Entity) -> Entity:
    return entity
