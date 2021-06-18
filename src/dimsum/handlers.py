from typing import Any

import os
import hashlib
import base64

import movement
import health

from context import *
from reply import *
from game import *
from things import *
from events import *
from world import *

log = logging.getLogger("dimsum")


class WhateverHandlers:
    def __init__(self, bus: bus.EventBus):
        super().__init__()

        @bus.handler(PlayerJoined)
        def handle_player_joined(player: entity.Entity = None, **kwargs):
            log.info("player joined handler: %s %s", player, kwargs)
