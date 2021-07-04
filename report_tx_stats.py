import json
import math
import sys

MAID = 3

f = open("all_maidsafecoin_txs.json")
content = f.read()
f.close()

txs = json.loads(content)
txs = sorted(txs, key=lambda t: (t["block"], int(t["txid"][:8],16)))

print("Total txs: %s" % len(txs))

class Dex:

    def __init__(self):
        self.orders = []

    def add(self, address, desiredAmount, desiredPropertyId, saleAmount, salePropertyId):
        order = {
            "address": address,
            "desiredAmount": desiredAmount,
            "desiredPropertyId": desiredPropertyId,
            "saleAmount": saleAmount,
            "salePropertyId": salePropertyId,
            "cancelled": False,
            "saleMatched": 0,
            "desiredMatched": 0,
        }
        orderRate = desiredAmount / saleAmount
        # match the order to the best rate
        # and resolve ties with FIFO by keeping
        # the order chronological and using the first
        # instance of the best rate
        transactions = []
        orderFullyMatched = self.isFullyMatched(order)
        while not orderFullyMatched:
            bestMatchIndex = None
            bestMatchRate = 9999999999
            for i, o in enumerate(self.orders):
                # do not match with cancelled orders
                if o["cancelled"]:
                    continue
                # check if existing order desires what this order is selling
                if o["desiredPropertyId"] != order["salePropertyId"]:
                    continue
                # check if existing order is selling what this order desires
                if o["salePropertyId"] != order["desiredPropertyId"]:
                    continue
                # do not match with orders that are already matched
                if o["saleMatched"] >= o["saleAmount"]:
                    continue
                if o["desiredMatched"] >= o["desiredAmount"]:
                    continue
                # check the rate is suitable
                oRate = o["desiredAmount"] / o["saleAmount"]
                comparableRate = 1 / oRate
                if orderRate > comparableRate:
                    continue
                if comparableRate < bestMatchRate:
                    bestMatchRate = comparableRate
                    bestMatchIndex = i
            # if there are no matches then this order is finished matching
            if bestMatchIndex is None:
                break
            # calculate the transfer amounts
            bm = self.orders[bestMatchIndex]
            bmMatchedSale = 0
            bmMatchedDesired = 0
            bmSaleRemaining = bm["saleAmount"] - bm["saleMatched"]
            bmDesiredRemaining = bm["desiredAmount"] - bm["desiredMatched"]
            orderDesiredRemaining = order["desiredAmount"] - order["desiredMatched"]
            orderSaleRemaining = order["saleAmount"] - order["saleMatched"]
            if bmSaleRemaining <= orderDesiredRemaining:
                # earlier order sale amount is completely consumed
                bmMatchedSale = bmSaleRemaining
                bmMatchedDesired = bmDesiredRemaining
            else:
                # newer order desired amount is completely consumed
                bmMatchedSale = orderDesiredRemaining
                bmMatchedDesired = orderSaleRemaining
            # create the transactions
            transactions.append({
                "sendingaddress": bm["address"],
                "referenceaddress": order["address"],
                "amount": str(bmMatchedSale),
                "type_int": 0,
                "type": "Simple Send",
                "propertyid": bm["salePropertyId"],
                "valid": True,
            })
            transactions.append({
                "sendingaddress": order["address"],
                "referenceaddress": bm["address"],
                "amount": str(bmMatchedDesired),
                "type_int": 0,
                "type": "Simple Send",
                "propertyid": order["salePropertyId"],
                "valid": True,
            })
            # add these matched amounts to the existing order
            self.orders[bestMatchIndex]["saleMatched"] = bm["saleMatched"] + bmMatchedSale
            self.orders[bestMatchIndex]["desiredMatched"] = bm["desiredMatched"] + bmMatchedDesired
            # add these matched amounts to the new order
            order["saleMatched"] = order["saleMatched"] + bmMatchedDesired
            order["desiredMatched"] = order["desiredMatched"] + bmMatchedSale
            # if this new order has been fully matched, we can stop here
            orderFullyMatched = self.isFullyMatched(order)
        # record this order
        self.orders.append(order)
        return transactions

    def isFullyMatched(self, order):
        fullySold = order["saleMatched"] >= order["saleAmount"]
        fullyDesired = order["desiredMatched"] >= order["desiredAmount"]
        return fullySold and fullyDesired

    def cancel(self, address, desiredAmount, desiredPropertyId, saleAmount, salePropertyId, txid):
        didCancel = False
        for o in self.orders:
            if o["address"] != address:
                continue
            if o["desiredAmount"] != desiredAmount:
                continue
            if o["desiredPropertyId"] != desiredPropertyId:
                continue
            if o["saleAmount"] != saleAmount:
                continue
            if o["salePropertyId"] != salePropertyId:
                continue
            if o["cancelled"] == True:
                continue
            o["cancelled"] = True
            didCancel = True
            break
        if not didCancel:
            print("No matching order to cancel for %s %s" % (address, txid))

dex = Dex()

