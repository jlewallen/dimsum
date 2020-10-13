from lark import Lark


def create_parser():
    l = Lark(
        """
        start: look | obliterate | drop | hold | make | go | remember | modify | eat | drink | home | stimulate

        _WS:        WS
        TEXT:       (WORD | "?" | "!" | "." | "," | "'" | "`" | "$" | "%" | "#" | WS)+

        somebody_here: TEXT
        item_here:     TEXT
        item_new:      TEXT
        item_held:     TEXT
        item_goes:     TEXT

        home:       "home"
        look:       "look"
                  | "look" ("at" _WS "myself")   -> look_myself
                  | "look" ("at" _WS item_held)  -> look_item
        drop:       "drop"
        hold:       "hold" _WS item_here
        make:       "make" _WS item_new
        go:         "go" _WS item_goes
        eat:        "eat" _WS item_held
        drink:      "drink" _WS item_held
        obliterate: "obliterate"
        remember:   "remember"

        stimulate:  hug | kiss | kick | tickle | poke | heal
        heal:       "heal" _WS somebody_here
        hug:         "hug" _WS somebody_here
        kiss:       "kiss" _WS somebody_here
        kick:       "kick" _WS somebody_here
        tickle:   "tickle" _WS somebody_here
        poke:       "poke" _WS somebody_here

        TEXT_FIELD: "name" | "desc" | "presence"
        CONSUMABLE_FIELDS: "sugar" | "fat" | "protein" | "toxicity" | "caffeine" | "alcohol" | "nutrition" | "vitamins"
        NUMERIC_FIELD: "capacity" | "size" | "weight" | CONSUMABLE_FIELDS

        number: NUMBER
        text: TEXT

        modify:     "modify" _WS TEXT_FIELD _WS text               -> modify_field
                  | "modify" _WS NUMERIC_FIELD _WS number          -> modify_field
                  | "modify" _WS "when" _WS "opened"               -> when_opened
                  | "modify" _WS "when" _WS "eaten"                -> when_eaten
                  | "modify" _WS "when" _WS "drank"                -> when_drank

        %import common.WS
        %import common.WORD
        %import common.NUMBER
        %ignore " "
        """
    )

    return l
