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


def last_day_of_month(any_day):
    #获取每个月的最后一天
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
    return next_month - datetime.timedelta(days=next_month.day)


@st_bp.route("/query_branch", methods=['POST'])
def query_branch():
    """
    获取各支行在某时间区间内贷款金额
    :return:
    """
    try:
        js = json.loads(request.data)
    except Exception:
        return generate_error(ErrCode.PARAM_LOST, "参数解析失败")
    date_from = js.get("date_from", None)
    date_to = js.get("date_to", None)
    ts = datetime.date(int(date_from[:4]), int(date_from[4:]), 1)
    tt = datetime.date(int(date_to[:4]), int(date_to[4:]), last_day_of_month(datetime.date(int(date_to[:4]), int(date_to[4:]), 1)).day)
    result = database.session.query(LoanRecord.subbranch, database.func.sum(LoanRecord.total_fund)).\
        filter(LoanRecord.date <= tt).\
        filter(LoanRecord.date >= ts). \
        group_by(LoanRecord.subbranch).\
        all()
    branches = database.session.query(SubBranch.name).all()
    res = []
    for item in result:
        res.append({'branch': item[0], 'fund': float(item[1])})
        if item[0] in branches:
            branches.remove(item[0])
    for item in branches:
        res.append({'branch': item[0], 'fund': 0})
    return generate_success(res)