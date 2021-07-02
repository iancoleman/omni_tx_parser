# Old script that will fetch from omniexplorer.info
# No longer in use
# Very slow
# Incomplete (eg does not get MetaDEx trades)
# Cannot be trusted the way a local copy of omnicore can

import json
import math
import os
import requests
import sys
import time

rateLimitSeconds = 15
# Error returned is:
# status code 400
# Rate Limit Reached.
# Please limit consecutive requests to no more than 5 every 60s.
# Repetitive abuse will be banned

firstAddr = "1ARjWDkZ7kT9fwjPrjcQyvbXDkEySzKHwu"

#addrUrl = "https://api.omniexplorer.info/v1/address/addr/details/"
addrUrl = "https://api.omniexplorer.info/v1/transaction/address"

addrDir = "addrs"

os.makedirs(addrDir, exist_ok=True)

MAID = 3

txsPerPage = 10

headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "user-agent": "scraper",
}

savedTxs = {}

class AddrTracker:

    def __init__(self):
        self.addrs = []
        self.metadata = {}
        self.fetched = []

    # adds an addr to the list for fetching
    # and keeps metadata for the latest tx time of each addr
    def add(self, addr, txtime):
        # no need to add an already fetched addr
        if addr in self.fetched:
            return
        if addr in self.addrs:
            # if txtime is more recent,
            # update time to latest
            if txtime > self.metadata[addr]["time"]:
                self.metadata[addr]["time"] = txtime
        else:
            self.addrs.append(addr)
            self.metadata[addr] = {}
            self.metadata[addr]["time"] = txtime

    # moves an address from to fetch to fetched
    def remove(self, addr):
        # remove from addrs
        self.addrs.remove(addr)
        # add to fetched
        self.fetched.append(addr)

    def setBalance(self, addr, balance):
        if addr not in self.metadata:
            self.metadata[addr] = {}
        self.metadata[addr]["balance"] = balance

    def removeAddrsWithZeroBalance(self):
        for addr in self.metadata:
            if addr not in self.addrs:
                continue
            if "balance" not in self.metadata[addr]:
                continue
            if self.metadata[addr]["balance"] == 0:
                self.remove(addr)

    # gets the next address most likely to have updated txs
    # TODO consider improving efficiency of this
    # TODO firstly fetch any addrs in a tx which has only one of two addrs
    def next(self):
        latestAddr = None
        latestTime = 0
        for addr in self.addrs:
            if self.metadata[addr]["time"] > latestTime:
                latestAddr = addr
                latestTime = self.metadata[addr]["time"]
        return latestAddr, latestTime

    def isFetched(self, addr):
        return addr in self.fetched

    def lenToFetch(self):
        return len(self.addrs)

def loadAllSavedTxs():
    print("Loading already saved txs")
    for root, dirs, rootfiles in os.walk(addrDir):
        for addr in dirs:
            txCount = 0
            balance = 0
            srcDir = os.path.join(root, addr)
            files = os.listdir(srcDir)
            for filename in files:
                src = os.path.join(srcDir, filename)
                if not src.endswith(".json"):
                    print("Not a json file: %s" % src)
                    continue
                f = open(src)
                c = f.read()
                f.close()
                j = json.loads(c)
                if "transactions" not in j:
                    continue
                if len(j["transactions"]) == 0:
                    continue
                if "txcount" not in j:
                    continue
                if "current_page" not in j:
                    continue
                txCount = txCount + len(j["transactions"])
                totalTxs = j["txcount"]
                page = j["current_page"]
                # store rolling tally of txCount
                if addr not in savedTxs:
                    savedTxs[addr] = {}
                    savedTxs[addr]["existing_indexes"] = set()
                    savedTxs[addr]["missing_indexes"] = set(range(0,totalTxs))
                # store for fetching in the future if it's a MAID address
                for tx in j["transactions"]:
                    isMaid = False
                    if "propertyid" in tx:
                        if tx["propertyid"] == MAID:
                            isMaid = True
                    if "purchasedpropertyid" in tx:
                        if tx["purchasedpropertyid"] == MAID:
                            isMaid = True
                    if not isMaid:
                        continue
                    # keep track of latest transaction time
                    txTime = tx["blocktime"]
                    # keep track of balances
                    amount = 0
                    if "amount" in tx:
                        amount = float(tx["amount"])
                    if "referenceaddress" in tx:
                        addrTracker.add(tx["referenceaddress"], txTime)
                        if tx["referenceaddress"] == addr:
                            balance = balance + amount
                    if "sendingaddress" in tx:
                        addrTracker.add(tx["sendingaddress"], txTime)
                        if tx["sendingaddress"] == addr:
                            balance = balance - amount
                indexes = getIndexesFromStart(totalTxs, page)
                savedTxs[addr]["existing_indexes"].update(indexes)
                savedTxs[addr]["missing_indexes"].difference_update(indexes)
            addrTracker.setBalance(addr, balance)
    # tidy up addrs we don't need to fetch
    beforeLen = addrTracker.lenToFetch()
    addrTracker.removeAddrsWithZeroBalance()
    afterLen = addrTracker.lenToFetch()
    # report stats
    print("Addrs before tidy: %s, after tidy: %s" % (beforeLen, afterLen))
    print("Will fetch at least %s addrs" % addrTracker.lenToFetch())

