from lark import Lark


def create_parser():
    l = Lark(
        """
        start: look | obliterate | drop | hold | make | go | remember | modify | eat | drink | home | call | forget | think | hug | kiss | kick | tickle | poke | heal | verb

        noun:              TEXT
        this:              "this"
        that:              "that"

        look:              "look"
                         | "look" ("at" _WS "myself") -> look_myself
                         | "look" ("at" _WS noun)     -> look_item
        call:              "call" _WS this _WS NAME

        verb:              WORD (this | that | noun)?
        home:              "home"
        think:             "think"
        drop:              "drop"
        obliterate:        "obliterate"
        remember:          "remember"
        make:              "make" _WS noun
        hold:              "hold" _WS noun
        go:                "go" _WS noun
        eat:               "eat" _WS noun
        drink:             "drink" _WS noun
        forget:            "forget" _WS noun
        heal:              "heal" _WS noun
        hug:               "hug" _WS noun
        kiss:              "kiss" _WS noun
        kick:              "kick" _WS noun
        tickle:            "tickle" _WS noun
        poke:              "poke" _WS noun

        modify:            "modify" _WS TEXT_FIELD _WS text               -> modify_field
                         | "modify" _WS NUMERIC_FIELD _WS number          -> modify_field
                         | "modify" _WS "when" _WS "opened"               -> when_opened
                         | "modify" _WS "when" _WS "eaten"                -> when_eaten
                         | "modify" _WS "when" _WS "drank"                -> when_drank
                         | "modify" _WS "when" _WS "activated"            -> when_activated
                         | "modify" _WS "when" _WS "triggered"            -> when_triggered
                         | "modify" _WS "when" _WS "closed"               -> when_closed

        CONSUMABLE_FIELDS: "sugar" | "fat" | "protein" | "toxicity" | "caffeine" | "alcohol" | "nutrition" | "vitamins"
        NUMERIC_FIELD:     "capacity" | "size" | "weight" | "volatility" | "explosivity" | CONSUMABLE_FIELDS
        TEXT_FIELD:        "name" | "desc" | "presence"

        TEXT:         (WORD | "?" | "!" | "." | "," | "'" | "`" | "$" | "%" | "#" | WS)+
        NAME:         TEXT
        number:       NUMBER
        text:         TEXT
        _WS:          WS

        %import common.WS
        %import common.WORD
        %import common.NUMBER
        %ignore " "
        """
    )

    return l
