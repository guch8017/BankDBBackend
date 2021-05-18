from ext import database


class User(database.Model):
    __tablename__ = 'user'
    user_id = database.Column(database.CHAR(length=18))
    password = database.Column(database.CHAR(length=32))
    session_id = database.Column(database.CHAR(length=32))
    last_use_time = database.Column(database.TIMESTAMP)


class SubBranch(database.Model):
    __tablename__ = 'subbranch'
    name = database.Column(database.VARCHAR(length=10))
    city = database.Column(database.VARCHAR(length=10))
    fund = database.Column(database.DECIMAL(20, 2))


class Customer(database.Model):
    __tablename__ = 'customer'
    user_id = database.Column(database.CHAR(length=18))
    name = database.Column(database.VARCHAR(length=10))
    phone = database.Column(database.CHAR(length=20))


class Account(database.Model):
    __tablename__ = 'account'
    account_id = database.Column(database.CHAR(length=19), primary_key=True)
    refund = database.Column(database.DECIMAL(20, 2), nullable=False)
    open_date = database.Column(database.DATE, nullable=False)
    sub_branch = database.Column(database.VARCHAR(length=10), database.ForeignKey('subbranch.name'), nullable=False)
    recent_visit = database.Column(database.DATE, nullable=False)
    type = database.Column(database.INTEGER, nullable=False)


class SavingAccount(database.Model):
    __tablename__ = 'saving_account'
    account_id = database.Column(database.CHAR(length=19), database.ForeignKey('account.account_id'), primary_key=True)
    rate = database.Column(database.DECIMAL(20, 10), nullable=False)
    finance = database.Column(database.CHAR(length=10), nullable=False)


class CheckingAccount(database.Model):
    __tablename__ = 'checking_account'
    account_id = database.Column(database.CHAR(length=19), database.ForeignKey('account.account_id'), primary_key=True)
    # TODO


class Department(database.Model):
    __tablename__ = 'department'
    department_id = database.Column(database.CHAR(16), primary_key=True)
    department_type = database.Column(database.CHAR(10), nullable=False)
    manager = database.Column(database.CHAR(length=18), database.ForeignKey('employee.user_id'), nullable=True)    # TODO
    subbranch = database.Column(database.VARCHAR(length=10), database.ForeignKey('subbranch.name'), primary_key=True)


class Employee(database.Model):
    __tablename__ = 'employee'
    user_id = database.Column(database.CHAR(length=18), primary_key=True)
    type = database.Column(database.INTEGER, nullable=False)
    name = database.Column(database.VARCHAR(length=20), nullable=False)
    phone = database.Column(database.CHAR(length=20))
    address = database.Column(database.VARCHAR(length=100))
    department_id = database.Column(database.CHAR(16), database.ForeignKey('department.department_id'), nullable=False)
    start_date = database.Column(database.DATE, nullable=False)


class LoanRecord(database.Model):
    __tablename__ = 'loan_record'
    loan_id = database.Column(database.CHAR(18), primary_key=True)
    subbranch = database.Column(database.VARCHAR(length=10), database.ForeignKey('subbranch.name'), nullable=False)
    total_fund = database.Column(database.DECIMAL(20, 2), nullable=False)
    date = database.Column(database.DATE, nullable=False)


class PaidRecord(database.Model):
    __tablename__ = 'paid_record'
    id = database.Column(database.INTEGER, primary_key=True)
    fund = database.Column(database.DECIMAL(20, 2), nullable=False)
    date = database.Column(database.DATE, nullable=False)
    loan_id = database.Column(database.CHAR(18), database.ForeignKey('loan_record.loan_id'), nullable=False)


class RelationEmpAcc(database.Model):
    __tablename__ = 'relation_emp_acc'
    account_id = database.Column(database.CHAR(length=19), database.ForeignKey('account.account_id'), primary_key=True)
    user_id = database.Column(database.CHAR(length=18), database.ForeignKey('customer.user_id'), primary_key=True)


class RelationLoanAcc(database.Model):
    __tablename__ = 'relation_loan_acc'
    account_id = database.Column(database.CHAR(length=19), database.ForeignKey('account.account_id'), primary_key=True)
    loan_id = database.Column(database.CHAR(18), database.ForeignKey('loan_record.loan_id'), primary_key=True)