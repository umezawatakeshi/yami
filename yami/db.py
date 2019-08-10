from flask import current_app, g
import pymysql

def init_db(app):
	app.teardown_appcontext(close_db)
	app.config["MYSQL_CONNECT_KWARGS"]["charset"] = "utf8mb4"

def get_db():
	if "db" not in g:
		g.db = pymysql.connect(**current_app.config["MYSQL_CONNECT_KWARGS"])
	return g.db

def get_cursor():
	return get_db().cursor()

def get_dict_cursor():
	return get_db().cursor(pymysql.cursors.DictCursor)

def commit():
	if "db" in g:
		g.db.commit()

def rollback():
	if "db" in g:
		g.db.rollback()

def close_db(e=None):
	db = g.pop("db", None)
	if db is not None:
		db.close()
