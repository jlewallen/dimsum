from typing import Optional, Dict

import time
import logging
import entity
import props
import game
import bus

DefaultMoveVerb = "walk"
log = logging.getLogger("dimsum")


class World(entity.Entity):
    def __init__(self, bus: bus.EventBus, context_factory):
        super().__init__()
        self.details = props.Details("World", desc="Ya know, everything")
        self.key = "world"
        self.bus = bus
        self.context_factory = context_factory
        self.entities: Dict[str, entity.Entity] = {}
        self.destroyed: Dict[str, entity.Entity] = {}

    def register(self, entity: entity.Entity):
        self.entities[entity.key] = entity

    def unregister(self, entity: entity.Entity):
        entity.destroy()
        del self.entities[entity.key]
        self.destroyed[entity.key] = entity

    def empty(self):
        return len(self.entities.keys()) == 0

    def items(self):
        return [e for e in self.entities.values() if isinstance(e, game.Item)]

    def areas(self):
        return [e for e in self.entities.values() if isinstance(e, game.Area)]

    def people(self):
        return [e for e in self.entities.values() if isinstance(e, game.Person)]

    def players(self):
        return [e for e in self.entities.values() if isinstance(e, game.Player)]

    def find_person_by_name(self, name):
        for person in self.people():
            if person.details.name == name:
                return person
        return None

    def welcome_area(self):
        return self.areas()[0]

    def look(self, player: game.Player):
        area = self.find_player_area(player)
        return area.look(player)

    def find_entity_area(self, entity: entity.Entity):
        for area in self.areas():
            if area.contains(entity) or area.occupying(entity):
                return area
        return None

    def find_player_area(self, player: game.Player):
        return self.find_entity_area(player)

    def contains(self, key):
        return key in self.entities

    def find(self, key):
        return self.entities[key]

    def resolve(self, keys):
        return [self.entities[key] for key in keys]

    def add_area(self, area: game.Area):
        self.register(area)
        for entity in area.entities():
            self.register(entity)

    def build_new_area(
        self,
        player: game.Player,
        fromArea: game.Area,
        entry: game.Item,
        verb: str = DefaultMoveVerb,
    ):
        log.info("building new area")

        theWayBack = game.Item(creator=player, details=entry.details.clone())
        theWayBack.link_area(fromArea, verb=verb)

        area = game.Area(
            creator=player,
            details=props.Details(
                "A pristine, new place.",
                desc="Nothing seems to be here, maybe you should decorate?",
            ),
        )
        area.add_item(theWayBack)
        self.add_area(area)
        return area

    def search_hands(self, player: game.Player, whereQ: str):
        return player.find(whereQ)

    def search_floor(self, player: game.Player, whereQ: str):
        area = self.find_player_area(player)
        return area.find(whereQ)

    def search(self, player: game.Player, whereQ: str, unheld=None, **kwargs):
        log.info("%s", player)
        area = self.find_player_area(player)
        log.info("%s", area)

        order = [player.find, area.find]

        if unheld:
            order = [area.find, player.find]

        for fn in order:
            item = fn(whereQ)
            if item:
                return item

        return None

    async def perform(self, player: game.Player, action):
        area = self.find_player_area(player)
        ctx = game.Ctx(self.context_factory, world=self, person=player, area=area)
        return await action.perform(ctx, self, player)

    async def tick(self, now: Optional[float] = None):
        if now is None:
            now = time.time()
        return await self.everywhere("tick", time=now)

    async def everywhere(self, name: str, **kwargs):
        log.info("everywhere:%s %s", name, kwargs)
        everything = list(self.entities.values())
        for entity in everything:
            behaviors = entity.get_behaviors(name)
            if len(behaviors) > 0:
                log.info("tick: %s", entity)
                area = self.find_entity_area(entity)
                ctx = game.Ctx(
                    self.context_factory, world=self, area=area, entity=entity, **kwargs
                )
                await ctx.hook(name)

    def __str__(self):
        return "$world"

    def __repr__(self):
        return "$world"
