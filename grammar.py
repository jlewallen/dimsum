from lark import Lark


def create_parser():
    l = Lark(
        """
        start: verbs | verb

        verbs.2: look | obliterate | drop | hold | make | go | remember | modify | plant | shake | wear | remove | swing | water | pour | climb
                      | eat | drink | home | hit
                      | call | forget | think
                      | hug | kiss | kick | tickle | poke | heal | auth | say | tell

        USEFUL_WORD:      /(?!(on|with|over)\b)[\w][\w]*/i

        makeable_noun:     TEXT
        noun:              USEFUL_WORD+
        this:              "this"
        that:              "that"

        look:              "look"
                         | "look" ("down")            -> look_down
                         | "look" ("at" _WS "myself") -> look_myself
                         | "look" ("at" _WS noun)     -> look_item
                         | "look" ("for" _WS noun)    -> look_for
        call:              "call" _WS this _WS NAME

        say:               "say" TEXT
        tell:              "tell" TEXT

        verb.1:            WORD (this | that | noun)?
        home:              "home"
        think:             "think"
        drop:              "drop"
        obliterate:        "obliterate"
        remember:          "remember"
        make:              "make" _WS makeable_noun
        hold:              "hold" _WS noun
        go:                "go" _WS noun
        eat:               "eat" _WS noun
        drink:             "drink" _WS noun
        plant:             "plant" (_WS noun)?
        wear:              "wear" _WS noun
        remove:            "remove" _WS noun
        swing:             "swing" _WS noun
        shake:             "shake" _WS noun
        forget:            "forget" _WS noun
        heal:              "heal" _WS noun
        climb:             "climb" _WS noun
        hug:               "hug" _WS noun
        kiss:              "kiss" _WS noun
        kick:              "kick" _WS noun
        tickle:            "tickle" _WS noun (_WS "with" _WS noun)?
        poke:              "poke" _WS noun (_WS "with" _WS noun)?
        hit:               "hit" noun ("with" noun)?

        water:             "water" _WS noun (_WS "with" _WS noun)?
        pour:              "pour" _WS noun (_WS ("on"|"over") _WS noun)?

        auth:              "auth" _WS TEXT

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
