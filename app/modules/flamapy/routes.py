"""Flamapy endpoints removed.

This module kept as a placeholder to avoid import errors during transition.
All FlamaPy-related functionality has been removed. Endpoints return 410 Gone.
"""

from flask import jsonify

from app.modules.flamapy import flamapy_bp


@flamapy_bp.route("/flamapy/<path:rest>", methods=["GET", "POST", "PUT", "DELETE"])  # catch-all
def flamapy_removed(rest):
    return jsonify({"error": "FlamaPy functionality removed"}), 410
