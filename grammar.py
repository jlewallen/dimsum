from lark import Lark


def create_parser():
    l = Lark(
        """
        start: look | obliterate | drop | hold | make | go | remember | modify

        _WS:  WS
        TEXT:       (WS | WORD | "?" | "!" | "." | "," | "'" | "`" | "$" | "%" | "#")+
        something_here: TEXT
        something_new:  TEXT
        somewhere:      TEXT

        look:       "look"
        drop:       "drop"
        hold:       "hold" _WS something_here
        make:       "make" _WS something_new
        go:         "go" _WS somewhere
        obliterate: "obliterate"
        remember:   "remember"

        TEXT_FIELD: "name" | "desc" | "presence"
        NUMERIC_FIELD: "capacity" | "size" | "weight" | "nutrition" | "toxicity"

        number: NUMBER
        text: TEXT

        modify:     "modify" _WS TEXT_FIELD _WS text               -> modify_field
                  | "modify" _WS NUMERIC_FIELD _WS number          -> modify_field
                  | "modify" _WS "when" _WS "opened"               -> when_opened
                  | "modify" _WS "when" _WS "eaten"                -> when_eaten

        %import common.WS
        %import common.WORD
        %import common.NUMBER
        %ignore " "
         """
    )

    return l