def fetch(addr, txPage):
    print("Fetching %s txPage %s" % (addr, txPage), end=" ")
    # page 0 and page 1 are identical, so internally we use page 0 to N but
    # for the api we use pages 1 to N+1
    payload = {
        "addr": addr,
        "page": txPage,
    }
    try:
        r = requests.post(addrUrl, data=payload)
    except:
        msg = "Unknown error fetching %s txPage"
        e = sys.exc_info()[0]
        params = (addr)
        print("", flush=True)
        print(msg % params)
        time.sleep(90)
        return fetch(addr, txPage)
    if r.status_code != 200:
        msg = "Error fetching %s txPage %s status code %s"
        params = (addr, txPage, r.status_code)
        print(msg % params)
        print(r.text)
        print("", flush=True)
        time.sleep(90)
        return fetch(addr, txPage)
    j = json.loads(r.text)
    if "transactions" not in j:
        print("PROBLEM: no transactions for %s page %s" % (addr, txPage))
        return
    if len(j["transactions"]) == 0:
        print("PROBLEM: zero transactions for %s page %s" % (addr, txPage))
        return
    firstTx = j["transactions"][0]
    if "txid" not in firstTx:
        print("PROBLEM: no first txid for %s page %s" % (addr, txPage))
        return
    firstTxId = firstTx["txid"]
    dstDir = os.path.join(addrDir, addr)
    dst = os.path.join(dstDir, "%s.json" % firstTxId)
    os.makedirs(dstDir, exist_ok=True)
    f = open(dst, 'w')
    f.write(r.text)
    f.close()
    print("of %s total %s txs" % (j["pages"], j["txcount"]), flush=True)
    print("Saved %s" % dst)
    time.sleep(rateLimitSeconds)
    return r.text, j

def fetchAllAddr(addr):
    if addrTracker.isFetched(addr):
        return
    # record that we've fetched this so don't fetch it all over again
    addrTracker.remove(addr)
    # start with fetching the youngest txs up to our current youngest tx
    firstPageIndex = 1
    t, j = fetch(addr, firstPageIndex)
    findSubAddrs(j)
    if "txcount" not in j:
        print("Expected txcount key in j, but did not find")
        return
    totalTxs = j["txcount"]
    thisFetchTxIndexes = getIndexesFromStart(totalTxs, firstPageIndex)
    # find which pages we need to fetch
    pagesToFetch = set()
    if addr in savedTxs:
        for missingIndex in savedTxs[addr]["missing_indexes"]:
            # ignore missing indexes if we already got it in this fetch
            if missingIndex in thisFetchTxIndexes:
                continue
            page = getPageForIndexFromStart(totalTxs, missingIndex)
            if page != firstPageIndex:
                pagesToFetch.add(page)
    else:
        pagesToFetch = set(range(firstPageIndex + 1, j["pages"] + 1))
    # fetch missing pages
    for page in pagesToFetch:
        t, j = fetch(addr, page)
        findSubAddrs(j)

