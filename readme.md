# omni_tx_parser

Parses all maidsafecoin transactions into a list sorted by date.

# Usage

### Install omnicore

Download from [https://github.com/OmniLayer/omnicore/releases/latest](https://github.com/OmniLayer/omnicore/releases/latest)

### Run omnicore

For the first time use this:

```
export EXTERNALHDD=$HOME/hdd
./omnicored -blocksdir=${EXTERNALHDD}/blocks -datadir=${EXTERNALHDD}/data -debuglogfile=${EXTERNALHDD}/debuglog -walletdir=${EXTERNALHDD}/wallet -rpcuser=mysecureusername -rpcpassword=mysecurepassword -txindex=1 -rpcallowip=127.0.0.1 -dbcache=20480 -disablewallet -server -experimental-btc-balances -reindex -reindex-chainstate
```

Any future time (when you already have the blockchain) use this: (note the
lack of -reindex and -reindex-chainstate flags)

```
export EXTERNALHDD=$HOME/hdd
./omnicored -blocksdir=${EXTERNALHDD}/blocks -datadir=${EXTERNALHDD}/data -debuglogfile=${EXTERNALHDD}/debuglog -walletdir=${EXTERNALHDD}/wallet -rpcuser=mysecureusername -rpcpassword=mysecurepassword -txindex=1 -rpcallowip=127.0.0.1 -dbcache=20480 -disablewallet -server -experimental-btc-balances
```

### Extract the transactions

Edit config.json to suit your needs.

`txjson` value is the absolute path to the directory to store each
transaction data file.

`omnicorecli` value is the absolute path to the omnicore-cli
binary

Once the blockchain is fully synced (yes you must wait) run the command

```
python omnicore_scraper.py > all_maidsafecoin_txs.json
```
