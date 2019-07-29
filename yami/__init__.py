#
# YAMI - Yet-another Auction Manager for Intranet
# 
# Copyright (C) 2019  UMEZAWA Takeshi
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from flask import Flask

def create_app(test_config=None):
	app = Flask(__name__, instance_relative_config = True)
	app.config.from_pyfile("config.py")
	app.config["MYSQL_DATABASE_CHARSET"] = "utf8mb4"

	from . import db
	db.init_db(app)

	from . import yami
	app.register_blueprint(yami.bp)

	return app
