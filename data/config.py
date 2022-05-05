import json

with open("./config.json", "r", encoding="utf8") as input_file:
    config = json.loads(input_file.read())

DELAY = config["delay"]
RETRY_AMOUNT = config["retry_amount"]
CAPMONSTER_KEY = config["capmonster_key"]
