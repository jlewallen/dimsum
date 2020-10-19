import logging
import props

log = logging.getLogger("dimsum")


class EdibleMixin:
    def consumed(self, player):
        FoodFields = [
            props.SumFields("sugar"),
            props.SumFields("fat"),
            props.SumFields("protein"),
            props.SumFields("toxicity"),
            props.SumFields("caffeine"),
            props.SumFields("alcohol"),
            props.SumFields("nutrition"),
            props.SumFields("vitamins"),
        ]
        changes = props.merge_dictionaries(
            player.details.map, self.details.map, FoodFields
        )
        log.info("merged %s" % (changes,))
        player.details.update(changes)
