# Gets all the maidsafecoin transactions from omnicore
# and saves them into a list
# in the file
# all_maidsafecoin_txs_omnicore.json
# and saves all the balances for these addresses in
# all_maidsafecoin_balances_omnicore.json
#
# Usage:
# Make sure omnicore is running, then run
# python omnicore_scraper.py
#
# Notes:
# - Individual transaction json is saved to the directory 'txjson'
#   since it's slow to extract data from the blockchain, so the
#   data is saved locally to speed successive runs up.

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

# load config for parameters specific to this machine
f = open("config.json")
configStr = f.read()
f.close()
config = json.loads(configStr)

# Individual transactions are stored in this directory to
# avoid having to extract them on successive runs. It's relavitely
# slow to extract from the blockchain but fast to read from file.
# As of 2021-07-01 the total size of this directory ended up at 6.6 GB.
txDir = config["txjson"]

# The location of omnicore-cli binary
omnicoreCli = config["omnicorecli"]

# Variable to store the output
txs = []

def runCmd(cmd_arr):
    proc = subprocess.Popen(cmd_arr, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdout, ignore) = proc.communicate()
    return stdout.decode("utf-8")

def fetchAddrTxs(addr):
    print("Fetching %s" % addr)
    addrShort = addr[:8] + "..."
    # get all txs for this addr
    # omnicore-cli getaddresstxids '{"addresses": ["2NDaa1MvFcpc2CAbFvG5g9dDxzrRyDnKnsj"]}'
    addrJson = json.dumps({"addresses": [addr]})
    addrTxsStr = runCmd([omnicoreCli, "getaddresstxids", addrJson])
    addrTxs = json.loads(addrTxsStr)
    for i, txid in enumerate(addrTxs):
        if i % 100 == 0:
            print("Fetching %s tx %s of %s" % (addrShort, (i+1), len(addrTxs)))
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
                txStr = runCmd([omnicoreCli, "omni_gettransaction", txid])
                f = open(txFullFilename, 'w')
                f.write(txStr)
                f.close()
            if txStr[0] != "{":
                #print("Unknown format for tx %s\n%s" % (txid, txStr))
                continue
            # use this tx data to find related txs
            tx = json.loads(txStr)
            propertyid = 0
            isMaid = False
            if tx["type"] == "Crowdsale Purchase": # eg 4ec15360a03d23c069c2fd4a035cfee28af5ddfdd5a6839934dd2629129d477e
                if "purchasedpropertyid" in tx:
                    if tx["purchasedpropertyid"] == MAID_OMNI_ID:
                        isMaid = True
            elif tx["type"] in [
                    "Create Property - Variable", # eg 86f214055a7f4f5057922fd1647e00ef31ab0a3ff15217f8b90e295f051873a7
                    "Create Property - Fixed", # eg e2b6e8bee4ca45197b1a83fc7f4d2b0745620da209aaf79ae96580f40d0fa199
                    "Create Property - Manual", # eg 85a93f535c3dde14996153650c12300b423facfb998d377f42972fe13da362f2
                    "Simple Send", # eg cfff3c800655073452c6d590bc7685250dc5bd94067a69b2d5264a0232bba390
                    "Grant Property Tokens", # eg 0c8c22ee5cd69649ff36c0396bb9ce951425614a32129d8d54c0144895ef4e7a
                    "Revoke Property Tokens", # eg 56e3274f90d7a6acbffe85df723a23f82baa5b7317b51f43b1c11be8392f01da
                    "DEx Accept Offer", # eg 847452a7b832a80f61178f85a7258668d254c8ee8bf33c269748733bd85a2e01
                    "DEx Sell Offer", # eg 8ddc1b28c6cdc58737a054a6516ad5d683f1371f863a32e2abdcfcd99fc682c9
                    "Change Issuer Address", # eg 537a15666c215485eade88853b6a4fb10c4a80ac14b78f7fc5cc283d05d7a9b8
                    "Close Crowdsale", # eg b8864525a2eef4f76a58f33a4af50dc24461445e1a420e21bcc99a1901740e79
                ]:
                if "propertyid" in tx:
                    if tx["propertyid"] == MAID_OMNI_ID:
                        isMaid = True
            elif tx["type"] in [
                    "MetaDEx trade", # eg 70e8050d156161713e399250fef25ff6950fe4e9195427dfde3164a1bcd0fb97
                    "MetaDEx cancel-price", # eg ec1b540c9253292795ef9ad6b4ea19ad128f67ff98b28ac0f7748e65a0fd2e4d
                ]:
                if "propertyiddesired" in tx:
                    if tx["propertyiddesired"] == MAID_OMNI_ID:
                        isMaid = True
                if "propertyidforsale" in tx:
                    if tx["propertyidforsale"] == MAID_OMNI_ID:
                        isMaid = True
            elif tx["type"] == "Send All": # eg 0dc6720bea96a8abc8912ea016afcdf3477ac3574d4af33b3b3a8f15f579c90c
                if "subsends" in tx:
                    for subsend in tx["subsends"]:
                        if subsend["propertyid"] == MAID_OMNI_ID:
                            isMaid = True
            elif tx["type"] == "DEx Purchase": # eg 6198083e28a56e5b73fd27f1243357107954fe3b39c9d1b886ff3e8506b399d7
                if "purchases" in tx:
                    for purchase in tx["purchases"]:
                        if purchase["propertyid"] == MAID_OMNI_ID:
                            isMaid = True
            elif tx["type"] == "MetaDEx cancel-ecosystem": # eg e23247a07beb8e6725719af1b5a44589aa87a0ac2bd120d3652e0df9cca3f26f
                pass
            else:
                print("Unknown tx type: %s %s" % (tx["type"], tx["txid"]))
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

