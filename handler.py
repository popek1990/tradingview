# ----------------------------------------------- #
# Project                : TradingView-Webhook-Bot #
# File                   : handler.py              #
# ----------------------------------------------- #

import collections
import logging
import re
import textwrap
import threading
from typing import Any
from urllib.parse import urlparse

import requests
from discord_webhook import DiscordEmbed, DiscordWebhook
from telegram import Bot
from telegram.error import TelegramError

from config import get_settings

logger = logging.getLogger(__name__)

NETWORK_TIMEOUT = 10  # seconds — timeout for network operations
REGEX_WEBHOOK_ID = re.compile(r"^[a-zA-Z0-9/_\-]+$")  # Allowed chars in webhook ID

# Telegram bot cache (invalidated on token change, thread-safe)
_tg_bot_lock = threading.Lock()
_tg_bot_cache: tuple[str, Bot] | None = None

# Telegram group name cache — LRU with max 256 entries (thread-safe)
_tg_names_lock = threading.Lock()
_tg_names_cache: collections.OrderedDict[str, str] = collections.OrderedDict()
_TG_NAMES_MAX = 256


def _get_tg_bot(token: str) -> Bot:
    """Returns cached Telegram bot instance (creates new one on token change)."""
    global _tg_bot_cache
    with _tg_bot_lock:
        if _tg_bot_cache is None or _tg_bot_cache[0] != token:
            _tg_bot_cache = (token, Bot(token=token))
        return _tg_bot_cache[1]


def _get_group_name(bot: Bot, channel_id: str) -> str:
    """Returns group name (title) from LRU cache or API. Returns ID on error."""
    with _tg_names_lock:
        if channel_id in _tg_names_cache:
            _tg_names_cache.move_to_end(channel_id)
            return _tg_names_cache[channel_id]

    try:
        chat_info = bot.get_chat(channel_id, timeout=NETWORK_TIMEOUT)
        name = chat_info.title or chat_info.username or channel_id
        with _tg_names_lock:
            _tg_names_cache[channel_id] = name
            if len(_tg_names_cache) > _TG_NAMES_MAX:
                _tg_names_cache.popitem(last=False)  # evict oldest
        return name
    except Exception:
        return channel_id


def _tg_send_message(bot: Bot, channel: str, msg: str) -> None:
    """Sends Telegram message with Markdown, retries without formatting on parse error."""
    try:
        bot.sendMessage(channel, msg, parse_mode="MARKDOWN", timeout=NETWORK_TIMEOUT)
    except TelegramError as e:
        if "parse" in str(e).lower() or "can't" in str(e).lower():
            logger.warning("Telegram: Markdown parse failed, retrying without formatting")
            bot.sendMessage(channel, msg, timeout=NETWORK_TIMEOUT)
        else:
            raise


def _validate_webhook_url(url: str, expected_host: str, expected_prefix: str) -> bool:
    """Validates that a full webhook URL is safe (correct host, no query/fragment tricks)."""
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname == expected_host
            and parsed.path.startswith(expected_prefix)
            and not parsed.query
            and not parsed.fragment
            and ".." not in parsed.path
        )
    except Exception:
        return False


def send_alert(data: dict[str, Any]) -> dict[str, bool]:
    """Sends alert to all enabled channels. Returns results {channel: success}."""
    settings = get_settings()
    msg = data["msg"]
    results: dict[str, bool] = {}

    if settings.send_alerts_telegram:
        try:
            tg_bot = _get_tg_bot(settings.tg_token)
            channel = data.get("telegram") or settings.channel
            if not re.match(r"^-?\d+$", str(channel)):
                logger.warning("Telegram: invalid channel ID format: rejected")
                results["telegram"] = False
            else:
                group_name = _get_group_name(tg_bot, channel)

                _tg_send_message(tg_bot, channel, msg)
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

            _tg_send_message(tg_bot, settings.channel_2, msg)
            logger.info("Telegram 2: sent to %s", group_name_2)
            results["telegram_2"] = True
        except Exception as e:
            logger.error("Telegram 2: %s", e)
            results["telegram_2"] = False

    if settings.send_alerts_discord:
        try:
            webhook_id = data.get("discord") or settings.discord_webhook

            # SSRF validation — full URL validated strictly, ID validated with regex
            discord_url = None
            if not webhook_id:
                logger.warning("Discord: Empty webhook ID")
            elif webhook_id.startswith("https://"):
                if _validate_webhook_url(webhook_id, "discord.com", "/api/webhooks/"):
                    discord_url = webhook_id
                else:
                    logger.warning("Discord: Rejected invalid webhook URL")
            elif REGEX_WEBHOOK_ID.match(webhook_id):
                discord_url = "https://discord.com/api/webhooks/" + webhook_id
            else:
                logger.warning("Discord: Rejected suspicious webhook ID")

            if not discord_url:
                results["discord"] = False
            else:
                webhook = DiscordWebhook(url=discord_url, timeout=NETWORK_TIMEOUT)
                title = textwrap.shorten(msg, width=256, placeholder="...")
                if len(msg) > 256:
                    embed = DiscordEmbed(title=title, description=msg[:4096])
                else:
                    embed = DiscordEmbed(title=title)
                webhook.add_embed(embed)
                response = webhook.execute()
                if response is None:
                    logger.error("Discord: execute() returned None (no response)")
                    results["discord"] = False
                else:
                    # execute() returns Response or list of Response (on rate limit)
                    responses = response if isinstance(response, list) else [response]
                    failed = any(
                        r and hasattr(r, "status_code") and r.status_code >= 400
                        for r in responses
                    )
                    if failed:
                        codes = [r.status_code for r in responses if hasattr(r, "status_code")]
                        logger.error("Discord: server returned status %s", codes)
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

            # SSRF validation — full URL validated strictly, ID validated with regex
            slack_url = None
            if not slack_id:
                logger.warning("Slack: Empty webhook ID")
            elif slack_id.startswith("https://"):
                if _validate_webhook_url(slack_id, "hooks.slack.com", "/services/"):
                    slack_url = slack_id
                else:
                    logger.warning("Slack: Rejected invalid webhook URL")
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
