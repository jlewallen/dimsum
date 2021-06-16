from lark import Lark


def create_parser():
    l = Lark(
        """
        start: verbs | verb

        verbs.2:           look
                         | drop | hold | put | take | lock | unlock | give | wear | remove | open | close
                         | make | call | modify | obliterate | freeze | unfreeze
                         | eat | drink | hit | kick
                         | go | climb | walk | run | home
                         | plant | pour | water
                         | shake | swing
                         | hug | kiss | tickle | poke | heal | say | tell
                         | remember | forget | think
                         | auth | dig

        verb.1:            WORD (this | that | noun)?

        USEFUL_WORD:      /(?!(on|from|in|under|with|over|within|inside)\b)[a-zA-Z][a-zA-Z0-9]*/i

        makeable_noun:     TEXT
        contained_noun:    USEFUL_WORD+
        unheld_noun:       USEFUL_WORD+
        held_noun:         USEFUL_WORD+
        consumable_noun:   USEFUL_WORD+
        general_noun:      USEFUL_WORD+

        makeable:          makeable_noun
        contained:         object_by_number | contained_noun
        consumable:        object_by_number | consumable_noun
        unheld:            object_by_number | unheld_noun
        held:              object_by_number | held_noun
        noun:              object_by_number | general_noun

        this:              "this"
        that:              "that"

        look:              "look"
                         | "look" ("down")                         -> look_down
                         | "look" ("at" "myself")                  -> look_myself
                         | "look" ("at" noun)                      -> look_item
                         | "look" ("for" noun)                     -> look_for
                         | "look" ("in" held)                      -> look_inside

        dig_direction:     direction 
        dig_arbitrary:     WORD
        dig_linkage:       dig_direction | dig_arbitrary
        dig:               "dig" dig_linkage "to" STRING           -> dig

        call:              "call" this NAME

        say:               "say" TEXT
        tell:              "tell" TEXT

        give:              "give"

        eat:               "eat" consumable
        drink:             "drink" consumable

        take:              "take"                                  -> take
                         | "take" "bite" "of" noun                 -> take_bite
                         | "take" "sip" "of" noun                  -> take_sip
                         | "take" contained "out" "of" held        -> take_out

        put:               "put" held ("in") held                  -> put_inside

        open:              "open" held                             -> open_hands
        close:             "close" held                            -> close_hands

        freeze:            "freeze" held                           -> freeze
        unfreeze:          "unfreeze" held                         -> unfreeze

        lock:              "lock" held "with" held                 -> lock_with
                         | "lock" held                             -> lock_new

        unlock:            "unlock" held "with" held               -> unlock_with
                         | "unlock" held                           -> unlock

        hold:              "hold" unheld                           -> hold
                         | "hold" number unheld                    -> hold_quantity

        drop:              "drop"                                  -> drop
                         | "drop" number held                      -> drop_quantity
                         | "drop" held                             -> drop_item

        named_route:       USEFUL_WORD
        DIRECTION:         "north" | "west" | "east" | "south"
        direction:         DIRECTION
        find_direction:    direction
        route:             find_direction | named_route
        home:              "home"
        go:                "go" route
        climb:             "climb" route
        walk:              "walk" route
        run:               "run" route

        obliterate:        "obliterate"
        make:              "make" makeable                         -> make
                         | "make" number makeable                  -> make_quantified

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

        pour:              "pour" "from" noun                      -> pour_from
                         | "pour" noun ("from"|"on"|"over") noun   -> pour

        modify:            "modify" TEXT_FIELD text                -> modify_field
                         | "modify" NUMERIC_FIELD number           -> modify_field
                         | "modify" "servings" number              -> modify_servings
                         | "modify" "capacity" number              -> modify_capacity
                         | "modify" "pours" makeable_noun          -> when_pours
                         | "modify" "when" "worn"                  -> when_worn
                         | "modify" "when" "opened"                -> when_opened
                         | "modify" "when" "eaten"                 -> when_eaten
                         | "modify" "when" "drank"                 -> when_drank
                         | "modify" "when" "activated"             -> when_activated
                         | "modify" "when" "triggered"             -> when_triggered
                         | "modify" "when" "closed"                -> when_closed
                         | "modify" "hard" "to" "see"              -> modify_hard_to_see
                         | "modify" "easy" "to" "see"              -> modify_easy_to_see

        auth:              "auth" TEXT

        object_by_number:  "#"NUMBER

        CONSUMABLE_FIELDS: "sugar" | "fat" | "protein" | "toxicity" | "caffeine" | "alcohol" | "nutrition" | "vitamins"
        NUMERIC_FIELD:     "size" | "weight" | "volatility" | "explosivity" | CONSUMABLE_FIELDS
        TEXT_FIELD:        "name" | "desc" | "presence"

        TEXT_INNER:   (WORD | "?" | "!" | "." | "," | "'" | "`" | "$" | "%" | "#")
        TEXT:         TEXT_INNER (WS | TEXT_INNER)*
        NAME:         TEXT
        number:       NUMBER
        text:         TEXT
        _WS:          WS

        DOUBLE_QUOTED_STRING:  /"[^"]*"/
        SINGLE_QUOTED_STRING:  /'[^']*'/
        STRING:                (SINGLE_QUOTED_STRING | DOUBLE_QUOTED_STRING)

        %import common.WS
        %import common.WORD
        %import common.NUMBER
        %ignore " "
        """
    )

    return l
