import config
import uuid
import time
from typing import Tuple
from data_type import User


class Session:
    @staticmethod
    def login(user_id: str, password: str) -> Tuple[bool, str]:
        """
        登录系统
        :param user_id: 用户名
        :param password: 密码
        :return: 成功则返回Session值，失败则返回失败信息
        """
        user: User = User.query.filter_by(user_id=user_id).first()
        if not user:
            return False, '用户名不存在'
        if user.password != password:
            return False, '用户名与密码不匹配'
        session = str(uuid.uuid1())
        ts = int(time.time())
        User.query.filter_by(user_id=user_id).update({'last_use_time': ts, 'session_id': session})
        return True, session

    @staticmethod
    def verify_session(user_id: str, session: str) -> Tuple[bool, str]:
        """
        检查Session有效性
        若有效则更新最后使用时间
        :param user_id:
        :param session:
        :return:
        """
        user: User = User.query.filter_by(user_id=user_id).first()
        if not user:
            return False, 'SESSION用户名不存在'
        if user.session_id != session or int(time.time()) > user.last_use_time + config.SEC_VALID_TIME:
            return False, 'SESSION无效或已过期'
        else:
            User.query.filter_by(user_id=user_id).update({'last_use_time': int(time.time())})
            return True, '成功'

    @staticmethod
    def logout(user_id: str, session: str) -> Tuple[bool, str]:
        """
        登出
        :param user_id:
        :param session:
        :return:
        """
        user: User = User.query.filter_by(user_id=user_id).first()
        if not user:
            return False, "将要登出的账户不存在"
        if user.session_id != session:
            return False, "SESSION无效"
        else:
            User.query.filter_by(user_id=user_id).update({'session_id': None})
            return True, ''
