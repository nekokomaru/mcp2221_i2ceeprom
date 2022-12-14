# I2C EEPROM Writer/Reader for MCP2221A

### 概要
Hid デバイスである MCP2221A の I2C 通信機能を使い、I2C EEPROM にデータを書き込む、及びデータを読み出す python スクリプト

### 動作環境
* python 3.10 以上
* python ライブラリの hidapi (https://pypi.org/project/hidapi/)

作者が動作確認をしたソフトウェア環境は以下の通り

* windows 10
* python 3.11.1
* hidapi 0.12.0.post2

ハードウェア環境は以下の通り

* MCP2221A (https://www.microchip.com/en-us/product/MCP2221A) revision A612
* ATMEL 24C02 (2kbits i2c eeprom)
* 自作 MCP2221A 基板 (https://nekokohouse.sakura.ne.jp/accessory/#mcp2221a)

### 使用前の準備
* python 3.10 以上をインストールし、合わせて `hidapi` ライブラリもインストールしておく
```bash
pip install hidapi
```
* MCP2221A の I2C バスに eeprom を接続し、MCP2221A を USB 接続する

### 使用方法
* 引数なしで実行すると、接続されている MCP2221A の一覧を表示する
```bash
python mcp2221_i2ceeprom.py  # MCP2221A の一覧が表示される
```
* `-h`, `--help` オプションを指定して実行すると使い方が表示される
```bash
python mcp2221_i2ceeprom.py -h   # ヘルプが表示される
```
* `--write` と `--filename` オプションを使って、eeprom にバイナリファイルの内容を書き込むことができる
```bash
python mcp2221_i2ceeprom.py --write --filename input.bin  # input.bin の内容を eeprom に書き込む
```
* `--read` と `--filename` オプションを使って、eeprom の内容をバイナリファイルに書き出すことができる
```bash
python mcp2221_i2ceeprom.py --read --filename output.bin  # eeprom の内容を読み出して output.bin に書き込む
```
* `--romsize` オプションを使うと、ターゲットとなる eeprom のサイズ(bit)を指定できる。**デフォルト値(`'2k'`)以外の時は指定すること**
```bash
python mcp2221_i2ceeprom.py --write --romsize '64k' --filename input.bin  # 64kビットサイズの eeprom に input.bin の内容を書き込む
```
* `--slave` オプションを使うと、ターゲットとなる eeprom のスレーブアドレス(7bit)を指定できる
```bash
python mcp2221_i2ceeprom.py --write --romsize '64k' --slave 0x52 --filename input.bin  # スレーブアドレス 0x52、64kビットサイズの eeprom に input.bin の内容を書き込む
```
* `--no` や `--name` オプションを使うと、使用する MCP2221A を指定できる
```bash
python mcp2221_i2ceeprom.py --write --romsize '64k' --slave 0x52 --no 1 --filename input.bin   # 一覧表示される MCP2221A のうち No.1 のデバイスにつながっている スレーブアドレス 0x52、64kビットサイズの eeprom に input.bin の内容を書き込む
```


ヘルプを参考にその他のオプションを使用すると、細かい動作を指定できる

### 免責事項
本ソフトウェアの動作は保証しない。著作者は一切の責任を追わない

### ライセンス
MIT ライセンスである。詳しくは LICENSE を参照のこと

### 著作者
Yachiyo https://nekokohouse.sakura.ne.jp/
