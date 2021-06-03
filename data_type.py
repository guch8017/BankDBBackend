from ext import database
from typing import Optional, Union, List
import uuid
import datetime


class AccountType:
    SAVING = 0
    CHECKING = 1


class SearchMethod:
    ACCOUNT_ID = 0  # 以账户ID搜索
    BRANCH_NAME = 1  # 以开卡支行搜索
    ACCOUNT_TYPE = 2  # 以账户类型搜索
    CUSTOMER_ID = 3  # 以持有卡的客户的ID搜索/持有贷款的客户

    LOAN_ID = 0     # 贷款ID


class User(database.Model):
    __tablename__ = 'user'
    user_id = database.Column(database.CHAR(length=18), primary_key=True)
    password = database.Column(database.CHAR(length=32), nullable=False)
    session_id = database.Column(database.CHAR(length=48), nullable=True)
    last_use_time = database.Column(database.INTEGER, default=0)


class SubBranch(database.Model):
    __tablename__ = 'subbranch'
    name = database.Column(database.VARCHAR(length=10), primary_key=True)
    city = database.Column(database.VARCHAR(length=10))
    fund = database.Column(database.DECIMAL(20, 2))


class Department(database.Model):
    __tablename__ = 'department'
    department_id = database.Column(database.CHAR(16), primary_key=True)
    department_type = database.Column(database.CHAR(10), nullable=False)
    # manager = database.Column(database.CHAR(length=18), database.ForeignKey('employee.user_id'), nullable=True)
    subbranch = database.Column(database.VARCHAR(length=10), database.ForeignKey(SubBranch.name), primary_key=True)


class Employee(database.Model):
    __tablename__ = 'employee'
    user_id = database.Column(database.CHAR(length=18), primary_key=True)
    type = database.Column(database.INTEGER, nullable=False)
    name = database.Column(database.VARCHAR(length=20), nullable=False)
    phone = database.Column(database.CHAR(length=20))
    address = database.Column(database.VARCHAR(length=100))
    department_id = database.Column(database.CHAR(16), nullable=False)
    subbranch = database.Column(database.VARCHAR(length=10), primary_key=True)
    start_date = database.Column(database.DATE, nullable=False)
    __table_args__ = (
        database.ForeignKeyConstraint((department_id, subbranch), [Department.department_id, Department.subbranch]),
    )


class BankManager(database.Model):
    __tablename__ = 'manager'
    subbranch = database.Column(database.VARCHAR(length=10), database.ForeignKey(SubBranch.name), primary_key=True)
    department_id = database.Column(database.CHAR(16), database.ForeignKey(Department.department_id), primary_key=True)
    user_id = database.Column(database.CHAR(length=18), database.ForeignKey(Employee.user_id))


class Customer(database.Model):
    def __init__(self, js: Optional[dict] = None):
        if js:
            self.update(js)

    def update(self, js: dict):
        self.user_id = js.get('identifier_id')
        self.name = js.get('name')
        self.phone = js.get('phone')
        self.address = js.get('address')
        self.s_name = js.get('s_name')
        self.s_phone = js.get('s_phone')
        self.s_email = js.get('s_email')
        self.s_relation = js.get('s_rel')

    def to_dict(self):
        return {
            'identifier_id': self.user_id,
            'name': self.name,
            'phone': self.phone,
            'address': self.address,
            's_name': self.s_name,
            's_phone': self.s_phone,
            's_email': self.s_email,
            's_rel': self.s_relation
        }

    __tablename__ = 'customer'
    user_id = database.Column(database.CHAR(length=18), primary_key=True)
    name = database.Column(database.VARCHAR(length=20))
    phone = database.Column(database.CHAR(length=20))
    address = database.Column(database.VARCHAR(length=100))
    s_name = database.Column(database.VARCHAR(length=20))
    s_phone = database.Column(database.CHAR(length=20))
    s_email = database.Column(database.CHAR(length=40))
    s_relation = database.Column(database.VARCHAR(length=10))
    employee_id = database.Column(database.CHAR(length=18), database.ForeignKey(Employee.user_id), nullable=True)


