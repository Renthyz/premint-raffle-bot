import logging

logging.basicConfig(
    format="[%(asctime)s]%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    handlers=[
        # logging.FileHandler("logs.log"),
        logging.StreamHandler()
    ]
)


class PremintLogger:
    def __init__(self, module, account_name, task, total_tasks):
        self.base = f"[{task}/{total_tasks}][{account_name}]"

    def info(self, msg):
        logging.info(f"{self.base} \u001b[0m{msg}\u001b[0m")

    def success(self, msg):
        logging.info(f"{self.base} \u001b[32;1m{msg}\u001b[0m")

    def error(self, msg):
        logging.error(f"{self.base} \u001b[31m{msg}\u001b[0m")

    def debug(self, msg):
        logging.debug(f"{self.base} {msg}")
