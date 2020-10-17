from lark import Lark


def create_parser():
    l = Lark(
        """
        start: verbs | verb

        verbs.2: look | obliterate | drop | hold | make | go | remember | modify | plant | shake | wear | remove | swing | water | pour | climb
                      | eat | drink | home | hit
                      | call | forget | think | give | take
                      | hug | kiss | kick | tickle | poke | heal | auth | say | tell

        USEFUL_WORD:      /(?!(on|with|over)\b)[\w][\w]*/i

        makeable_noun:     TEXT
        noun:              USEFUL_WORD+
        this:              "this"
        that:              "that"

        look:              "look"
                         | "look" ("down")            -> look_down
                         | "look" ("at" "myself")     -> look_myself
                         | "look" ("at" noun)         -> look_item
                         | "look" ("for" noun)        -> look_for
        call:              "call" this NAME

        say:               "say" TEXT
        tell:              "tell" TEXT

        verb.1:            WORD (this | that | noun)?
        give:              "give"
        take:              "take"
        home:              "home"
        think:             "think"

        drop:              "drop"             -> drop
                         | "drop" number noun -> drop_quantity
                         | "drop" noun        -> drop_item

        obliterate:        "obliterate"
        remember:          "remember"
        make:              "make" makeable_noun        -> make
                         | "make" number makeable_noun -> make_quantified
        hold:              "hold" noun
        go:                "go" noun
        eat:               "eat" noun
        drink:             "drink" noun
        plant:             "plant" (noun)?
        wear:              "wear" noun
        remove:            "remove" noun
        swing:             "swing" noun
        shake:             "shake" noun
        forget:            "forget" noun
        heal:              "heal" noun
        climb:             "climb" noun
        hug:               "hug" noun
        kiss:              "kiss" noun
        kick:              "kick" noun
        tickle:            "tickle" noun ("with" noun)?
        poke:              "poke" noun ("with" noun)?
        hit:               "hit" noun ("with" noun)?

        water:             "water" noun ("with" noun)?
        pour:              "pour" noun (("on"|"over") noun)?

        auth:              "auth" TEXT

        modify:            "modify" TEXT_FIELD text               -> modify_field
                         | "modify" NUMERIC_FIELD number          -> modify_field
                         | "modify" "when" "opened"               -> when_opened
                         | "modify" "when" "eaten"                -> when_eaten
                         | "modify" "when" "drank"                -> when_drank
                         | "modify" "when" "activated"            -> when_activated
                         | "modify" "when" "triggered"            -> when_triggered
                         | "modify" "when" "closed"               -> when_closed

        CONSUMABLE_FIELDS: "sugar" | "fat" | "protein" | "toxicity" | "caffeine" | "alcohol" | "nutrition" | "vitamins"
        NUMERIC_FIELD:     "capacity" | "size" | "weight" | "volatility" | "explosivity" | CONSUMABLE_FIELDS
        TEXT_FIELD:        "name" | "desc" | "presence"

        TEXT_INNER:   (WORD | "?" | "!" | "." | "," | "'" | "`" | "$" | "%" | "#")
        TEXT:         TEXT_INNER (WS | TEXT_INNER)*
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