class Account(database.Model):
    def __init__(self, account_id, branch, ac_type):
        self.account_id = account_id
        self.sub_branch = branch
        self.type = ac_type
        self.refund = 0
        self.open_date = datetime.datetime.now()
        self.recent_visit = datetime.datetime.now()

    __tablename__ = 'account'
    account_id = database.Column(database.CHAR(length=19), primary_key=True)
    refund = database.Column(database.DECIMAL(20, 2), nullable=False)
    open_date = database.Column(database.DATE, nullable=False)
    sub_branch = database.Column(database.VARCHAR(length=10), database.ForeignKey(SubBranch.name), nullable=False)
    recent_visit = database.Column(database.DATE, nullable=False)
    type = database.Column(database.INTEGER, nullable=False)
    __table_args__ = (
        database.Index('id_acc_acc_tp', account_id, type),
    )


class SavingAccount(database.Model):
    def __init__(self, account_id):
        self.account_id = account_id
        self.rate = 0
        self.finance = 0

    __tablename__ = 'saving_account'
    account_id = database.Column(database.CHAR(length=19), database.ForeignKey(Account.account_id), primary_key=True)
    rate = database.Column(database.DECIMAL(20, 2), nullable=False)
    finance = database.Column(database.CHAR(length=10), nullable=False)


class CheckingAccount(database.Model):
    def __init__(self, account_id):
        self.account_id = account_id
        self.overdraft = 0

    __tablename__ = 'checking_account'
    account_id = database.Column(database.CHAR(length=19), database.ForeignKey(Account.account_id), primary_key=True)
    overdraft = database.Column(database.DECIMAL(20, 2), nullable=False)  # 透支额度


class LoanRecord(database.Model):
    __tablename__ = 'loan_record'
    loan_id = database.Column(database.CHAR(18), primary_key=True)
    subbranch = database.Column(database.VARCHAR(length=10), database.ForeignKey(SubBranch.name), nullable=False)
    total_fund = database.Column(database.DECIMAL(20, 2), nullable=False)
    date = database.Column(database.DATE, nullable=False)

    def __init__(self, subbranch, total_fund):
        self.loan_id = str(uuid.uuid4())[:18]
        self.subbranch = subbranch
        self.total_fund = total_fund
        self.date = datetime.datetime.now()


class PaidRecord(database.Model):
    __tablename__ = 'paid_record'
    id = database.Column(database.INTEGER, primary_key=True)
    fund = database.Column(database.DECIMAL(20, 2), nullable=False)
    date = database.Column(database.DATE, nullable=False)
    loan_id = database.Column(database.CHAR(18), database.ForeignKey(LoanRecord.loan_id), nullable=False)

    def __init__(self, loan_id, fund):
        self.loan_id = loan_id
        self.fund = fund
        self.date = datetime.datetime.now()


class RelationLoanUsr(database.Model):
    __tablename__ = 'relation_loan_usr'
    user_id = database.Column(database.CHAR(length=19), database.ForeignKey(Customer.user_id), primary_key=True)
    loan_id = database.Column(database.CHAR(18), database.ForeignKey(LoanRecord.loan_id), primary_key=True)

    def __init__(self, user_id, loan_id):
        self.user_id = user_id
        self.loan_id = loan_id


class RelationAccountCustomerBranch(database.Model):
    def __init__(self, account_id, customer_id, ac_type, branch_name):
        self.account_id = account_id
        self.customer_id = customer_id
        self.type = ac_type
        self.branch = branch_name

    __tablename__ = 'relation_a_c_b'
    account_id = database.Column(database.CHAR(length=19), primary_key=True)
    customer_id = database.Column(database.CHAR(18), database.ForeignKey(Customer.user_id), nullable=False)
    type = database.Column(database.INTEGER, nullable=False)
    branch = database.Column(database.VARCHAR(length=10), database.ForeignKey(SubBranch.name), nullable=False)
    __table_args__ = (
        database.UniqueConstraint(customer_id, type, branch),
        database.ForeignKeyConstraint((account_id, type), (Account.account_id, Account.type))
    )
