from loggers import get_logger
from model import Entity

log = get_logger("dimsum.proxying")


def create(entity: Entity) -> Entity:
    return entity
