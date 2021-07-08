import logging

import model.finders as finders
import model.properties as properties
import model.scopes.movement as movement
import plugins.default.actions as actions
import transformers

log = logging.getLogger("dimsum")


class Default(transformers.Base):
    def modify_hard_to_see(self, args):
        return actions.ModifyHardToSee(item=finders.AnyHeldItem(), hard_to_see=True)

    def modify_easy_to_see(self, args):
        return actions.ModifyHardToSee(item=finders.AnyHeldItem(), hard_to_see=False)

    def modify_field(self, args):
        field = str(args[0])
        value = args[1]
        return actions.ModifyField(item=finders.AnyHeldItem(), field=field, value=value)
