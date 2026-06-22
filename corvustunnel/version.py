"""Single source of truth for the CorvusTunnel version.

Every module that needs the version string imports it from here so the
package, CLI, HTTP banner, and /health endpoint can never drift apart.
"""

__version__ = "1.1.0"
