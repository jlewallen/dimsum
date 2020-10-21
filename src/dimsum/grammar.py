from lark import Lark


def create_parser():
    l = Lark(
        """
        start: verbs | verb

        verbs.2:           look | obliterate | drop | hold | put | make | go | remember | modify | plant | shake | wear | remove | swing | water | pour
                         | go | climb | walk | run
                         | eat | drink | home | hit
                         | call | forget | think | give | take
                         | hug | kiss | kick | tickle | poke | heal | auth | say | tell

        verb.1:            WORD (this | that | noun)?

        USEFUL_WORD:      /(?!(on|in|under|with|over|within|inside)\b)[a-zA-Z][a-zA-Z0-9]*/i

        makeable_noun:     TEXT
        contained_noun:    USEFUL_WORD+
        unheld_noun:       USEFUL_WORD+
        held_noun:         USEFUL_WORD+
        noun:              USEFUL_WORD+

        this:              "this"
        that:              "that"

        look:              "look"
                         | "look" ("down")                         -> look_down
                         | "look" ("at" "myself")                  -> look_myself
                         | "look" ("at" noun)                      -> look_item
                         | "look" ("for" noun)                     -> look_for
        call:              "call" this NAME

        say:               "say" TEXT
        tell:              "tell" TEXT

        give:              "give"
        home:              "home"


        eat:               "eat" noun
        drink:             "drink" noun

        take:              "take"                                  -> take
                         | "take" "bite" "of" noun                 -> take_bite
                         | "take" "sip" "of" noun                  -> take_sip
                         | "take" contained_noun "out" "of" held_noun -> take_out

        put:               "put" held_noun ("in") held_noun        -> put_inside

        hold:              "hold" unheld_noun                      -> hold
                         | "hold" number unheld_noun               -> hold_quantity

        drop:              "drop"                                  -> drop
                         | "drop" number held_noun                 -> drop_quantity
                         | "drop" held_noun                        -> drop_item

        named_route:       USEFUL_WORD
        DIRECTION:         "north" | "west" | "east" | "south"
        direction:         DIRECTION
        route:             direction | named_route
        go:                "go" route
        climb:             "climb" route
        walk:              "walk" route
        run:               "run" route

        obliterate:        "obliterate"
        make:              "make" makeable_noun                    -> make
                         | "make" number makeable_noun             -> make_quantified

        think:             "think"
        forget:            "forget" noun
        remember:          "remember"

        wear:              "wear" noun
        remove:            "remove" noun

        plant:             "plant" (noun)?
        swing:             "swing" noun
        shake:             "shake" noun
        heal:              "heal" noun
        hug:               "hug" noun
        kiss:              "kiss" noun
        kick:              "kick" noun
        tickle:            "tickle" noun ("with" noun)?
        poke:              "poke" noun ("with" noun)?
        hit:               "hit" noun ("with" noun)?

        water:             "water" noun ("with" noun)?
        pour:              "pour" noun (("on"|"over") noun)?

        modify:            "modify" TEXT_FIELD text                -> modify_field
                         | "modify" NUMERIC_FIELD number           -> modify_field
                         | "modify" "servings" number              -> modify_servings
                         | "modify" "when" "worn"                  -> when_worn
                         | "modify" "when" "opened"                -> when_opened
                         | "modify" "when" "eaten"                 -> when_eaten
                         | "modify" "when" "drank"                 -> when_drank
                         | "modify" "when" "activated"             -> when_activated
                         | "modify" "when" "triggered"             -> when_triggered
                         | "modify" "when" "closed"                -> when_closed

        auth:              "auth" TEXT

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