def getPageForIndexFromStart(totalTxs, txIndexFromStart):
    # pages start at index 1
    # page 0 does exist but is a duplicate of page 1
    if txIndexFromStart >= totalTxs:
        print("Error, index is greater than totalTxs")
        return
    if totalTxs <= txsPerPage:
        return 1
    totalPages = math.ceil(totalTxs / txsPerPage)
    firstIndex = totalTxs - 1
    distanceFromFirstIndex = firstIndex - txIndexFromStart
    page = math.floor(distanceFromFirstIndex / txsPerPage)
    return page + 1

assert(getPageForIndexFromStart(1, 0) == 1)
assert(getPageForIndexFromStart(9, 0) == 1)
assert(getPageForIndexFromStart(9, 8) == 1)
assert(getPageForIndexFromStart(10, 9) == 1)
assert(getPageForIndexFromStart(11, 0) == 2)
assert(getPageForIndexFromStart(11, 1) == 1)
assert(getPageForIndexFromStart(11, 9) == 1)
assert(getPageForIndexFromStart(11, 10) == 1)
assert(getPageForIndexFromStart(20, 0) == 2)
assert(getPageForIndexFromStart(20, 9) == 2)
assert(getPageForIndexFromStart(20, 10) == 1)
assert(getPageForIndexFromStart(20, 19) == 1)
assert(getPageForIndexFromStart(21, 0) == 3)
assert(getPageForIndexFromStart(21, 1) == 2)
assert(getPageForIndexFromStart(21, 10) == 2)
assert(getPageForIndexFromStart(21, 11) == 1)
assert(getPageForIndexFromStart(21, 20) == 1)

def getIndexesFromStart(totalTxs, page):
    indexes = []
    if totalTxs <= 0:
        return indexes
    firstIndex = totalTxs - 1
    firstIndexOfPage = firstIndex - 10*(page-1)
    for i in range(firstIndexOfPage, firstIndexOfPage - txsPerPage, -1):
        if i >= 0:
            indexes.append(i)
    return indexes

assert(getIndexesFromStart(0, 1) == [])
assert(getIndexesFromStart(1, 1) == [0])
assert(getIndexesFromStart(2, 1) == [1, 0])
assert(getIndexesFromStart(10, 1) == [9, 8, 7, 6, 5, 4, 3, 2, 1, 0])
assert(getIndexesFromStart(20, 1) == [19, 18, 17, 16, 15, 14, 13, 12, 11, 10])
assert(getIndexesFromStart(19, 1) == [18, 17, 16, 15, 14, 13, 12, 11, 10, 9])
assert(getIndexesFromStart(19, 2) == [8, 7, 6, 5, 4, 3, 2, 1, 0])
assert(getIndexesFromStart(19, 3) == [])

def countSavedTxs(addr):
    # some files may contain the same tx twice
    # so we need to filter for unique txs when counting
    uniqueTxs = {}
    txCount = 0
    srcDir = os.path.join(addrDir, addr)
    files = os.listdir(srcDir)
    for filename in files:
        src = os.path.join(srcDir, filename)
        if not src.endswith(".json"):
            print("Not a json file: %s" % src)
            continue
        f = open(src)
        c = f.read()
        f.close()
        j = json.loads(c)
        if "transactions" not in j:
            continue
        if len(j["transactions"]) == 0:
            continue
        for tx in j["transactions"]:
            txid = tx["txid"]
            if txid in uniqueTxs:
                continue
            txCount = txCount + 1
            uniqueTxs[txid] = True
    return txCount

def findSubAddrs(j):
    if "transactions" not in j:
        return
    for t in j["transactions"]:
        txTime = t["blocktime"]
        isMaid = False
        if "propertyid" in t:
            if t["propertyid"] == MAID:
                isMaid = True
        if "purchasedpropertyid" in t:
            if t["purchasedpropertyid"] == MAID:
                isMaid = True
        if isMaid:
            if "sendingaddress" in t:
                a = t["sendingaddress"]
                addrTracker.add(a, txTime)
            if "referenceaddress" in t:
                b = t["referenceaddress"]
                addrTracker.add(b, txTime)

addrTracker = AddrTracker()
addrTracker.add(firstAddr, 0)
loadAllSavedTxs()
while addrTracker.lenToFetch() > 0:
    addr, latestTime = addrTracker.next()
    print("%s addrs left to fetch with latest time %s" % (addrTracker.lenToFetch(), latestTime))
    fetchAllAddr(addr)
