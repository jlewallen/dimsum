from lark import Lark


def create_parser():
    l = Lark(
        """
        start: look | obliterate | drop | hold | make | go | remember | modify | eat | drink | home | stimulate | call | forget

        _WS:        WS
        TEXT:       (WORD | "?" | "!" | "." | "," | "'" | "`" | "$" | "%" | "#" | WS)+
        NAME:       TEXT

        somebody_here:  TEXT
        item_here:      TEXT
        item_recipe:    TEXT
        item_held:      TEXT
        item_goes:      TEXT
        memory:         TEXT

        home:       "home"
        this:       "this"

        look:       "look"
                  | "look" ("at" _WS "myself")   -> look_myself
                  | "look" ("at" _WS item_held)  -> look_item
        drop:       "drop"
        call:       "call" _WS this _WS NAME
        hold:       "hold" _WS item_here
        make:       "make" _WS item_recipe
        go:         "go" _WS item_goes
        eat:        "eat" _WS item_held
        drink:      "drink" _WS item_held
        obliterate: "obliterate"
        remember:   "remember"


        forget:     "forget" _WS memory

        stimulate:  hug | kiss | kick | tickle | poke | heal
        heal:       "heal" _WS somebody_here
        hug:         "hug" _WS somebody_here
        kiss:       "kiss" _WS somebody_here
        kick:       "kick" _WS somebody_here
        tickle:   "tickle" _WS somebody_here
        poke:       "poke" _WS somebody_here

        TEXT_FIELD: "name" | "desc" | "presence"
        CONSUMABLE_FIELDS: "sugar" | "fat" | "protein" | "toxicity" | "caffeine" | "alcohol" | "nutrition" | "vitamins"
        NUMERIC_FIELD: "capacity" | "size" | "weight" | "volatility" | "explosivity" | CONSUMABLE_FIELDS

        number: NUMBER
        text: TEXT

        modify:     "modify" _WS TEXT_FIELD _WS text               -> modify_field
                  | "modify" _WS NUMERIC_FIELD _WS number          -> modify_field
                  | "modify" _WS "when" _WS "opened"               -> when_opened
                  | "modify" _WS "when" _WS "eaten"                -> when_eaten
                  | "modify" _WS "when" _WS "drank"                -> when_drank
                  | "modify" _WS "when" _WS "activated"            -> when_activated
                  | "modify" _WS "when" _WS "triggered"            -> when_triggered
                  | "modify" _WS "when" _WS "closed"               -> when_closed

        %import common.WS
        %import common.WORD
        %import common.NUMBER
        %ignore " "
        """
    )

    return l
