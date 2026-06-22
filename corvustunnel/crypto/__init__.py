# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/crypto/__init__.py
# Description: End-to-end encryption package.
# \*---------------------------------------------------------------------*/

from corvustunnel.crypto.channel import ServerIdentity, get_server_identity

__all__ = ["ServerIdentity", "get_server_identity"]
