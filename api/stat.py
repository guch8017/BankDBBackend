from flask import Blueprint, request, jsonify
import json
from data_type import *
from api.__util import generate_error, pre_process, parse_sqlerror, generate_success, ErrCode
from sqlalchemy.exc import IntegrityError
from typing import List

st_bp = Blueprint("Statistic", "Statistic", url_prefix="/stat")


@st_bp.route("/query_user", methods=['POST'])
def query_user():
    """
    获取统计表格
    {
        "date_from": str,
        "date_to": str
    }
    :return:
    """
    try:
        js = json.loads(request.data)
    except Exception:
        return generate_error(ErrCode.PARAM_LOST, "参数解析失败")
    date_from = js.get("date_from", None)
    date_to = js.get("date_to", None)
    if not date_from or not date_to:
        return generate_error(ErrCode.PARAM_LOST, "缺少必要参数")
    result = database.session.query(Customer.create_time, database.func.count(Customer.user_id)).\
        filter(Customer.create_time >= date_from).\
        filter(Customer.create_time <= date_to).\
        group_by(Customer.create_time).\
        order_by(Customer.create_time).\
        all()
    res = []
    for item in result:
        res.append({'date': item[0], 'count': item[1]})
    return generate_success(res)


@st_bp.route("/query_user", methods=['POST'])
def query_branch():
    """
    获取各支行的用户数
    :return:
    """