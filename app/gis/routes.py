from flask import Blueprint, request
from app.auth.permissions import optional_jwt
from app.gis.service import get_gis_layers
from app.utils.responses import success_response

gis_bp = Blueprint("gis", __name__)


@gis_bp.route("/features", methods=["GET"])
@optional_jwt
def all_layers():
    user = getattr(request, "current_user", None)
    mine_id = request.args.get("mine_id")
    layers = get_gis_layers(user=user, mine_id=mine_id)
    return success_response(data=layers, message="GIS spatial layers loaded successfully")


@gis_bp.route("/violations", methods=["GET"])
@optional_jwt
def violation_layer():
    user = getattr(request, "current_user", None)
    mine_id = request.args.get("mine_id")
    layers = get_gis_layers(user=user, mine_id=mine_id)
    return success_response(data=layers.get("violations", {}), message="Violations GIS layer")


@gis_bp.route("/mines", methods=["GET"])
@optional_jwt
def mine_layer():
    user = getattr(request, "current_user", None)
    layers = get_gis_layers(user=user)
    return success_response(data=layers.get("mines", {}), message="Mines GIS layer")
