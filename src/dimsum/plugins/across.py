import json
import functools
import pprint
import jq
from typing import List, Dict

ItemsPath = "/home/jlewallen/jlewallen/animal-crossing/json/combined/Items.json"


@functools.lru_cache
def load_items():
    with open(ItemsPath, "r") as file:
        data = json.loads(file.read())
        return data


def main():
    items = load_items()

    compiled = jq.compile(
        ".[] | { sourceSheet, name, seasonEventExclusive, buy, sell, uniqueEntryId, internalId }"
    )
    for row in compiled.input(items).all():
        pprint.pp(row)


if __name__ == "__main__":
    main()
