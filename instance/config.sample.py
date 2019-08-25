# Site name. Used in web page title.
# サイトの名前。Webページのタイトルなどに使われる。
YAMI_SITE_NAME = "YAMI"

# Admin name. Written at the bottom of web pages.
# 管理者の名前。ページの下部などに記載される。
YAMI_ADMIN_NAME = "The YAMI Master"

# The number of auctions per page in auction list.
# オークション一覧ページにおける1ページあたりのオークション数
YAMI_NUM_AUCTIONS_PER_PAGE = 20

# The minimum of price step.
# 入札ステップの最小値。
YAMI_PRICE_STEP_MIN = 50

# Whether calculate price step from current price each time.
# If set to False, calculate it from start price.
# 入札ステップを現在価格から都度計算するかどうか。
# False の場合は開始価格から計算する。
YAMI_PRICE_STEP_FROM_CURRENT_PRICE = True

# The rule to calculate price step.
# The following example expresses:
#    200 for from 1000 to  2000
#    400 for from 2000 to  4000
#   1000 for from 4000 to 10000
#
# The keys and values of this dict must be able to be converted to Decimal.
# The keys must contain 1.
# Floating point numbers should not be used because they may generate rounding error.
#
# 入札ステップ計算ルール。
# 以下の例だと、
#   1000以上 2000未満の場合は 200
#   2000以上 4000未満の場合は 400
#   4000以上10000未満の場合は1000
# となる。
# 
# dict のキーと値は Decimal に変換できる必要がある。
# キーには必ず 1 を含む必要がある。
# 丸め誤差が発生するので浮動小数点数を書くべきではない。
YAMI_PRICE_STEP_RULE = {
	1: "0.2",
	2: "0.4",
	4: "1.0",
}

# Automatic duration extension in seconds.
# The remaining duration is less than this value, it is extended to this value.
# 入札時自動延長秒数。
# この時間より残り時間が短かった場合、この時間に延長される。
YAMI_AUTO_EXTENSION = 300


## database configuration ##

MYSQL_CONNECT_KWARGS = {
	"host":     "localhost",
	"port":     3306,
	"user":     "yami",
	"password": "password",
	"database": "db_yami",
}
