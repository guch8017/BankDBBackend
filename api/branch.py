from flask import Blueprint
from data_type import SubBranch
from api.__util import generate_success

sb_bp = Blueprint("SubBranch", "SubBranch", url_prefix='/branch')


@sb_bp.route('/get_all', methods=['POST', 'GET'])
def get_all():
    return generate_success([it.to_dict() for it in SubBranch.query.all()])
