"""
贷款相关API
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from data_type import *
from ext import database
from api.__util import generate_error, pre_process, parse_sqlerror, ErrCode, generate_success
from math import isclose

la_bp = Blueprint("Loan", "Loan", url_prefix='/loan')


def loan2json(loans: Union[List[LoanRecord], LoanRecord]):
    def l2j(loan: LoanRecord):
        users = []
        paid = []
        usr_list: List[RelationLoanUsr] = RelationLoanUsr.query.filter(RelationLoanUsr.loan_id == loan.loan_id).all()
        for user in usr_list:
            users.append(user.user_id)
        paid_list: List[PaidRecord] = PaidRecord.query.filter(PaidRecord.loan_id == loan.loan_id).all()
        for h in paid_list:
            paid.append({
                'id': h.id,
                'date': h.date.strftime('%Y-%m-%d'),
                'fund': float(h.fund)
            })
        return {
            'loan_id': loan.loan_id,
            'total': float(loan.total_fund),
            'branch': loan.subbranch,
            'create_date': loan.date.strftime('%Y-%m-%d'),
            'customers': users,
            'paid_history': paid
        }

    ret = []
    if isinstance(loans, list):
        for loan in loans:
            ret.append(l2j(loan))
        return ret
    else:
        return l2j(loans)


@la_bp.route('/create', methods=['POST'])
def create_loan():
    """
    添加一笔贷款信息
    json payload:
    {
        user_list: [str, ...],  // 持有贷款的用户列表
        total_fund: float,      // 贷款总金额
        sub_branch: str         // 发放的支行
    }
    :return:
    loan_id: 贷款ID
    """
    data = pre_process()
    if not data.logged_in:
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    user_ids: list = data.data.get('user_list', None)
    total_fund = data.data.get('total_fund', None)
    sub_branch = data.data.get('sub_branch', None)
    if user_ids is None or total_fund is None or sub_branch is None:
        return generate_error(ErrCode.PARAM_LOST, "缺少必要参数")
    if not isinstance(user_ids, list):
        return generate_error(ErrCode.PARAM_TYPE_MISMATCH, "参数类型异常")
    if len(user_ids) == 0:
        return generate_error(ErrCode.USER_LIST_EMPTY, "用户列表为空")
    # 添加信息
    record = LoanRecord(sub_branch, total_fund)
    transaction = database.session.begin()
    try:
        database.session.add(record)
        for user in user_ids:
            database.session.add(RelationLoanUsr(user, record.loan_id))
        database.session.commit()
    except IntegrityError:
        transaction.rollback()
        return generate_error(ErrCode.SQL_REFERENCE_ERROR, "SQL插入异常，可能出现参照或重复错误")
    return generate_success(loan2json(record))


@la_bp.route('/pay', methods=['POST'])
def pay_loan():
    """
    发放贷款
    json payload
    {
        loan_id: str,       // 贷款ID
        fund: float,        // 发放金额
    }
    :return:
    """
    data = pre_process()
    if not data.logged_in:
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    loan_id: list = data.data.get('loan_id', None)
    fund = data.data.get('fund', None)
    if loan_id is None or fund is None:
        return generate_error(ErrCode.PARAM_LOST, "缺少必要参数")
    if not (isinstance(fund, float) or isinstance(fund, int)) or fund < 0:
        return generate_error(ErrCode.PARAM_TYPE_MISMATCH, "参数类型异常")
    # 检查是否超出额度
    loan: LoanRecord = LoanRecord.query.filter(LoanRecord.loan_id == loan_id).first()
    if not loan:
        return generate_error(ErrCode.LOAN_NO_EXIST, "贷款记录不存在")
    paid_loan = database.session.query(database.func.coalesce(database.func.sum(PaidRecord.fund), 0)).filter(PaidRecord.loan_id == loan_id).first()
    if float(paid_loan[0]) + fund > float(loan.total_fund):
        return generate_error(ErrCode.LOAN_TOO_MUCH, "贷款付款超出最大值")
    # 插入支付信息
    record = PaidRecord(loan_id, fund)
    transaction = database.session.begin()
    try:
        database.session.add(record)
        database.session.commit()
    except IntegrityError:
        transaction.rollback()
        return generate_error(ErrCode.SQL_UNKNOWN_ERROR, "插入数据失败(未知异常)")
    return generate_success(loan2json(loan))


@la_bp.route('/delete', methods=['POST'])
def delete_loan():
    """
    删除贷款信息
    json payload
    {
        loan_id: str        // 贷款ID
    }
    :return:
    """
    data = pre_process()
    if not data.logged_in:
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    loan_id: list = data.data.get('loan_id', None)
    if loan_id is None:
        return generate_error(ErrCode.PARAM_LOST, "缺少必要参数")
    # 检查是否已经完成发放
    loan: LoanRecord = LoanRecord.query.filter(LoanRecord.loan_id == loan_id).first()
    if not loan:
        return generate_error(ErrCode.LOAN_NO_EXIST, "贷款记录不存在")
    paid_loan = database.session.query(database.func.coalesce(database.func.sum(PaidRecord.fund), 0)).filter(PaidRecord.loan_id == loan_id).first()
    if not isclose(float(paid_loan[0]), float(loan.total_fund), rel_tol=1e-03):
        return generate_error(ErrCode.LOAN_STILL_PAYING, "不允许删除未发放完成的贷款信息")
    # 删除相关信息
    transaction = database.session.begin()
    try:
        database.session.query(PaidRecord).filter(PaidRecord.loan_id == loan_id).delete()
        database.session.query(RelationLoanUsr).filter(RelationLoanUsr.loan_id == loan_id).delete()
        database.session.query(LoanRecord).filter(LoanRecord.loan_id == loan_id).delete()
        database.session.commit()
    except IntegrityError:
        transaction.rollback()
        return generate_error(ErrCode.SQL_UNKNOWN_ERROR, "SQL执行异常")
    return generate_success()


@la_bp.route('/query', methods=['POST'])
def query_loan():
    """
    查询贷款信息
    json payload
    {
        keyword: str,   // 关键词
        method: int     // 查询方法
    }
    :return:
    """

    data = pre_process()
    if not data.logged_in:
        return generate_error(403, data.login_message)
    if not data.data:
        return generate_error(400, data.error_message)
    keyword: str = data.data.get('keyword', None)
    method: int = data.data.get('method', None)
    if keyword is None or method is None:
        return generate_error(ErrCode.PARAM_LOST, "缺少必要参数")
    if method not in [SearchMethod.LOAN_ID, SearchMethod.CUSTOMER_ID, SearchMethod.BRANCH_NAME]:
        return generate_error(ErrCode.PARAM_TYPE_MISMATCH, "未知的关键词类型")
    result: List[LoanRecord] = []
    if method == SearchMethod.LOAN_ID:
        result = LoanRecord.query.filter(LoanRecord.loan_id == keyword).all()
    elif method == SearchMethod.BRANCH_NAME:
        result = LoanRecord.query.filter(LoanRecord.subbranch == keyword).all()
    elif method == SearchMethod.CUSTOMER_ID:
        result = database.session.query(LoanRecord).filter(LoanRecord.loan_id.in_(
            database.session.query(RelationLoanUsr.loan_id).filter(RelationLoanUsr.user_id == keyword).all())).all()
    return generate_success(loan2json(result))


@la_bp.route('/get_all', methods=['POST', 'GET'])
def get_all():
    loan: List[LoanRecord] = LoanRecord.query.all()
    return generate_success(loan2json(loan))