from flask import current_app, g
import pymysql

def init_db(app):
	app.teardown_appcontext(close_db)
	app.config["MYSQL_PYMYSQL_KWARGS"]["charset"] = "utf8mb4"

def get_db():
	if "db" not in g:
		g.db = pymysql.connect(**current_app.config["MYSQL_PYMYSQL_KWARGS"])
	return g.db

def close_db(e=None):
	db = g.pop("db", None)
	if db is not None:
		db.close()
