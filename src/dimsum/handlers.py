from typing import Any

import os
import hashlib
import base64

import bus
import context

import model.entity as entity

import model.scopes.movement as movement
import model.scopes.health as health

from model.events import *

log = logging.getLogger("dimsum")


class WhateverHandlers:
    def __init__(self, bus: bus.EventBus):
        super().__init__()

        @bus.handler(PlayerJoined)
        def handle_player_joined(player: entity.Entity = None, **kwargs):
            log.info("player joined handler: %s %s", player, kwargs)