balances = {
    "1ARjWDkZ7kT9fwjPrjcQyvbXDkEySzKHwu": 1452520155,
}
totalcp = 0
for tx in txs:
    if not tx["valid"]:
        continue
    addrSrc = ""
    addrDst = ""
    amountSrc = "0"
    amountDst = "0"
    if tx["type"] == "Simple Send":
        # eg d06af7214cfed65bbd7bd0881c7152fd5e32fbdabcfa4ab2cfd4115deaa66971
        addrSrc = tx["sendingaddress"]
        addrDst = tx["referenceaddress"]
        amountSrc = tx["amount"]
        amountDst = tx["amount"]
    elif tx["type"] == "Send All":
        # eg b6380b4a95c836bcf3899311dffc2814a7c2b40055336ea080f47a92f4cc5bc0
        addrSrc = tx["sendingaddress"]
        addrDst = tx["referenceaddress"]
        for subsend in tx["subsends"]:
            if subsend["propertyid"] == MAID:
                amountSrc = subsend["amount"]
                amountDst = subsend["amount"]
    elif tx["type"] == "Crowdsale Purchase":
        # eg d55b05195d1e52ef09da12f251aa23b46807af80ffe85fe0c28e052761612705
        # addrs seems backwards but it's correct
        addrSrc = tx["referenceaddress"]
        addrDst = tx["sendingaddress"]
        amountSrc = tx["purchasedtokens"]
        amountDst = tx["purchasedtokens"]
        totalcp = totalcp + float(amountDst)
    elif tx["type"] == "MetaDEx trade":
        # eg ada786071ea9f4c0c0f9a8ab7bde7e20160ec46ac7ae74c5c2f1127318e121b1
        address = tx["sendingaddress"]
        desiredAmount = float(tx["amountdesired"])
        desiredPropertyId = tx["propertyiddesired"]
        saleAmount = float(tx["amountforsale"])
        salePropertyId = tx["propertyidforsale"]
        dextxs = dex.add(address, desiredAmount, desiredPropertyId, saleAmount, salePropertyId)
        for dextx in dextxs:
            if dextx["propertyid"] == MAID:
                addrSrc = dextx["sendingaddress"]
                addrDst = dextx["referenceaddress"]
                amountSrc = dextx["amount"]
                amountDst = dextx["amount"]
    elif tx["type"] == "MetaDEx cancel-price":
        # eg 3277318d3a18e28fdead0b0b3cd065849000073446472a79f0099fe4f24b864a
        address = tx["sendingaddress"]
        desiredAmount = float(tx["amountdesired"])
        desiredPropertyId = tx["propertyiddesired"]
        saleAmount = float(tx["amountforsale"])
        salePropertyId = tx["propertyidforsale"]
        txid = tx["txid"]
        dex.cancel(address, desiredAmount, desiredPropertyId, saleAmount, salePropertyId, txid)
    elif tx["type"] == "Create Property - Variable":
        # eg 86f214055a7f4f5057922fd1647e00ef31ab0a3ff15217f8b90e295f051873a7
        continue
    elif tx["type"] == "Close Crowdsale":
        continue
    else:
        print("Unknown tx type %s %s" % (tx["type"], tx["txid"]))
        continue
    # do some checks
    amountSrcFlt = float(amountSrc)
    amountDstFlt = float(amountDst)
    if math.floor(amountSrcFlt) != amountSrcFlt:
        print("Decimal maidsafecoin amount: %s %s" % (amountSrc, tx["txid"]))
    if math.floor(amountDstFlt) != amountDstFlt:
        print("Decimal maidsafecoin amount: %s %s" % (amountDst, tx["txid"]))
    # do the accounting
    if addrSrc != "":
        if addrSrc not in balances:
            balances[addrSrc] = 0
        balances[addrSrc] = balances[addrSrc] - amountSrcFlt
    if addrDst != "":
        if addrDst not in balances:
            balances[addrDst] = 0
        balances[addrDst] = balances[addrDst] + amountDstFlt
    # check for negative balances
    if addrSrc in balances and balances[addrSrc] < 0:
        print("Addr just went to invalid negative balance %s: %s with tx %s" % (balances[addrSrc], addrSrc, tx["txid"]))
        sys.exit(0)
    if addrDst in balances and balances[addrDst] < 0:
        print("Addr just went to invalid negative balance %s: %s with tx %s" % (balances[addrDst], addrDst, tx["txid"]))
        sys.exit(0)

print("Total maidsafecoin in crowdsale purchase: %s" % totalcp)

totalFromUtxos = 0
for addr in balances:
    totalFromUtxos = totalFromUtxos + balances[addr]
print("Total maidsafecoin from current balances: %s" % totalFromUtxos)

ltz = 0
ltzAddrs = []
gtz = 0
z = 0
for addr in balances:
    if balances[addr] < 0:
        ltz = ltz + 1
        ltzAddrs.append(addr)
    if balances[addr] == 0:
        z = z + 1
    if balances[addr] > 0:
        gtz = gtz + 1

print("Total addrs: %s" % len(balances.keys()))
print("Addrs with gt zero balance: %s" % gtz)
print("Addrs with lt zero balance: %s" % ltz)
print("Addrs with zero balance: %s" % z)

for addr in ltzAddrs:
    print("lt 0 balance: %s %s" % (addr, balances[addr]))

# report the state of the dex orderbook
dexbuys = 0
dexsells = 0
for o in dex.orders:
    if o["cancelled"]:
        continue
    if o["saleMatched"] >= o["saleAmount"]:
        continue
    if o["desiredMatched"] >= o["desiredAmount"]:
        continue
    if o["desiredPropertyId"] == MAID:
        dexbuys = dexbuys + o["desiredMatched"]
    if o["salePropertyId"] == MAID:
        dexsells = dexsells + o["saleMatched"]
print("Dex maidsafecoin waiting to be sold: %s" % dexsells)
print("Dex maidsafecoin waiting to be bought: %s" % dexbuys)







testdex = Dex()
# add order to buy 100 maidsafecoin for 1 omnicoin
#def add(self, address, desiredAmount, desiredPropertyId, saleAmount, salePropertyId):
testdex.add("a", 100, 3, 1, 1)
# add another order to buy 10 omnicoin for 50 maidsafecoin
testdex.add("b", 10, 1, 50, 3)
# should be no matched orders yet
for o in testdex.orders:
    assert(o["saleMatched"] == 0)
    assert(o["desiredMatched"] == 0)
