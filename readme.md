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

Any future time (when you already have the blockchain) use this:
This is the same as above but maybe there are some reindex flags we can leave
off? If you know which flags can be omitted please submit a PR fixing it.

```
export EXTERNALHDD=$HOME/hdd
./omnicored -blocksdir=${EXTERNALHDD}/blocks -datadir=${EXTERNALHDD}/data -debuglogfile=${EXTERNALHDD}/debuglog -walletdir=${EXTERNALHDD}/wallet -rpcuser=mysecureusername -rpcpassword=mysecurepassword -txindex=1 -rpcallowip=127.0.0.1 -dbcache=20480 -disablewallet -server -experimental-btc-balances -reindex -reindex-chainstate
```

### Extract the transactions

Once the blockchain is fully synced (yes you must wait) run the command

```
python omnicore_scraper.py > all_maidsafecoin_txs.json
```
