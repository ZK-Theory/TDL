"""Discovery replay.

Deliberately empty of imports: :mod:`research_system.discovery.replay.registry`
imports the lifecycle reducer modules, so eagerly importing the driver here
would make the package initialiser part of its own dependency chain.  Import
:func:`research_system.discovery.replay.driver.replay_discovery` directly.
"""

from __future__ import annotations
