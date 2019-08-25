YAMI_SITE_NAME = "YAMI"
YAMI_ADMIN_NAME = "The YAMI Master"
YAMI_NUM_AUCTIONS_PER_PAGE = 20
YAMI_PRICE_STEP_MIN = 50
YAMI_PRICE_STEP_FROM_CURRENT_PRICE = True
YAMI_PRICE_STEP_RULE = {
	1: "0.2",
	2: "0.4",
	4: "1.0",
}
YAMI_AUTO_EXTENSION = 300

MYSQL_CONNECT_KWARGS = {
	"host":     "localhost",
	"port":     3306,
	"user":     "yami",
	"password": "password",
	"database": "db_yami",
}
