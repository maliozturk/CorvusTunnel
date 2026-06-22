# /*--------------------------------*- py -*-----------------------------*\
# | ___                 _____                  _                          |
# || _ \___ _ ___ ___ _|_   _|  _ _ _  _ _  ___| |                         |
# ||   / _ \ '_\ V / || || || || | ' \| ' \/ -_) |                         |
# ||_|_\___/_|  \_/ \_,_||_| \_,_|_||_|_||_\___|_|                         |
# |  CorvusTunnel  -  control AI agents from your phone  -  MIT            |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/crypto/__init__.py
# Description: End-to-end encryption package.
# \*---------------------------------------------------------------------*/

from corvustunnel.crypto.e2e import E2ECrypto, get_e2e_crypto

__all__ = ["E2ECrypto", "get_e2e_crypto"]
