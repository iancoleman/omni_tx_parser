import json

MAID = 3

f = open("all_maidsafecoin_txs.json")
content = f.read()
f.close()

txs = json.loads(content)

print("Total txs: %s" % len(txs))

balances = {}
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
        if tx["propertyiddesired"] == MAID:
            addrDst = tx["sendingaddress"]
            amountDst = tx["amountdesired"] # Is this right?
        if tx["propertyidforsale"] == MAID:
            addrSrc = tx["sendingaddress"]
            amountSrc = tx["amountforsale"] # Is this right?
    elif tx["type"] == "MetaDEx cancel-price":
        # eg 3277318d3a18e28fdead0b0b3cd065849000073446472a79f0099fe4f24b864a
        if tx["propertyiddesired"] == MAID:
            addrDst = tx["sendingaddress"]
            amountDst = "-" + tx["amountdesired"] # Is this right?
        if tx["propertyidforsale"] == MAID:
            addrSrc = tx["sendingaddress"]
            amountSrc = "-" + tx["amountforsale"] # Is this right?
    elif tx["type"] == "Create Property - Variable":
        # eg 86f214055a7f4f5057922fd1647e00ef31ab0a3ff15217f8b90e295f051873a7
        continue
    elif tx["type"] == "Close Crowdsale":
        continue
    else:
        print("Unknown tx type %s %s" % (tx["type"], tx["txid"]))
        continue
    # do some checks
    if amountSrc.find(".") > -1:
        print("Decimal maidsafecoin amount: %s %s" % (amountSrc, tx["txid"]))
    if amountDst.find(".") > -1:
        print("Decimal maidsafecoin amount: %s %s" % (amountDst, tx["txid"]))
    # do the accounting
    if addrSrc != "":
        if addrSrc not in balances:
            balances[addrSrc] = 0
        balances[addrSrc] = balances[addrSrc] - float(amountSrc)
    if addrDst != "":
        if addrDst not in balances:
            balances[addrDst] = 0
        balances[addrDst] = balances[addrDst] + float(amountDst)

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
