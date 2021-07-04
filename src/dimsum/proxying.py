import logging

import model.entity as entity

log = logging.getLogger("dimsum.proxying")


def create(entity: entity.Entity) -> entity.Entity:
    return entity
