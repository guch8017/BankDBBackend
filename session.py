import config
import uuid
import time
from database import pool


class Session:

    @staticmethod
    def create_session(user: str) -> str:
        """
        使用密码登陆系统，生成新Session
        :param user: 用户ID
        :return: 返回给客户端的Session
        """
        _session = str(uuid.uuid4())
        conn = pool.connection()
        cursor = conn.cursor()
        cursor.execute("update Session set session=%s, last_use_time=%s where user_id=%s;", (_session, int(time.time()), user))
        cursor.close()
        conn.commit()
        conn.close()
        return _session

    @staticmethod
    def verify_session(user: str, session: str) -> bool:
        """
        检查Session有效性
        若有效则更新最后使用时间
        :param user:
        :param session:
        :return:
        """
        conn = pool.connection()
        cursor = conn.cursor()
        cursor.execute("SELECT session, last_use_time FROM Session WHERE user_id=%s;", (user, ))
        res = cursor.fetchone()
        if res is None or res[0] != session or res[1] - int(time.time()) > config.SEC_VALID_TIME:
            return False
        cursor.execute("UPDATE Session SET last_use_time=%s WHERE user_id=%s;", (int(time.time()), user))
        cursor.close()
        conn.commit()
        conn.close()
        return True
