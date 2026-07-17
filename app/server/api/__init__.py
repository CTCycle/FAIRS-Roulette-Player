from __future__ import annotations

"""API package marker.

Routers are imported by the application composition root so importing a
small endpoint module does not eagerly load the training and ML stack.
"""
