import json
import re
from config import MENU_PATH
from utils.logger import log

menu = json.load(open(MENU_PATH))

def parse_order(text):
    text = text.lower()
    items = []

    for item in menu["items"]:
        if item["name"] in text:
            qty_match = re.search(r"(\d+)", text)
            qty = int(qty_match.group()) if qty_match else 1

            items.append({
                "name": item["name"],
                "qty": qty
            })

    log(f"📦 Parsed Order: {items}")
    return items
