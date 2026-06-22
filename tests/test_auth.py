# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        tests/test_auth.py
# Description: Tests for the boot/session TokenManager (claim, one-time
#              consumption, session verification).
# \*---------------------------------------------------------------------*/


class TestTokenManager:
    def test_verify_with_boot_token(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()
        assert mgr.verify(env_token) is True

    def test_verify_with_wrong_token(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()
        assert mgr.verify("wrong-token") is False

    def test_claim_boot_token(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()
        session_token = mgr.claim_boot_token(env_token)
        assert session_token is not None
        assert len(session_token) > 20
        assert mgr.is_claimed is True

    def test_boot_token_consumed_after_claim(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()
        session_token = mgr.claim_boot_token(env_token)
        assert session_token is not None
        assert mgr.verify(env_token) is False
        assert mgr.verify(session_token) is True

    def test_claim_fails_with_wrong_token(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()
        assert mgr.claim_boot_token("wrong-token") is None
        assert mgr.is_claimed is False

    def test_double_claim_rejected(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()
        assert mgr.claim_boot_token(env_token) is not None
        assert mgr.claim_boot_token(env_token) is None

    def test_session_verify_without_ip(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()
        session_token = mgr.claim_boot_token(env_token)
        assert mgr.verify(session_token) is True
