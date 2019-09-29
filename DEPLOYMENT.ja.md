# 構築手順

## アプリケーションサーバの設定

```
root# python3 -m pip -r requirements.txt
```

```
user$ cd instance
user$ cp config.sample.py config.py
user$ vi config.py # edit configuration
```

結合テストを行う場合は

```
user$ cp testconfig.sample.py testconfig.py
user$ vi testconfig.py # edit configuration
```

## DB の設定

### 新規に構築する場合

DB サーバで

```
root# mysql
mysql> CREATE USER yami;
mysql> CREATE DATABASE db_yami;
mysql> GRANT ALL ON db_yami.* TO yami;
mysql> USE db_yami
mysql> source schema.mysql
```

結合テストを行う場合は

```
mysql> CREATE DATABASE test_yami;
mysql> GRANT ALL ON test_yami.* TO yami;
```

### アップグレードの場合

DB サーバで

```
root# mysql db_yami < upgrade.mysql
```

## 起動

テスト（ユニットテスト/結合テスト）

```
user$ python3 -m pytest .
```

Flask 組み込みの開発サーバで起動する場合

```
user$ FLASK_APP=yami FLASK_ENV=development flask run
```

gunicorn 環境下で起動する場合

```
user$ gunicorn "yami:create_app()"
```

本番稼働させる場合は、 https://flask.palletsprojects.com/en/1.0.x/deploying/ を参考にしてください。

## cron job

オークションの時間切れによる終了の処理を行うために `check_expiration.py` を定期的に実行する必要があります。

`check_expiration.py` を実行しなくてもオークションは終了しているように見えるように作ってありますが、時間切れの場合の終了時に行われる処理は `check_expiration.py` から実行されるため、中途半端な状態になります。
