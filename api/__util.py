from flask import request, jsonify
from api.session import Session
from typing import Optional, Union
from sqlalchemy.exc import IntegrityError
import json


class RequestData:
    def __init__(self, lg, uid, data, err, lmsg, session):
        self.logged_in: bool = lg
        self.user_id: str = uid
        self.data: dict = data
        self.error_message: str = err
        self.login_message: str = lmsg
        self.session: str = session


SQLError = {
    1062: 'ER_DUP_ENTRY',
    1451: 'ER_ROW_IS_REFERENCED_2',
    1452: 'ER_NO_REFERENCED_ROW_2'
}


class SQLErr:
    DUPLICATE_ENTRY = 1062
    ROW_REFERENCED = 1451
    NO_REFERENCE = 1452


class ErrCode:
    NO_LOGIN = 403


def generate_error(code: int, message: str, sql_error: Optional[str] = None):
    data = {
        'success': False,
        'code': code,
        'msg': message
    }
    if sql_error:
        data.update({'sql_err': sql_error})
    return jsonify(data)


def generate_success(data: Optional[Union[dict, list]] = None):
    if data is None:
        dt = jsonify({
            'success': True,
            'msg': '',
            'code': 0,
        })
    else:
        dt = jsonify({
                'success': True,
                'msg': '',
                'code': 0,
                'data': data
            })
    return dt


def pre_process() -> RequestData:
    """
    预处理请求
    检查登录状态，反序列化数据
    ** 一定要在请求环境中调用，否则出错 **
    :return:
    """
    user_id = request.headers.get('USER_ID', None)
    session = request.headers.get('SESSION', None)
    err_msg = ''
    msg = ''
    data = None
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError as e:
        print(e)
        err_msg = '无法解析数据'
    logged = user_id and session
    if logged:
        logged, msg = Session.verify_session(user_id, session)
    return RequestData(logged, user_id, data, err_msg, msg, session)


def parse_sqlerror(err: IntegrityError):
    arg = err.args[0]
    arg = arg[29:]
    err_tuple = eval(arg)
    return err_tuple[0], SQLError.get(err_tuple[0], 'UNKNOWN'), err_tuple[1]
