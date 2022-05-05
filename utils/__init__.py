import csv
from itertools import cycle

from eth_account import Account


def get_accounts(path: str) -> dict:
    accounts = {}

    with open(path, "r", encoding="utf8") as input_file:
        reader = csv.DictReader(input_file)
        for row in reader:
            try:
                accounts[row["account_name"]] = {
                    "email": row["email"],
                    "private_key": row["private_key"]
                }
            except Exception as err:
                print(f"Error getting profile: {err}")

    return accounts


def get_tasks(path: str) -> list:
    tasks = []

    profiles = get_accounts("./accounts.csv")

    with open(path, "r", encoding="utf8") as input_file:
        reader = csv.DictReader(input_file)
        for row in reader:
            try:
                tasks.append({
                    "raffle_url": row["raffle_url"],
                    "email": profiles[row["account_name"]]["email"],
                    "account_name": row["account_name"],
                    "account": Account.from_key(profiles[row["account_name"]]["private_key"]),
                })
            except Exception as err:
                print(f"Error getting task: {err}")

    return tasks


def get_proxies(path: str) -> cycle:
    proxy_list = []

    with open(path, "r", encoding="utf8") as input_file:
        for row in input_file:
            try:
                proxy = row.split(":")
                if len(proxy) == 2:
                    proxy_list.append(f"http://{proxy[0]}:{proxy[1][:len(proxy[1]) - 1]}")
                elif len(proxy) == 4:
                    proxy_list.append(f"http://{proxy[2]}:{proxy[3][:len(proxy[3]) - 1]}@{proxy[0]}:{proxy[1]}")
                else:
                    print("Incorrect proxy")
            except Exception as err:
                print(f"Error getting proxy: {err}")

    if len(proxy_list) == 0:
        proxy_list.append(None)

    return cycle(proxy_list)
