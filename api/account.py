"""
账户管理相关API
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from random import randint
from threading import Lock
from data_type import *
from ext import database
from api.__util import generate_error, pre_process, parse_sqlerror, generate_success, ErrCode

ac_bp = Blueprint('AccountManagement', 'AccountManagement', url_prefix='/account')

card_list = []
t_lock = Lock()


def account2dict(accounts: List[Union[Account, CheckingAccount, SavingAccount]]) -> Union[List[dict], dict]:
    def acc2d(account: List[Union[Account, CheckingAccount, SavingAccount]]):
        holder = []
        rels: List[RelationAccountCustomerBranch] = RelationAccountCustomerBranch.query.filter(
            RelationAccountCustomerBranch.account_id == account[0].account_id).all()
        for rel in rels:
            holder.append(rel.customer_id)
        return {
            'account_id': account[0].account_id,
            'refund': float(account[0].refund),
            'open_date': account[0].open_date.strftime('%Y-%m-%d'),
            'sub_branch': account[0].sub_branch,
            'recent_visit': account[0].recent_visit.strftime('%Y-%m-%d'),
            'type': account[0].type,
            'rate': float(account[2].rate) if account[2] is not None else None,
            'finance': account[2].finance if account[2] is not None else None,
            'overdraft': float(account[1].overdraft) if account[1] is not None else None,
            'holder': holder  # 持卡人列表
        }

    if not accounts:
        return []

    if isinstance(accounts, list):
        ret = []
        for account in accounts:
            ret.append(acc2d(account))
        return ret
    else:
        return acc2d(accounts)


@ac_bp.route('/create', methods=['POST'])
def create_account():
    """
    创建账户

