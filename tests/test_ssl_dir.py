"""Tests for writable SSL directory resolution in Easy HTTPS."""

import os
from unittest.mock import MagicMock, patch

import pytest

import custom_components.easy_https as easy_https


def _hass_with_config_path(tmp_path):
    hass = MagicMock()
    hass.config.path = lambda *parts: os.path.join(str(tmp_path), "config", *parts)
    return hass


def test_default_ssl_dir_used_when_writable(tmp_path):
    default_dir = tmp_path / "ssl"
    hass = _hass_with_config_path(tmp_path)

    with patch.object(easy_https, "DEFAULT_SSL_DIR", str(default_dir)):
        assert easy_https.get_ssl_dir(hass) == str(default_dir)

    # Probe file must not be left behind
    assert not any(p.name.startswith(".easy_https") for p in default_dir.iterdir())


def test_falls_back_when_default_dir_read_only(tmp_path):
    """A /ssl that exists but is not writable must not be selected."""
    default_dir = tmp_path / "ssl"
    default_dir.mkdir()
    default_dir.chmod(0o555)
    hass = _hass_with_config_path(tmp_path)

    try:
        with patch.object(easy_https, "DEFAULT_SSL_DIR", str(default_dir)):
            result = easy_https.get_ssl_dir(hass)
    finally:
        default_dir.chmod(0o755)

    assert result == hass.config.path("ssl")
    assert os.path.isdir(result)


def test_raises_when_no_candidate_writable(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o555)
    hass = MagicMock()
    hass.config.path = lambda *parts: str(locked / "config-ssl")

    try:
        with patch.object(easy_https, "DEFAULT_SSL_DIR", str(locked / "ssl")):
            with pytest.raises(OSError):
                easy_https.get_ssl_dir(hass)
    finally:
        locked.chmod(0o755)
