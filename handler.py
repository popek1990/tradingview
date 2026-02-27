# ----------------------------------------------- #
# Nazwa projektu         : TradingView-Webhook-Bot #
# Plik                   : handler.py              #
# ----------------------------------------------- #

import logging
import threading
from typing import Any

import requests
from discord_webhook import DiscordEmbed, DiscordWebhook
from telegram import Bot

from config import pobierz_ustawienia

logger = logging.getLogger(__name__)

TIMEOUT_SIEC = 10  # sekundy — timeout na operacje sieciowe

# Cache bota Telegram (inwalidacja przy zmianie tokena, thread-safe)
_tg_bot_lock = threading.Lock()
_tg_bot_cache: tuple[str, Bot] | None = None


def _pobierz_tg_bot(token: str) -> Bot:
    """Zwraca cache'owana instancje bota Telegram (tworzy nowa przy zmianie tokena)."""
    global _tg_bot_cache
    with _tg_bot_lock:
        if _tg_bot_cache is None or _tg_bot_cache[0] != token:
            _tg_bot_cache = (token, Bot(token=token))
        return _tg_bot_cache[1]


def wyslij_alert(data: dict[str, Any]) -> dict[str, bool]:
    """Wysyla alert do wszystkich wlaczonych kanalow. Zwraca wyniki {kanal: sukces}."""
    ust = pobierz_ustawienia()
    msg = data["msg"]
    wyniki: dict[str, bool] = {}

    if ust.wyslij_alerty_telegram:
        try:
            tg_bot = _pobierz_tg_bot(ust.tg_token)
            kanal = data.get("telegram") or ust.kanal
            tg_bot.sendMessage(kanal, msg, parse_mode="MARKDOWN", timeout=TIMEOUT_SIEC)
            logger.info("Telegram: wyslano do %s", kanal)
            wyniki["telegram"] = True
        except Exception as e:
            logger.error("Telegram: %s", e)
            wyniki["telegram"] = False

    # Druga grupa Telegram
    if ust.wyslij_alerty_telegram_2 and ust.kanal_2:
        try:
            tg_bot = _pobierz_tg_bot(ust.tg_token)
            tg_bot.sendMessage(ust.kanal_2, msg, parse_mode="MARKDOWN", timeout=TIMEOUT_SIEC)
            logger.info("Telegram 2: wyslano do %s", ust.kanal_2)
            wyniki["telegram_2"] = True
        except Exception as e:
            logger.error("Telegram 2: %s", e)
            wyniki["telegram_2"] = False

    if ust.wyslij_alerty_discord:
        try:
            webhook_id = data.get("discord") or ust.discord_webhook
            discord_url = webhook_id if webhook_id.startswith("http") else "https://discord.com/api/webhooks/" + webhook_id
            webhook = DiscordWebhook(url=discord_url, timeout=TIMEOUT_SIEC)
            if len(msg) > 256:
                embed = DiscordEmbed(title=msg[:253] + "...", description=msg)
            else:
                embed = DiscordEmbed(title=msg)
            webhook.add_embed(embed)
            odpowiedz = webhook.execute()
            if odpowiedz and hasattr(odpowiedz, "status_code") and odpowiedz.status_code >= 400:
                logger.error("Discord: serwer zwrocil status %s", odpowiedz.status_code)
                wyniki["discord"] = False
            else:
                logger.info("Discord: wyslano")
                wyniki["discord"] = True
        except Exception as e:
            logger.error("Discord: %s", e)
            wyniki["discord"] = False

    if ust.wyslij_alerty_slack:
        try:
            slack_id = data.get("slack") or ust.slack_webhook
            slack_url = slack_id if slack_id.startswith("http") else "https://hooks.slack.com/services/" + slack_id
            odpowiedz = requests.post(slack_url, json={"text": msg}, timeout=TIMEOUT_SIEC)
            if odpowiedz.status_code >= 400:
                logger.error("Slack: serwer zwrocil status %s", odpowiedz.status_code)
                wyniki["slack"] = False
            elif odpowiedz.text != "ok":
                logger.error("Slack: odpowiedz: %s", odpowiedz.text)
                wyniki["slack"] = False
            else:
                logger.info("Slack: wyslano")
                wyniki["slack"] = True
        except Exception as e:
            logger.error("Slack: %s", e)
            wyniki["slack"] = False

    return wyniki
