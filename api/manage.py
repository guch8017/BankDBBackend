from flask import Blueprint, request, jsonify
import json
from api.__util import pre_process, generate_error
from api.session import Session

mg_bp = Blueprint('Manage', 'Manage', url_prefix='/manage')


@mg_bp.route('/login', methods=['POST'])
def login():
    # 不走统一验证，单独获取信息
    try:
        data: dict = json.loads(request.data)
    except json.JSONDecodeError as e:
        return generate_error(5, '登录参数解析失败')
    user_id = data.get('user_id', None)
    passwd = data.get('passwd', None)
    if not user_id or not passwd:
        return generate_error(6, '登录参数缺失')
    status, msg = Session.login(user_id, passwd)
    if not status:
        return generate_error(7, msg)
    else:
        return jsonify({
            'success': True,
            'msg': '',
            'code': 0,
            'data': {
                'session': msg
            }
        })


@mg_bp.route('/logout', methods=['POST'])
def logout():
    data = pre_process()
    if not data.logged_in:
        return generate_error(2, '您尚未登录，无法进行登出操作')
    status, msg = Session.logout(data.user_id, data.session)
    if not status:
        return generate_error(3, msg)
    else:
        return jsonify({
            'success': True,
            'msg': '',
            'code': 0
        })
