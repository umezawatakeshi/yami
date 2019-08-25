import pytest
import pymysql
import re
from instance.testconfig import MYSQL_CONNECT_KWARGS

@pytest.fixture
def initdb():
	conn = pymysql.connect(**MYSQL_CONNECT_KWARGS)
	with conn.cursor() as cur:
		execute_files(cur, ["tests/clean.mysql", "schema.mysql"])
	conn.commit()
	yield conn
	conn.close()

def execute_files(cur, filenames):
	for filename in filenames:
		with open(filename, "rt") as f:
			for stmt in f.read().split(";"):
				if re.fullmatch("[ \t\n\r]*", stmt):
					# workaround for 'Query was empty'
					continue
				cur.execute(stmt)
