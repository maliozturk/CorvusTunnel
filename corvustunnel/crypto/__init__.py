# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/crypto/__init__.py
# Description: End-to-end encryption package.
# \*---------------------------------------------------------------------*/

from corvustunnel.crypto.e2e import E2ECrypto, get_e2e_crypto

__all__ = ["E2ECrypto", "get_e2e_crypto"]