{
                'account_id': account[0].account_id,
                'refund': float(account[0].refund),
                'open_date': account[0].open_date.strftime('%Y-%m-%d'),
                'sub_branch': account[0].sub_branch,
                'recent_visit': account[0].recent_visit.strftime('%Y-%m-%d'),
                'type': account[0].type,
                'rate': float(account[1].rate) if account[1] is not None else None,
                'finance': account[1].finance if account[1] is not None else None,
                'overdraft': float(account[2].overdraft) if account[2] is not None else None,
                'holder': holder  # 持卡人列表
            }
    :return:
    创建成功data区返回
    {
        'account_id': str
    }
    """
    data = pre_process()
    if not data.logged_in:
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    try:
        user_ids = data.data.get('holder')
        refund = data.data.get('refund')
        branch_name = data.data.get('sub_branch')
        ac_type = data.data.get('type')
        if ac_type == AccountType.SAVING:
            finance = data.data.get('finance')
            rate = data.data.get('rate')
        elif ac_type == AccountType.CHECKING:
            overdraft = data.data.get('overdraft')
        else:
            return generate_error(ErrCode.UNKNOWN_ACC_TYPE, "未知的账户类型 " + str(ac_type))
    except KeyError:
        return generate_error(ErrCode.PARAM_LOST, '创建账户所需数据不完整')
    card_id = randint(0, 10 ** 18)
    # 生成卡号
    t_lock.acquire(blocking=True)
    while str(card_id).zfill(19) in card_list:
        card_id += 1
    card_id = str(card_id).zfill(19)
    card_list.append(card_id)
    t_lock.release()
    # 执行插入操作
    transaction = database.session.begin()
    account = Account(
        card_id, branch_name, ac_type
    )
    database.session.add(account)
    if ac_type == AccountType.SAVING:
        database.session.add(SavingAccount(card_id, rate, finance))
    else:
        database.session.add(CheckingAccount(card_id, overdraft))
    # 验证支行-用户-账户类型限制
    for user in user_ids:
        database.session.add(RelationAccountCustomerBranch(card_id, user, ac_type, branch_name))
    # 提交验证及异常检测回滚
    try:
        database.session.commit()
    except IntegrityError as e:
        code, err_type, msg = parse_sqlerror(e)
        if code == 1062:
            response = generate_error(1062, 'UNIQUE约束失败。请注意同一用户不能在同一支行下创建了多个储蓄/支付账户')
        elif code == 1452:
            response = generate_error(1452, 'REFERENCE参照失败。请注意支行名/用户ID是否存在')
        else:
            response = generate_error(code, '未知SQL执行异常\n' + msg)
        transaction.rollback()
        t_lock.acquire(blocking=True)
        card_list.remove(card_id)
        t_lock.release()
        return response
    target = database.session.query(Account, CheckingAccount, SavingAccount).filter(Account.account_id == card_id). \
        outerjoin(CheckingAccount, Account.account_id == CheckingAccount.account_id). \
        outerjoin(SavingAccount, Account.account_id == SavingAccount.account_id).first()
    return generate_success(account2dict(target))


@ac_bp.route('/modify', methods=['POST'])
def modify():
    """
    更新账户信息
    json payload格式
{
                'account_id': account[0].account_id,
                'refund': float(account[0].refund),
                'open_date': account[0].open_date.strftime('%Y-%m-%d'),
                'sub_branch': account[0].sub_branch,
                'recent_visit': account[0].recent_visit.strftime('%Y-%m-%d'),
                'type': account[0].type,
                'rate': float(account[1].rate) if account[1] is not None else None,
                'finance': account[1].finance if account[1] is not None else None,
                'overdraft': float(account[2].overdraft) if account[2] is not None else None,
                'holder': holder  # 持卡人列表
            }
    :return:
    """
    data = pre_process()
    if not data.logged_in:
        return generate_error(ErrCode.NO_LOGIN, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    account_id = data.data.get('account_id', None)
    if not account_id:
        return generate_error(ErrCode.PARAM_LOST, '请求信息缺少账户ID')
    holders = data.data.get('holder', [])
    account: Account = Account.query.filter(Account.account_id == account_id).first()
    if not holders:
        return generate_error(ErrCode.PARAM_LOST, '无法获取持卡人列表或列表为空')
    if not account:
        return generate_error(400, '待修改的账户不存在')
    refund = data.data.get('refund', None)
    if refund is None:
        return generate_error(400, '请求信息缺少目标值')
    account.refund = refund
    s_ac: Optional[SavingAccount] = None
    c_ac: Optional[CheckingAccount] = None
    if account.type == AccountType.SAVING:
        rate = data.data.get('rate', None)
        finance = data.data.get('finance', None)
        if rate is None or finance is None:
            return generate_error(ErrCode.PARAM_LOST, '请求信息缺少目标值')
        s_ac = SavingAccount.query.filter(SavingAccount.account_id == account_id).first()
        s_ac.rate = rate
        s_ac.finance = finance
    elif account.type == AccountType.CHECKING:
        overdraft = data.data.get('overdraft', None)
        if overdraft is None:
            return generate_error(ErrCode.PARAM_LOST, '请求信息缺少目标值')
        c_ac = CheckingAccount.query.filter(CheckingAccount.account_id == account_id).first()
        c_ac.overdraft = overdraft
    transaction = database.session.begin()
    database.session.add(account)
    if s_ac:
        database.session.add(s_ac)
    if c_ac:
        database.session.add(c_ac)
    # 处理所有用户变更：
    # 移除被取消关联的账户
    rels: List[RelationAccountCustomerBranch] = RelationAccountCustomerBranch.query.filter(
        RelationAccountCustomerBranch.account_id == account_id).all()
    for rel in rels:
        if rel.customer_id not in holders:
            database.session.delete(rel)
        else:
            holders.remove(rel.customer_id)
    # 添加新关联的账户
    for hold in holders:
        database.session.add(
            RelationAccountCustomerBranch(account_id, hold, account.type, account.sub_branch)
        )
    try:
        database.session.commit()
    except IntegrityError as e:
        transaction.rollback()
        return generate_error(500, str(e))
    target = database.session.query(Account, CheckingAccount, SavingAccount).filter(Account.account_id == account_id). \
        outerjoin(CheckingAccount, Account.account_id == CheckingAccount.account_id). \
        outerjoin(SavingAccount, Account.account_id == SavingAccount.account_id).first()
    return generate_success(account2dict(target))


@ac_bp.route('/query', methods=['POST'])
def query_account():
    """
    查询账户信息
    json payload格式
    {
        'method': int,        // 检索类型
        'keyword': str
    }
    :return:
    返回值包含账户所有信息，若有别的账户类型特有的字段则为None
    """

    data = pre_process()
    if not data.logged_in:
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    search_method = data.data.get('method', None)
    keyword = data.data.get('keyword', None)
    if search_method is None or keyword is None:
        return generate_error(400, '请求信息缺少必要值')
    target: Optional[List[Union[Account, CheckingAccount, SavingAccount]]]
    if search_method == SearchMethod.ACCOUNT_ID:
        target = database.session.query(Account, CheckingAccount, SavingAccount).filter(Account.account_id == keyword). \
            outerjoin(CheckingAccount, Account.account_id == CheckingAccount.account_id). \
            outerjoin(SavingAccount, Account.account_id == SavingAccount.account_id).all()
    elif search_method == SearchMethod.ACCOUNT_TYPE:
        try:
            keyword = int(keyword)
            if keyword != AccountType.SAVING and keyword != AccountType.CHECKING:
                raise ValueError
        except ValueError:
            return generate_error(600, f'未知账户类型: {keyword}')
        target = database.session.query(Account, CheckingAccount, SavingAccount).filter(Account.type == keyword). \
            outerjoin(CheckingAccount, Account.account_id == CheckingAccount.account_id). \
            outerjoin(SavingAccount, Account.account_id == SavingAccount.account_id).all()
    elif search_method == SearchMethod.BRANCH_NAME:
        target = database.session.query(Account, CheckingAccount, SavingAccount).filter(Account.sub_branch == keyword). \
            outerjoin(CheckingAccount, Account.account_id == CheckingAccount.account_id). \
            outerjoin(SavingAccount, Account.account_id == SavingAccount.account_id).all()
    elif search_method == SearchMethod.CUSTOMER_ID:
        target = database.session.query(Account, CheckingAccount, SavingAccount, RelationAccountCustomerBranch). \
            filter(RelationAccountCustomerBranch.customer_id == keyword). \
            outerjoin(Account, RelationAccountCustomerBranch.account_id == Account.account_id). \
            outerjoin(CheckingAccount, Account.account_id == CheckingAccount.account_id). \
            outerjoin(SavingAccount, Account.account_id == SavingAccount.account_id).all()
    else:
        return generate_error(600, f'未知搜索类型: {search_method}')
    return generate_success(account2dict(target))


@ac_bp.route('/delete', methods=['POST'])
def delete_account():
    """
    删除账户
    :return:
    """
    data = pre_process()
    if not data.logged_in:
        return generate_error(ErrCode.NO_LOGIN, data.login_message)
    if not data.data:
        return generate_error(ErrCode.PARAM_LOST, data.error_message)
    account_id = data.data.get('account_id', None)
    if not account_id:
        return generate_error(400, '请求信息缺少账户ID')
    account: Account = Account.query.filter(Account.account_id == account_id).first()
    if not account:
        return generate_error(400, '将要删除的账户不存在')
    database.session.begin()
    # 删除关联的所有binding信息
    try:
        if account.type == AccountType.SAVING:
            SavingAccount.query.filter(SavingAccount.account_id == account_id).delete()
        else:
            CheckingAccount.query.filter(CheckingAccount.account_id == account_id).delete()
        RelationAccountCustomerBranch.query.filter(RelationAccountCustomerBranch.account_id == account_id).delete()
        database.session.delete(account)
        database.session.commit()
    except IntegrityError as e:
        return generate_error(ErrCode.SQL_UNKNOWN_ERROR, str(e))
    return generate_success()


@ac_bp.route('/get_all', methods=['GET'])
def get_account_list():
    target = database.session.query(Account, CheckingAccount, SavingAccount). \
        outerjoin(CheckingAccount, Account.account_id == CheckingAccount.account_id). \
        outerjoin(SavingAccount, Account.account_id == SavingAccount.account_id).all()
    return generate_success(account2dict(target))
