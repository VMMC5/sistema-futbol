"""Pruebas de email_utils: timeout del SMTP y el envoltorio best-effort."""
import smtplib

from app import email_utils


class _SMTPFalso:
    """Captura los argumentos de smtplib.SMTP sin abrir conexiones."""

    ultimo = None

    def __init__(self, host, puerto, timeout=None):
        _SMTPFalso.ultimo = {"host": host, "puerto": puerto, "timeout": timeout}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        pass

    def login(self, usuario, password):
        pass

    def send_message(self, mensaje):
        pass


def test_smtp_real_lleva_timeout(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.ejemplo.com")
    monkeypatch.setattr(smtplib, "SMTP", _SMTPFalso)
    email_utils.enviar_correo("a@demo.com", "Asunto", "Cuerpo")
    assert _SMTPFalso.ultimo["timeout"] == 10


def test_sin_smtp_no_toca_la_red(monkeypatch, capsys):
    monkeypatch.delenv("SMTP_HOST", raising=False)

    def _explota(*args, **kwargs):
        raise AssertionError("sin SMTP_HOST no debe abrirse conexión")

    monkeypatch.setattr(smtplib, "SMTP", _explota)
    email_utils.enviar_correo("a@demo.com", "Asunto", "Cuerpo")
    assert "CORREO SIMULADO" in capsys.readouterr().out


def test_enviar_correo_seguro_atrapa_y_loguea_sin_pii(monkeypatch, caplog):
    def _smtp_caido(*args, **kwargs):
        raise RuntimeError("smtp caído")

    monkeypatch.setattr(email_utils, "enviar_correo", _smtp_caido)
    with caplog.at_level("ERROR"):
        # No debe lanzar:
        email_utils.enviar_correo_seguro("secreto@demo.com", "Asunto X", "cuerpo con password")
    assert "RuntimeError" in caplog.text
    assert "secreto@demo.com" not in caplog.text
    assert "password" not in caplog.text
