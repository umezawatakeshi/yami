# YAMI - Yet-another Auction Manager for Intranet

**YAMI** は組織内ネットワーク（つまりイントラネット）でオークションを開催するためのシンプルな Web アプリケーションです。

## やることとやらないこと

### やること

- オークションの出品と入札の調停

### やらないこと

- ユーザー管理

## 必要なもの

- MySQL 5.7
- Python 3
- 以下の Python パッケージ（requirements.txt を参照）
  - Flask >= 1.0
  - PyMySQL
  - tzlocal
  - pytz
  - pytest （テストを行う場合）

## 構築手順

[DEPLOYMENT.ja.md](DEPLOYMENT.ja.md) を参照。

## 著作権表示とライセンス

Copyright &copy; 2019 UMEZAWA Takeshi

YAMI は GNU Affero General Public License version 3 (GNU AGPL3) の下でライセンスされます。
詳しくは [LICENSE](./LICENSE) ファイルを参照してください。
