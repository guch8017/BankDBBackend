from dbutils.pooled_db import PooledDB
import pymysql
import config

pool = PooledDB(pymysql, 5, host=config.DB_HOST, port=config.DB_PORT, user=config.DB_USER, passwd=config.DB_PASSWORD)
