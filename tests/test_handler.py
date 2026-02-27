"""Testy handlera alertow (z mockowanymi kanalami)."""

import pytest
from unittest.mock import patch, MagicMock

from handler import wyslij_alert


class TestWyslijAlert:
    def test_brak_wlaczonych_kanalow(self, monkeypatch):
        """Gdy brak wlaczonych kanalow — pusty dict."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "False")
        wyniki = wyslij_alert({"msg": "test"})
        assert wyniki == {}

    @patch("handler._pobierz_tg_bot")
    def test_telegram_sukces(self, mock_bot, monkeypatch):
        """Telegram wysyla poprawnie — zwraca True."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "True")
        mock_instance = MagicMock()
        mock_bot.return_value = mock_instance

        wyniki = wyslij_alert({"msg": "test alert"})

        assert wyniki["telegram"] is True
        mock_instance.sendMessage.assert_called_once()

    @patch("handler._pobierz_tg_bot")
    def test_telegram_blad(self, mock_bot, monkeypatch):
        """Telegram rzuca wyjatek — zwraca False."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "True")
        mock_instance = MagicMock()
        mock_instance.sendMessage.side_effect = Exception("Connection error")
        mock_bot.return_value = mock_instance

        wyniki = wyslij_alert({"msg": "test"})

        assert wyniki["telegram"] is False

    @patch("handler._pobierz_tg_bot")
    def test_telegram_override_kanalu(self, mock_bot, monkeypatch):
        """Telegram uzywa kanalu z payloadu zamiast domyslnego."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "True")
        mock_instance = MagicMock()
        mock_bot.return_value = mock_instance

        wyslij_alert({"msg": "test", "telegram": "-999"})

        args = mock_instance.sendMessage.call_args
        assert args[0][0] == "-999"

    @patch("handler._pobierz_tg_bot")
    def test_telegram_fallback_na_config(self, mock_bot, monkeypatch):
        """Telegram uzywa kanalu z configu gdy brak override."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "True")
        monkeypatch.setenv("KANAL", "-100domyslny")
        mock_instance = MagicMock()
        mock_bot.return_value = mock_instance

        wyslij_alert({"msg": "test"})

        args = mock_instance.sendMessage.call_args
        assert args[0][0] == "-100domyslny"

    @patch("handler.requests.post")
    def test_slack_sukces(self, mock_post, monkeypatch):
        """Slack wysyla poprawnie — zwraca True."""
        monkeypatch.setenv("WYSLIJ_ALERTY_SLACK", "True")
        monkeypatch.setenv("SLACK_WEBHOOK", "https://hooks.slack.com/services/T/B/X")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"
        mock_post.return_value = mock_resp

        wyniki = wyslij_alert({"msg": "test slack"})

        assert wyniki["slack"] is True
        mock_post.assert_called_once()

    @patch("handler.requests.post")
    def test_slack_blad_serwera(self, mock_post, monkeypatch):
        """Slack zwraca blad — zwraca False."""
        monkeypatch.setenv("WYSLIJ_ALERTY_SLACK", "True")
        monkeypatch.setenv("SLACK_WEBHOOK", "https://hooks.slack.com/services/T/B/X")
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        wyniki = wyslij_alert({"msg": "test"})

        assert wyniki["slack"] is False

    @patch("handler.requests.post")
    def test_slack_odpowiedz_nie_ok(self, mock_post, monkeypatch):
        """Slack zwraca 200 ale nie 'ok' — zwraca False."""
        monkeypatch.setenv("WYSLIJ_ALERTY_SLACK", "True")
        monkeypatch.setenv("SLACK_WEBHOOK", "https://hooks.slack.com/services/T/B/X")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "no_service"
        mock_post.return_value = mock_resp

        wyniki = wyslij_alert({"msg": "test"})

        assert wyniki["slack"] is False

    @patch("handler._pobierz_tg_bot")
    def test_telegram_2_wyslano(self, mock_bot, monkeypatch):
        """Telegram wysyla na dwie grupy gdy kanal_2 ustawiony i toggle wlaczony."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "True")
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM_2", "True")
        monkeypatch.setenv("KANAL_2", "-100druga_grupa")
        mock_instance = MagicMock()
        mock_bot.return_value = mock_instance

        wyniki = wyslij_alert({"msg": "test dwie grupy"})

        assert wyniki["telegram"] is True
        assert wyniki["telegram_2"] is True
        assert mock_instance.sendMessage.call_count == 2

    @patch("handler._pobierz_tg_bot")
    def test_telegram_2_pusty_pomijany(self, mock_bot, monkeypatch):
        """Telegram nie wysyla na grupe 2 gdy kanal_2 pusty."""
        monkeypatch.setenv("WYSLIJ_ALERTY_TELEGRAM", "True")
        monkeypatch.setenv("KANAL_2", "")
        mock_instance = MagicMock()
        mock_bot.return_value = mock_instance

        wyniki = wyslij_alert({"msg": "test jedna grupa"})

        assert wyniki["telegram"] is True
        assert "telegram_2" not in wyniki
        mock_instance.sendMessage.assert_called_once()

    @patch("handler.DiscordWebhook")
    def test_discord_embed_krotki_msg(self, mock_webhook_cls, monkeypatch):
        """Discord — krotka wiadomosc trafia do title."""
        monkeypatch.setenv("WYSLIJ_ALERTY_DISCORD", "True")
        monkeypatch.setenv("DISCORD_WEBHOOK", "https://discord.com/api/webhooks/123/abc")
        mock_wh = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_wh.execute.return_value = mock_resp
        mock_webhook_cls.return_value = mock_wh

        wyniki = wyslij_alert({"msg": "Krotki alert"})

        assert wyniki["discord"] is True

    @patch("handler.DiscordWebhook")
    def test_discord_embed_dlugi_msg(self, mock_webhook_cls, monkeypatch):
        """Discord — dluga wiadomosc (>256 zn.) trafia do description."""
        monkeypatch.setenv("WYSLIJ_ALERTY_DISCORD", "True")
        monkeypatch.setenv("DISCORD_WEBHOOK", "https://discord.com/api/webhooks/123/abc")
        mock_wh = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_wh.execute.return_value = mock_resp
        mock_webhook_cls.return_value = mock_wh

        dlugi_msg = "A" * 300
        wyniki = wyslij_alert({"msg": dlugi_msg})

        assert wyniki["discord"] is True
        # Sprawdz ze add_embed zostal wywolany
        mock_wh.add_embed.assert_called_once()

