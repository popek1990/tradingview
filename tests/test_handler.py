"""Tests for alert handler (with mocked channels)."""

import pytest
from unittest.mock import patch, MagicMock

from handler import send_alert


class TestSendAlert:
    def test_no_channels_enabled(self, monkeypatch):
        """No channels enabled — empty dict."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "False")
        results = send_alert({"msg": "test"})
        assert results == {}

    @patch("handler._get_tg_bot")
    def test_telegram_success(self, mock_bot, monkeypatch):
        """Telegram sends successfully — returns True."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "True")
        mock_instance = MagicMock()
        mock_bot.return_value = mock_instance

        results = send_alert({"msg": "test alert"})

        assert results["telegram"] is True
        mock_instance.sendMessage.assert_called_once()

    @patch("handler._get_tg_bot")
    def test_telegram_error(self, mock_bot, monkeypatch):
        """Telegram throws exception — returns False."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "True")
        mock_instance = MagicMock()
        mock_instance.sendMessage.side_effect = Exception("Connection error")
        mock_bot.return_value = mock_instance

        results = send_alert({"msg": "test"})

        assert results["telegram"] is False

    @patch("handler._get_tg_bot")
    def test_telegram_channel_override(self, mock_bot, monkeypatch):
        """Telegram uses channel from payload instead of default."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "True")
        mock_instance = MagicMock()
        mock_bot.return_value = mock_instance

        send_alert({"msg": "test", "telegram": "-999"})

        args = mock_instance.sendMessage.call_args
        assert args[0][0] == "-999"

    @patch("handler._get_tg_bot")
    def test_telegram_fallback_to_config(self, mock_bot, monkeypatch):
        """Telegram uses channel from config when no override."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "True")
        monkeypatch.setenv("CHANNEL", "-100999888")
        mock_instance = MagicMock()
        mock_bot.return_value = mock_instance

        send_alert({"msg": "test"})

        args = mock_instance.sendMessage.call_args
        assert args[0][0] == "-100999888"

    @patch("handler.requests.post")
    def test_slack_success(self, mock_post, monkeypatch):
        """Slack sends successfully — returns True."""
        monkeypatch.setenv("SEND_ALERTS_SLACK", "True")
        monkeypatch.setenv("SLACK_WEBHOOK", "https://hooks.slack.com/services/T/B/X")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"
        mock_post.return_value = mock_resp

        results = send_alert({"msg": "test slack"})

        assert results["slack"] is True
        mock_post.assert_called_once()

    @patch("handler.requests.post")
    def test_slack_server_error(self, mock_post, monkeypatch):
        """Slack returns error — returns False."""
        monkeypatch.setenv("SEND_ALERTS_SLACK", "True")
        monkeypatch.setenv("SLACK_WEBHOOK", "https://hooks.slack.com/services/T/B/X")
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        results = send_alert({"msg": "test"})

        assert results["slack"] is False

    @patch("handler.requests.post")
    def test_slack_response_not_ok(self, mock_post, monkeypatch):
        """Slack returns 200 but not 'ok' — returns False."""
        monkeypatch.setenv("SEND_ALERTS_SLACK", "True")
        monkeypatch.setenv("SLACK_WEBHOOK", "https://hooks.slack.com/services/T/B/X")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "no_service"
        mock_post.return_value = mock_resp

        results = send_alert({"msg": "test"})

        assert results["slack"] is False

    @patch("handler._get_tg_bot")
    def test_telegram_2_sent(self, mock_bot, monkeypatch):
        """Telegram sends to two groups when channel_2 set and toggle enabled."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "True")
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM_2", "True")
        monkeypatch.setenv("CHANNEL_2", "-100second_group")
        mock_instance = MagicMock()
        mock_bot.return_value = mock_instance

        results = send_alert({"msg": "test two groups"})

        assert results["telegram"] is True
        assert results["telegram_2"] is True
        assert mock_instance.sendMessage.call_count == 2

    @patch("handler._get_tg_bot")
    def test_telegram_2_empty_skipped(self, mock_bot, monkeypatch):
        """Telegram doesn't send to group 2 when channel_2 empty."""
        monkeypatch.setenv("SEND_ALERTS_TELEGRAM", "True")
        monkeypatch.setenv("CHANNEL_2", "")
        mock_instance = MagicMock()
        mock_bot.return_value = mock_instance

        results = send_alert({"msg": "test one group"})

        assert results["telegram"] is True
        assert "telegram_2" not in results
        mock_instance.sendMessage.assert_called_once()

    @patch("handler.DiscordWebhook")
    def test_discord_embed_short_msg(self, mock_webhook_cls, monkeypatch):
        """Discord — short message goes into title."""
        monkeypatch.setenv("SEND_ALERTS_DISCORD", "True")
        monkeypatch.setenv("DISCORD_WEBHOOK", "https://discord.com/api/webhooks/123/abc")
        mock_wh = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_wh.execute.return_value = mock_resp
        mock_webhook_cls.return_value = mock_wh

        results = send_alert({"msg": "Short alert"})

        assert results["discord"] is True

    @patch("handler.DiscordWebhook")
    def test_discord_embed_long_msg(self, mock_webhook_cls, monkeypatch):
        """Discord — long message (>256 chars) goes into description."""
        monkeypatch.setenv("SEND_ALERTS_DISCORD", "True")
        monkeypatch.setenv("DISCORD_WEBHOOK", "https://discord.com/api/webhooks/123/abc")
        mock_wh = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_wh.execute.return_value = mock_resp
        mock_webhook_cls.return_value = mock_wh

        long_msg = "A" * 300
        results = send_alert({"msg": long_msg})

        assert results["discord"] is True
        mock_wh.add_embed.assert_called_once()
