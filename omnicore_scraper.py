# Gets all the maidsafecoin transactions from omnicore
# and saves them into a list
# which is printed to stdout.
#
# Usage:
# Make sure omnicore is running, then run
# python omnicore_scraper.py > all_maid_txs.json
#
# Notes:
# 1. Progress feedback is printed to stderr while the script runs.
# 2. Individual transaction json is saved to the directory 'txjson'
#    since it's slow to extract data from the blockchain, so the
#    data is saved locally to speed successive runs up.

import collections
import json
import os
import subprocess
import sys

firstAddr = "1ARjWDkZ7kT9fwjPrjcQyvbXDkEySzKHwu"

MAID_OMNI_ID = 3

# Keep track of work to avoid duplicate work
allAddrs = set()
fetchedAddrs = set()
allAddrs.add(firstAddr)
remainingAddrs = allAddrs.difference(fetchedAddrs)
txids = []

# Individual transactions are stored in this directory to
# avoid having to extract them on successive runs. It's relavitely
# slow to extract from the blockchain but fast to read from file.
# As of 2021-07-01 the total size of this directory ended up at 6.6 GB.
txDir = "txjson"

# Variable to store the output
txs = []

def stderr(msg):
    print(msg, file=sys.stderr)

def runCmd(cmd_arr):
    proc = subprocess.Popen(cmd_arr, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdout, ignore) = proc.communicate()
    return stdout.decode("utf-8")

def fetchAddrTxs(addr):
    stderr("Fetching %s" % addr)
    addrShort = addr[:8] + "..."
    # get all txs for this addr
    # omnicore-cli getaddresstxids '{"addresses": ["2NDaa1MvFcpc2CAbFvG5g9dDxzrRyDnKnsj"]}'
    addrJson = json.dumps({"addresses": [addr]})
    addrTxsStr = runCmd(["./omnicore-cli", "getaddresstxids", addrJson])
    addrTxs = json.loads(addrTxsStr)
    for i, txid in enumerate(addrTxs):
        if i % 100 == 0:
            stderr("Fetching %s tx %s of %s" % (addrShort, (i+1), len(addrTxs)))
        # save every tx
        # omnicore-cli "omni_gettransaction" "1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d"
        if txid not in txids:
            # try to read from file
            txFilename = txid + ".json"
            txFullFilename = os.path.join(txDir, txFilename)
            txStr = "txStr has not been read yet"
            try:
                f = open(txFullFilename)
                txStr = f.read()
                f.close()
            except FileNotFoundError:
                # if not in file, read from blockchain and store in file
                txStr = runCmd(["./omnicore-cli", "omni_gettransaction", txid])
                f = open(txFullFilename, 'w')
                f.write(txStr)
                f.close()
            if txStr[0] != "{":
                #stderr("Unknown format for tx %s\n%s" % (txid, txStr))
                continue
            # use this tx data to find related txs
            tx = json.loads(txStr)
            propertyid = 0
            isMaid = False
            if "purchasedpropertyid" in tx:
                if tx["purchasedpropertyid"] == MAID_OMNI_ID:
                    isMaid = True
            if "propertyid" in tx:
                if tx["propertyid"] == MAID_OMNI_ID:
                    isMaid = True
            if not isMaid:
                continue
            del tx["confirmations"]
            del tx["ismine"]
            txs.append(tx)
            txids.append(txid)
            # for every tx add any new addrs to allAddrs
            if "sendingaddress" in tx:
                fromAddr = tx["sendingaddress"]
                if fromAddr not in fetchedAddrs:
                    if fromAddr not in allAddrs:
                        allAddrs.add(fromAddr)
            if "referenceaddress" in tx:
                toAddr = tx["referenceaddress"]
                if toAddr not in fetchedAddrs:
                    if toAddr not in allAddrs:
                        allAddrs.add(toAddr)
    fetchedAddrs.add(addr)

while len(remainingAddrs) > 0:
    fetchAddrTxs(remainingAddrs.pop())
    remainingAddrs = allAddrs.difference(fetchedAddrs)
    stderr("allAddrs: %s fetchedAddrs: %s remainingAddrs: %s" % (len(allAddrs), len(fetchedAddrs), len(remainingAddrs)))

# sort txs by time, then by txid
txs = sorted(txs, key=lambda t: (t["blocktime"], int(t["txid"][:8],16)))
# print out the list of txs
print(json.dumps(txs, indent=2))
