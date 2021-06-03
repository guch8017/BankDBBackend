from flask import Blueprint, request, jsonify
import json
from data_type import *
from api.__util import generate_error, pre_process, parse_sqlerror
from sqlalchemy.exc import IntegrityError
from typing import List

cs_bp = Blueprint('CustomerManagement', 'CustomerManagement', url_prefix='/customer')

"""
统一失败返回数据：
{
    'success':  False,
    'code':     int,
    'msg':      string
}
"""


@cs_bp.route('/add', methods=['POST'])
def add_customer():
    """
    新增客户
    API路径：/customer/add
    json payload格式
    {
        'identifier_id':'string',
        'name'      :   'string',
        'phone'     :   'string',
        'address'   :   'string',
        's_name'    :   'string',
        's_phone'   :   'string',
        's_email'   :   'string',
        's_rel'     :   'string'
    }
    """
    data = pre_process()
    if not data.logged_in:
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    # 检查Payload数据是否完整
    try:
        customer = Customer(data.data)
    except KeyError:
        return generate_error(400, '客户数据模型不完整')
    # 执行插入
    transaction = database.session.begin()
    try:
        database.session.add(customer)
        database.session.commit()
    except IntegrityError as e:
        try:
            transaction.rollback()
        except Exception:
            return generate_error(-1, '未知错误')
        return generate_error(400, '插入失败', str(parse_sqlerror(e)))
    return jsonify({
        'success': True,
        'msg': ''
    })


@cs_bp.route('/update', methods=['POST'])
def modify_customer():
    """
    更新客户信息
    API路径：/customer/update
    参数格式与add一致
    :return:
    """
    data = pre_process()
    if not data.logged_in:
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    user_id = data.data.get('identifier_id', None)
    if not user_id:
        return generate_error(400, '无法获取待更改的客户ID')
    customer: Customer = Customer.query.filter_by(user_id=user_id).first()
    if not customer:
        return generate_error(400, '无法获取待更改的用户信息，请注意用户ID无法被修改')
    try:
        customer.update(data.data)
    except KeyError:
        return generate_error(400, '客户数据模型不完整')
    # 执行更新操作
    database.session.begin()
    database.session.add(customer)
    database.session.commit()
    return jsonify({
        'success': True,
        'msg': ''
    })


@cs_bp.route('/delete', methods=['POST'])
def delete_customer():
    """
    删除客户
    API路径：/customer/delete
    json payload格式
    {
        'identifier_id': 'string'
    }
    :return:
    """
    data = pre_process()
    if not data.logged_in:
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    user_id = data.data.get('identifier_id', None)
    if not user_id:
        return generate_error(400, '无法获取待删除的客户ID')
    customer: Customer = Customer.query.filter_by(user_id=user_id).first()
    if not customer:
        return generate_error(400, '无法获取待删除的客户信息')
    transaction = database.session.begin()
    try:
        database.session.delete(customer)
        database.session.commit()
    except IntegrityError as e:
        try:
            transaction.rollback()
        except Exception:
            return generate_error(-1, '未知错误')
        return generate_error(400, '删除失败', str(parse_sqlerror(e)))
    return jsonify({
        'success': True,
        'msg': ''
    })


@cs_bp.route('/query', methods=['POST'])
def query_customer():
    """
    查询客户
    API路径：/customer/query
    json payload格式
    {
        'exact': bool,  // True为精确查询
        'mode': int,    // 0: 身份证号， 1: 姓名， 2: 电话
        'keyword': str  // 查询关键词
    }
    :return:
    """

    class SearchInfo:
        def __init__(self, sd: dict):
            self.exact = sd.get('exact')
            self.mode = sd.get('mode')
            self.keyword = sd.get('keyword')
            if not self.exact:
                self.keyword = f'%{self.keyword}%'

    data = pre_process()
    if not data.logged_in:
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    Customer.query.filter()
    try:
        search_info = SearchInfo(data.data)
    except KeyError:
        return generate_error(400, '无法获取搜索参数')
    if search_info.mode != int(search_info.mode) or not 0 <= search_info.mode <= 2:
        return generate_error(400, '未知的搜索模式')
    s_data: List[Customer] = []
    if search_info.exact:
        if search_info.mode == 0:
            s_data = Customer.query.filter(Customer.user_id == search_info.keyword).all()
        elif search_info.mode == 1:
            s_data = Customer.query.filter(Customer.name == search_info.keyword).all()
        elif search_info.mode == 2:
            s_data = Customer.query.filter(Customer.phone == search_info.keyword).all()
    else:
        if search_info.mode == 0:
            s_data = Customer.query.filter(Customer.user_id.like(search_info.keyword)).all()
        elif search_info.mode == 1:
            s_data = Customer.query.filter(Customer.name.like(search_info.keyword)).all()
        elif search_info.mode == 2:
            s_data = Customer.query.filter(Customer.phone.like(search_info.keyword)).all()
    return jsonify({
        'success': True,
        'msg': '',
        'data': [it.to_dict() for it in s_data]
    })