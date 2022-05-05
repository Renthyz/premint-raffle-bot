import ssl
import time

import cloudscraper
import urllib3
from bs4 import BeautifulSoup
from capmonster_python import RecaptchaV2Task
from eth_account.messages import encode_defunct
from eth_account.signers.local import LocalAccount

from data.config import DELAY, RETRY_AMOUNT, CAPMONSTER_KEY
from utils.logger import PremintLogger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Premint:
    def __init__(self, task: dict, task_num: int, tasks_count: int, proxy: str):
        self.logger = PremintLogger(
            module="premint",
            account_name=task["account_name"],
            task=self._beautify_task_number(task_num, tasks_count),
            total_tasks=tasks_count
        )

        self.raffle_url = task["raffle_url"]
        self.email = task["email"]  # TODO Generate random email with domain
        self.account: LocalAccount = task["account"]
        self.proxy = proxy

        self.session = None
        self.csrf = None
        self.captcha_required = None
        self.registered = None

    def start_task(self):
        self.session = self._make_scraper()
        self.session.proxies = self.proxy

        try:
            if self._get_csrf_token():
                if self._register():
                    if self._login():
                        if self._submit_entry():
                            return
        except Exception as err:
            self.logger.error(f"Unknown error while starting tasks: {err}")
            raise err
        finally:
            self.session.close()

    def _get_csrf_token(self):
        for _ in range(RETRY_AMOUNT):
            try:
                self.logger.info("Initializing session...")
                with self.session.get("https://www.premint.xyz/login/", timeout=15) as response:
                    if response.ok:
                        self.session.headers.update({"x-csrftoken": response.cookies["csrftoken"]})
                        return True
                    else:
                        self.logger.error(f"Unknown status code while initializing session [{response.status_code}]")
            except Exception as err:
                self.logger.error(f"Error initializing session: {err}")

            time.sleep(DELAY)

        return False

    def _register(self):
        for _ in range(RETRY_AMOUNT):
            try:
                self.session.headers.update(
                    {
                        "referer": "https://www.premint.xyz/v1/login_api/",
                        "content-type": "application/x-www-form-urlencoded; charset=UTF-8"
                    }
                )
                data = f"username={self.account.address.lower()}"

                self.logger.info("Registering account...")
                with self.session.post("https://www.premint.xyz/v1/signup_api/", data=data, timeout=15) as response:
                    if response.ok:
                        return True
                    else:
                        self.logger.error(f"Unknown status code while registering account [{response.status_code}]")
            except Exception as err:
                self.logger.error(f"Error registering account: {err}")

            time.sleep(DELAY)

        return False

    def _login(self):
        for _ in range(RETRY_AMOUNT):
            try:
                for _ in range(RETRY_AMOUNT):
                    if self._get_nonce():
                        message = encode_defunct(text=self._get_message_to_sign())
                        signed_message = self.account.sign_message(message)
                        signature = signed_message["signature"].hex()
                        data = f"web3provider=metamask&address={self.account.address.lower()}&signature={signature}"

                        self.logger.info("Login in account...")
                        with self.session.post("https://www.premint.xyz/v1/login_api/", data=data,
                                               timeout=15) as response:
                            if response.ok:
                                if response.json()["success"]:
                                    self.logger.success(f"Successfully logged in account!")
                                    return True
                                else:
                                    self.logger.error(f"Error login: {response.text} [{response.status_code}]")
                            else:
                                self.logger.error(f"Unknown status code while login [{response.status_code}]")
                    return False

            except Exception as err:
                self.logger.error(f"Error login: {err}")

            time.sleep(DELAY)

        return False

    def _update_csrf_token(self):
        for _ in range(RETRY_AMOUNT):
            try:
                self.logger.info("Getting csrf token...")
                with self.session.get(self.raffle_url, timeout=15) as response:
                    if response.ok:
                        if "6Lf9yOodAAAAADyXy9cQncsLqD9Gl4NCBx3JCR_x" in response.text:
                            self.captcha_required = True
                        else:
                            self.captcha_required = False

                        if self.account.address.lower() in response.text.lower():
                            self.registered = True
                        else:
                            self.registered = False

                        soup = BeautifulSoup(response.content, "lxml")
                        self.csrf = soup.find_all("input", {"name": "csrfmiddlewaretoken"})[0]["value"]
                        return True
                    else:
                        self.logger.error(f"Unknown status code while getting csrf token [{response.status_code}]")

            except Exception as err:
                self.logger.error(f"Error getting csrf token: {err}")

            time.sleep(DELAY)

        return False

    def _submit_entry(self):
        for _ in range(RETRY_AMOUNT):
            if self._update_csrf_token():
                pass
            else:
                return

            if self.registered:
                self.logger.success(f"Already registered for raffle")
                return True

            body = f"csrfmiddlewaretoken={self.csrf}" \
                   "&custom_field=https://www.twitter.com/cryptocean/" \
                   "&params_field={}" \
                   f"&email_field=" \
                   "&registration-form-submit="

            if self.captcha_required:
                while True:
                    try:
                        g_recaptcha_response = self._solve_captcha()
                        self.logger.info(f"Successfully solved captcha")

                        body += f"&captcha={g_recaptcha_response}"
                        break

                    except Exception as err:
                        self.logger.error(f"Error solving captcha: {err}")

            try:
                self.logger.info("Submitting raffle entry...")
                with self.session.post(self.raffle_url, data=body, timeout=15) as response:
                    if response.ok:
                        print(response.url)
                        if "regyes=1" in response.url or 'regpending=1' in response.url:
                            self.logger.success(f"You have been registered to raffle!")
                            return True
                        else:
                            self.logger.error(f"Error submitting entry [{response.url}]")
                    else:
                        self.logger.error(f"Unknown status code while submitting entry [{response.status_code}]")
            except Exception as err:
                self.logger.error(f"Error submitting entry: {err}")

            time.sleep(DELAY)

        return False

    def _get_message_to_sign(self) -> str:

        return "Welcome to PREMINT!\n\n" \
               "Signing is the only way we can truly know \n" \
               "that you are the owner of the wallet you \n" \
               "are connecting. Signing is a safe, gas-less \n" \
               "transaction that does not in any way give \n" \
               "PREMINT permission to perform any \n" \
               "transactions with your wallet.\n\n" \
               f"Wallet address:\n{self.account.address.lower()}\n\n" \
               f"Nonce: {self.nonce}"

    def _get_nonce(self):
        try:
            self.logger.info("Getting nonce...")
            with self.session.get("https://www.premint.xyz/v1/login_api/", timeout=15) as response:
                if response.ok:
                    self.nonce = response.json()["data"]
                    return True
                else:
                    self.logger.error(f"Unknown status code while getting nonce [{response.status_code}]")
        except Exception as err:
            self.logger.error(f"Error getting nonce: {err}")

        return False

    def _solve_captcha(self) -> str:
        self.logger.info("Solving captcha")

        capmonster = RecaptchaV2Task(CAPMONSTER_KEY)
        task_id = capmonster.create_task(self.raffle_url, "6Lf9yOodAAAAADyXy9cQncsLqD9Gl4NCBx3JCR_x")
        result = capmonster.join_task_result(task_id)

        return result.get("gRecaptchaResponse")

    @staticmethod
    def _make_scraper():
        ssl_context = ssl.create_default_context()
        ssl_context.set_ciphers(
            "ECDH-RSA-NULL-SHA:ECDH-RSA-RC4-SHA:ECDH-RSA-DES-CBC3-SHA:ECDH-RSA-AES128-SHA:ECDH-RSA-AES256-SHA:"
            "ECDH-ECDSA-NULL-SHA:ECDH-ECDSA-RC4-SHA:ECDH-ECDSA-DES-CBC3-SHA:ECDH-ECDSA-AES128-SHA:"
            "ECDH-ECDSA-AES256-SHA:ECDHE-RSA-NULL-SHA:ECDHE-RSA-RC4-SHA:ECDHE-RSA-DES-CBC3-SHA:ECDHE-RSA-AES128-SHA:"
            "ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-NULL-SHA:ECDHE-ECDSA-RC4-SHA:ECDHE-ECDSA-DES-CBC3-SHA:"
            "ECDHE-ECDSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA:AECDH-NULL-SHA:AECDH-RC4-SHA:AECDH-DES-CBC3-SHA:"
            "AECDH-AES128-SHA:AECDH-AES256-SHA"
        )
        ssl_context.set_ecdh_curve("prime256v1")
        ssl_context.options |= (ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1_3 | ssl.OP_NO_TLSv1)
        ssl_context.check_hostname = False

        return cloudscraper.create_scraper(
            debug=False,
            ssl_context=ssl_context
        )

    # make a beautiful task number (e.g.: 001, 011, 111 || 0001, 0011, 0111, 1111)
    @staticmethod
    def _beautify_task_number(task_num: int, tasks_count: int) -> str:
        return "0" * (len(str(tasks_count)) - len(str(task_num))) + str(task_num)
