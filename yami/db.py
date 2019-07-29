from flask import current_app, g
from flaskext.mysql import MySQL

mysql = MySQL()

def init_db(app):
	mysql.init_app(app)

def get_db():
	if "db" not in g:
		g.db = mysql.get_db()
	return g.db

def close_db():
	db = g.pop("db", None)
	if db is not None:
		db.close()
