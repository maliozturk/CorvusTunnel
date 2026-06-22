# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        tests/test_client_ip.py
# Description: Tests for trusted client-IP resolution.
# \*---------------------------------------------------------------------*/




class _Client:
    def __init__(self, host):
        self.host = host


class _Conn:
    def __init__(self, peer, headers=None):
        self.client = _Client(peer) if peer else None
        self.headers = headers or {}


class TestTrustedClientIP:
    def test_xff_trusted_from_loopback(self, env_token):
        from corvustunnel.middleware.client_ip import get_trusted_client_ip

        conn = _Conn("127.0.0.1", {"x-forwarded-for": "203.0.113.7, 10.0.0.1"})
        assert get_trusted_client_ip(conn) == "203.0.113.7"

    def test_xff_ignored_from_untrusted_peer(self, env_token):
        from corvustunnel.middleware.client_ip import get_trusted_client_ip

        conn = _Conn("198.51.100.99", {"x-forwarded-for": "127.0.0.1"})
        assert get_trusted_client_ip(conn) == "198.51.100.99"

    def test_no_xff_uses_peer(self, env_token):
        from corvustunnel.middleware.client_ip import get_trusted_client_ip

        conn = _Conn("198.51.100.50", {})
        assert get_trusted_client_ip(conn) == "198.51.100.50"

    def test_no_client_returns_unknown(self, env_token):
        from corvustunnel.middleware.client_ip import get_trusted_client_ip

        conn = _Conn(None, {})
        assert get_trusted_client_ip(conn) == "unknown"

    def test_configured_trusted_proxy(self, monkeypatch, env_token):
        import corvustunnel.config.settings as settings_mod
        from corvustunnel.middleware.client_ip import get_trusted_client_ip

        monkeypatch.setenv("TRUSTED_PROXIES", "10.1.2.3")
        settings_mod.get_settings.cache_clear()
        try:
            conn = _Conn("10.1.2.3", {"x-forwarded-for": "203.0.113.42"})
            assert get_trusted_client_ip(conn) == "203.0.113.42"
        finally:
            settings_mod.get_settings.cache_clear()
