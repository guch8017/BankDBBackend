"""
贷款相关API
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from random import randint
from threading import Lock
from data_type import *
from ext import database
from api.__util import generate_error, pre_process, parse_sqlerror