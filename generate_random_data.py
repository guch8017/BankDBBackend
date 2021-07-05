from faker import Faker
import config
import pymysql
from random import randint

NUM_DATA = 50  # 指定数据大小

department_table = (
    (1, '办公室'),
    (2, '人力资源管理部'),
    (3, '监察室'),
    (4, '审计部'),
    (5, '工会办公室'),
    (6, '物业管理服务中心')
)

branch = """INSERT INTO bank.subbranch (name, city, fund) VALUES ('三里庵支行', '合肥', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('亳州路储蓄所', '合肥', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('嘉山路分理处', '合肥', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('广东省分行营业部', '广州', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('广州东山支行营业室', '广州', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('广州天河支行华南农业', '广州', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('广州天河支行暨南大学', '广州', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('广州天河支行濂泉路支', '广州', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('广州天河支行营业室', '广州', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('广州白云支行先烈东路', '广州', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('望江西路分理处', '合肥', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('滨水城分理处', '合肥', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('蒙城北路分理处', '合肥', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('阜阳北路支行', '合肥', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('颐和花园分理处', '合肥', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('高新开发区支行', '合肥', 0.00);
INSERT INTO bank.subbranch (name, city, fund) VALUES ('龙岗支行', '合肥', 0.00);"""

faker_instance = Faker(locale='zh_CN')

conn = pymysql.connect(user=config.DB_USER, passwd=config.DB_PASSWORD, db=config.DB_NAME, host=config.DB_HOST,
                       port=config.DB_PORT)
cursor = conn.cursor()
# 清空数据表
cursor.execute('DELETE FROM subbranch;')
cursor.execute('DELETE FROM employee;')
cursor.execute('DELETE FROM department;')
cursor.execute('DELETE FROM customer;')
conn.commit()
# 添加支行
for l in branch.split(';'):
    if l:
        cursor.execute(l)
# conn.commit()
# 提取所有支行信息
cursor.execute('SELECT name, city FROM subbranch;')
branches = cursor.fetchall()

# 添加所有部门
for branch_name, _ in branches:
    for dp_id, dp_type in department_table:
        cursor.execute('INSERT INTO bank.department (department_id, department_type, subbranch) VALUES (%s, %s, %s)',
                       (dp_id, dp_type, branch_name))
conn.commit()
# 随机生成员工数据
for _ in range(NUM_DATA):
    target_depart = randint(1, len(department_table))
    target_branch = branches[randint(0, len(branches) - 1)][0]
    cursor.execute(
        'INSERT INTO bank.employee (user_id, type, name, phone, address, department_id, start_date, subbranch) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
        (faker_instance.ssn(min_age=18, max_age=100), 0, faker_instance.name(), faker_instance.phone_number(),
         faker_instance.address(), target_depart, '2021-05-01', target_branch))
# 随机生成客户数据
for _ in range(NUM_DATA):
    cursor.execute(
        'INSERT INTO bank.customer (user_id, name, phone, address, s_name, s_phone, s_email, s_relation, create_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (faker_instance.ssn(min_age=18, max_age=100), faker_instance.name(), faker_instance.phone_number(),
         faker_instance.address(), faker_instance.name(), faker_instance.phone_number(), faker_instance.email(), '测试关系',
         str(randint(2018, 2021)).zfill(4) + str(randint(1, 12)).zfill(2)))
conn.commit()