def fetchBalance(addr):
    addrBalanceStr = runCmd([omnicoreCli, "omni_getbalance", addr, str(MAID_OMNI_ID)])
    if len(addrBalanceStr) == 0 or addrBalanceStr[0] != "{":
        print("Unknown addr balance format: %s %s" % (addr, addrBalanceStr))
        return {}
    # parse balance json
    try:
        addrBalance = json.loads(addrBalanceStr)
    except:
        print("Unknown addr balance json: %s %s" % (addr, addrBalanceStr))
        return {}
    return addrBalance

def fetchCurrentBlockHeight():
    infoStr = runCmd([omnicoreCli, "omni_getinfo"])
    if len(infoStr) == 0 or infoStr[0] != "{":
        print("Unknown omni_getinfo format: %s" % infoStr)
        return -1
    info = json.loads(infoStr)
    if "block" not in info:
        print("No block info in omni_getinfo: %s" % infoStr)
        return -1
    return info["block"]

while len(remainingAddrs) > 0:
    fetchAddrTxs(remainingAddrs.pop())
    remainingAddrs = allAddrs.difference(fetchedAddrs)
    print("allAddrs: %s fetchedAddrs: %s remainingAddrs: %s" % (len(allAddrs), len(fetchedAddrs), len(remainingAddrs)))

# sort txs by block then by position in block,
# which is necessary for dex trades to be processed correctly, see
# https://github.com/OmniLayer/spec/blob/fc37541641ad45959cdbb71a6985fcd99dae445c/OmniSpecification.adoc#723-sell-omni-protocol-coins-for-another-omni-protocol-currency
txs = sorted(txs, key=lambda t: (t["block"], t["positioninblock"]))

# get address balances
balances = {}
print("Getting current balances for all maidsafecoin addresses")
startBlockHeight = fetchCurrentBlockHeight()
print("Currently at block height %s" % startBlockHeight)
for tx in txs:
    if "sendingaddress" in tx:
        fromAddr = tx["sendingaddress"]
        if fromAddr not in balances:
            balance = fetchBalance(fromAddr)
            balances[fromAddr] = balance
    if "referenceaddress" in tx:
        toAddr = tx["referenceaddress"]
        if toAddr not in balances:
            balance = fetchBalance(toAddr)
            balances[toAddr] = balance
print("Checking if any new data has arrived since we started getting balances")
endBlockHeight = fetchCurrentBlockHeight()
print("Currently at block height %s" % endBlockHeight)
# if new data has arrived since the start then alert that the results might be incorrect
if endBlockHeight != startBlockHeight:
    print("ERROR: New block(s) arrived during processing of balances, results will be incorrect if there are maidsafecoin txs after block %s" % startBlockHeight)

# write the list of txs to file
txFilename = "all_maidsafecoin_txs_omnicore.json"
txContent = json.dumps(txs, indent=2)
f = open(txFilename, 'w')
f.write(txContent)
f.close()
print("Wrote file %s" % txFilename)

# write the list of balances to file
balancesFilename = "all_maidsafecoin_balances_omnicore.json"
balancesContent = json.dumps(balances, indent=2)
f = open(balancesFilename, 'w')
f.write(balancesContent)
f.close()
print("Wrote file %s" % balancesFilename)
