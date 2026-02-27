# ----------------------------------------------- #
# Project                : TradingView-Webhook-Bot #
# File                   : handler.py              #
# ----------------------------------------------- #

import logging
import re
import threading
from typing import Any

import requests
from discord_webhook import DiscordEmbed, DiscordWebhook
from telegram import Bot

from config import get_settings

logger = logging.getLogger(__name__)

NETWORK_TIMEOUT = 10  # seconds — timeout for network operations
REGEX_WEBHOOK_ID = re.compile(r"^[a-zA-Z0-9/_\-]+$")  # Allowed chars in webhook ID

# Telegram bot cache (invalidated on token change, thread-safe)
_tg_bot_lock = threading.Lock()
_tg_bot_cache: tuple[str, Bot] | None = None

# Telegram group name cache (id -> name)
_tg_names_lock = threading.Lock()
_tg_names_cache: dict[str, str] = {}


def _get_tg_bot(token: str) -> Bot:
    """Returns cached Telegram bot instance (creates new one on token change)."""
    global _tg_bot_cache
    with _tg_bot_lock:
        if _tg_bot_cache is None or _tg_bot_cache[0] != token:
            _tg_bot_cache = (token, Bot(token=token))
        return _tg_bot_cache[1]


def _get_group_name(bot: Bot, channel_id: str) -> str:
    """Returns group name (title) from cache or API. Returns ID on error."""
    global _tg_names_cache
    with _tg_names_lock:
        if channel_id in _tg_names_cache:
            return _tg_names_cache[channel_id]

    try:
        chat_info = bot.get_chat(channel_id)
        name = chat_info.title or chat_info.username or channel_id
        with _tg_names_lock:
            _tg_names_cache[channel_id] = name
        return name
    except Exception:
        return channel_id


def send_alert(data: dict[str, Any]) -> dict[str, bool]:
    """Sends alert to all enabled channels. Returns results {channel: success}."""
    settings = get_settings()
    msg = data["msg"]
    results: dict[str, bool] = {}

    if settings.send_alerts_telegram:
        try:
            tg_bot = _get_tg_bot(settings.tg_token)
            channel = data.get("telegram") or settings.channel
            group_name = _get_group_name(tg_bot, channel)

            tg_bot.sendMessage(channel, msg, parse_mode="MARKDOWN", timeout=NETWORK_TIMEOUT)
            logger.info("Telegram: sent to %s", group_name)
            results["telegram"] = True
        except Exception as e:
            logger.error("Telegram: %s", e)
            results["telegram"] = False

    # Second Telegram group
    if settings.send_alerts_telegram_2 and settings.channel_2:
        try:
            tg_bot = _get_tg_bot(settings.tg_token)
            group_name_2 = _get_group_name(tg_bot, settings.channel_2)

            tg_bot.sendMessage(settings.channel_2, msg, parse_mode="MARKDOWN", timeout=NETWORK_TIMEOUT)
            logger.info("Telegram 2: sent to %s", group_name_2)
            results["telegram_2"] = True
        except Exception as e:
            logger.error("Telegram 2: %s", e)
            results["telegram_2"] = False

    if settings.send_alerts_discord:
        try:
            webhook_id = data.get("discord") or settings.discord_webhook

            # SSRF validation — full URL accepted, ID validated with regex
            discord_url = None
            if not webhook_id:
                logger.warning("Discord: Empty webhook ID")
            elif webhook_id.startswith("https://discord.com/api/webhooks/"):
                discord_url = webhook_id
            elif REGEX_WEBHOOK_ID.match(webhook_id):
                discord_url = "https://discord.com/api/webhooks/" + webhook_id
            else:
                logger.warning("Discord: Rejected suspicious webhook ID")

            if not discord_url:
                results["discord"] = False
            else:
                webhook = DiscordWebhook(url=discord_url, timeout=NETWORK_TIMEOUT)
                if len(msg) > 256:
                    embed = DiscordEmbed(title=msg[:253] + "...", description=msg[:4096])
                else:
                    embed = DiscordEmbed(title=msg)
                webhook.add_embed(embed)
                response = webhook.execute()
                if response and hasattr(response, "status_code") and response.status_code >= 400:
                    logger.error("Discord: server returned status %s", response.status_code)
                    results["discord"] = False
                else:
                    logger.info("Discord: sent")
                    results["discord"] = True
        except Exception as e:
            logger.error("Discord: %s", e)
            results["discord"] = False

    if settings.send_alerts_slack:
        try:
            slack_id = data.get("slack") or settings.slack_webhook

            # SSRF validation — full URL accepted, ID validated with regex
            slack_url = None
            if not slack_id:
                logger.warning("Slack: Empty webhook ID")
            elif slack_id.startswith("https://hooks.slack.com/services/"):
                slack_url = slack_id
            elif REGEX_WEBHOOK_ID.match(slack_id):
                slack_url = "https://hooks.slack.com/services/" + slack_id
            else:
                logger.warning("Slack: Rejected suspicious webhook ID")

            if not slack_url:
                results["slack"] = False
            else:
                response = requests.post(slack_url, json={"text": msg}, timeout=NETWORK_TIMEOUT)
                if response.status_code >= 400:
                    logger.error("Slack: server returned status %s", response.status_code)
                    results["slack"] = False
                elif response.text != "ok":
                    logger.error("Slack: response: %s", response.text)
                    results["slack"] = False
                else:
                    logger.info("Slack: sent")
                    results["slack"] = True
        except Exception as e:
            logger.error("Slack: %s", e)
            results["slack"] = False

    return results
