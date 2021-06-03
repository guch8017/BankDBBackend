"""
账户管理相关API
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from random import randint
from threading import Lock
from data_type import *
from ext import database
from api.__util import generate_error, pre_process, parse_sqlerror, generate_success

ac_bp = Blueprint('AccountManagement', 'AccountManagement', url_prefix='/account')

card_list = []
t_lock = Lock()


@ac_bp.route('/create', methods=['POST'])
def create_account():
    """
    创建账户

    json payload格式
    {
        'customer': str,    // 客户ID
        'branch': str,      // 支行名
        'type': int,        // 账户类型 0: 储蓄， 1: 支票
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
        user_id = data.data.get('customer')
        branch_name = data.data.get('branch')
        ac_type = data.data.get('type')
    except KeyError:
        return generate_error(400, '创建账户所需数据不完整')
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
    database.session.add(Account(
        card_id, branch_name, ac_type
    ))
    if ac_type == 0:
        database.session.add(SavingAccount(card_id))
    else:
        database.session.add(CheckingAccount(card_id))
    # 验证支行-用户-账户类型限制
    database.session.add(RelationAccountCustomerBranch(card_id, user_id, ac_type, branch_name))
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
    return generate_success({'account_id': card_id})


@ac_bp.route('/bind', methods=['POST'])
def bind_customer():
    """
    将一个账户绑定到某个用户
    json payload格式
    {
        'customer': str,    // 客户ID
        'account_id': str   // 账户ID
    }
    :return:
    * 重复错误：账户已经被关联
    * 重复错误：客户已经在某个支行拥有储蓄/支票账户
    * 参照错误：客户不存在/银行账户不存在
    """
    data = pre_process()
    if not data.logged_in:
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    account_id = data.data.get('account_id', None)
    customer_id = data.data.get('customer', None)
    if not account_id or not customer_id:
        return generate_error(400, '请求信息不完整')
    # 验证账户是否存在并获取信息
    account: Account = Account.query.filter(Account.account_id == account_id)
    if not account:
        return generate_error(500, '待绑定的账户不存在')
    transaction = database.session.begin()
    rel = RelationAccountCustomerBranch(account_id, customer_id, account.type, account.sub_branch)
    try:
        database.session.add(rel)
        database.session.commit()
    except IntegrityError as e:
        transaction.rollback()
        code, err_type, msg = parse_sqlerror(e)
        if code == 1062:
            response = generate_error(1062, 'UNIQUE约束失败。请注意同一用户不能在同一支行下绑定多个储蓄/支付账户')
        elif code == 1452:
            response = generate_error(1452, 'REFERENCE参照失败。请注意用户ID是否存在')
        else:
            response = generate_error(code, '未知SQL执行异常\n' + msg)
        return response
    return generate_success()


@ac_bp.route('/unbind', methods=['POST'])
def unbind():
    """
    将一个账户与用户解绑
    json payload格式
    {
        'customer': str,    // 客户ID
        'account_id': str   // 账户ID
    }
    :return:
    * 客户ID或账户ID不存在
    * 客户未绑定至账户
    * 账户仅关联了一个账户
    """
    data = pre_process()
    if not data.logged_in:
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    account_id = data.data.get('account_id', None)
    customer_id = data.data.get('customer', None)
    if not account_id or not customer_id:
        return generate_error(400, '请求信息不完整')
    # 检查存在性
    account: Account = Account.query.filter(Account.account_id == account_id)
    customer: Customer = Customer.query.filter(Customer.user_id == customer_id)
    if not account:
        return generate_error(500, '账户不存在')
    if not customer:
        return generate_error(500, '客户不存在')
    rel: RelationAccountCustomerBranch = RelationAccountCustomerBranch.query.filter(
        database.and_(RelationAccountCustomerBranch.customer_id == customer_id,
                      RelationAccountCustomerBranch.account_id == account_id)).first()
    if not rel:
        return generate_error(500, '该客户未绑定至该账户')
    # 检查绑定数
    cnt = RelationAccountCustomerBranch.query.filter(
        RelationAccountCustomerBranch.account_id == account_id).with_entities(
        database.func.count(RelationAccountCustomerBranch)).first()[0]
    if int(cnt) == 1:
        return generate_error(500, '账户绑定的客户数不能小于1')
    database.session.begin()
    database.session.delete(rel)
    database.session.commit()
    return generate_success()


@ac_bp.route('/modify', methods=['POST'])
def modify():
    """
    更新账户信息
    json payload格式
    {
        'account_id': str,  // 账户ID
        'refund': float,    // 余额
        'rate': float,      // 仅SavingAccount有此字段
        'finance': str,     // 仅SavingAccount有此字段
        'overdraft': str    // 仅CheckingAccount有此字段
    }
    :return:
    """
    data = pre_process()
    if not data.logged_in:
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    account_id = data.data.get('account_id', None)
    if not account_id:
        return generate_error(400, '请求信息缺少账户ID')
    account: Account = Account.query.filter(Account.account_id == account_id)
    if not account:
        return generate_error(400, '待修改的账户不存在')
    refund = data.data.get('refund', None)
    if not refund:
        return generate_error(400, '请求信息缺少目标值')
    account.refund = refund
    s_ac: Optional[SavingAccount] = None
    c_ac: Optional[CheckingAccount] = None
    if account.type == AccountType.SAVING:
        rate = data.data.get('rate', None)
        finance = data.data.get('finance', None)
        if rate is None or finance is None:
            return generate_error(400, '请求信息缺少目标值')
        s_ac = SavingAccount.query.filter(SavingAccount.account_id == account_id).first()
        s_ac.rate = rate
        s_ac.finance = finance
    elif account.type == AccountType.CHECKING:
        overdraft = data.data.get('overdraft', None)
        if overdraft is None:
            return generate_error(400, '请求信息缺少目标值')
        c_ac = CheckingAccount.query.filter(CheckingAccount.account_id == account_id).first()
        c_ac.overdraft = overdraft
    transaction = database.session.begin()
    database.session.add(account)
    if s_ac:
        database.session.add(s_ac)
    if c_ac:
        database.session.add(c_ac)
    try:
        database.session.commit()
    except IntegrityError as e:
        transaction.rollback()
        return generate_error(500, str(e))
    return generate_success()


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
    def account2dict(accounts: List[Union[Account, CheckingAccount, SavingAccount]]) -> List[dict]:
        if not accounts:
            return []
        ret = []
        for account in accounts:
            holder = []
            rels: List[RelationAccountCustomerBranch] = RelationAccountCustomerBranch.query.filter(RelationAccountCustomerBranch.account_id == account[0].account_id).all()
            for rel in rels:
                holder.append(rel.customer_id)
            ret.append({
                'account_id': account[0].account_id,
                'refund': float(account[0].refund),
                'open_date': account[0].open_date.strftime('YYYY-MM-DD'),
                'sub_branch': account[0].sub_branch,
                'recent_visit': account[0].recent_visit.strftime('YYYY-MM-DD'),
                'type': account[0].type,
                'rate': float(account[1].rate) if account[1] is not None else None,
                'finance': account[1].finance if account[1] is not None else None,
                'overdraft': float(account[2].overdraft) if account[2] is not None else None,
                'holder': holder    # 持卡人列表
            })
        return ret
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
        target = database.session.query(Account, CheckingAccount, SavingAccount).filter(Account.account_id == keyword).\
            outerjoin(CheckingAccount, Account.account_id == CheckingAccount.account_id).\
            outerjoin(SavingAccount, Account.account_id == SavingAccount.account_id).all()
    elif search_method == SearchMethod.ACCOUNT_TYPE:
        try:
            keyword = int(keyword)
            if keyword != AccountType.SAVING and keyword != AccountType.CHECKING:
                raise ValueError
        except ValueError:
            return generate_error(600, f'未知账户类型: {keyword}')
        target = database.session.query(Account, CheckingAccount, SavingAccount).filter(Account.type == keyword).\
            outerjoin(CheckingAccount, Account.account_id == CheckingAccount.account_id).\
            outerjoin(SavingAccount, Account.account_id == SavingAccount.account_id).all()
    elif search_method == SearchMethod.BRANCH_NAME:
        target = database.session.query(Account, CheckingAccount, SavingAccount).filter(Account.sub_branch == keyword).\
            outerjoin(CheckingAccount, Account.account_id == CheckingAccount.account_id). \
            outerjoin(SavingAccount, Account.account_id == SavingAccount.account_id).all()
    elif search_method == SearchMethod.CUSTOMER_ID:
        target = database.session.query(RelationAccountCustomerBranch, Account, CheckingAccount, SavingAccount).\
            filter(RelationAccountCustomerBranch.customer_id == keyword).\
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
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    account_id = data.data.get('account_id', None)
    if not account_id:
        return generate_error(400, '请求信息缺少账户ID')
    account: Account = Account.query.filter(Account.account_id == account_id)
    if not account:
        return generate_error(400, '将要删除的账户不存在')
    database.session.begin()
    database.session.delete(account)
    database.session.commit()
    return generate_success()