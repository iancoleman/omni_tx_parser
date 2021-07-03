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
    if "sendingaddress" in tx and tx["sendingaddress"] == "15jiVUZLqg9ExtyDdfHsjA1J5efujTBqJL":
        print(json.dumps(tx, indent="  "))
    if "referenceaddress" in tx and tx["referenceaddress"] == "15jiVUZLqg9ExtyDdfHsjA1J5efujTBqJL":
        print(json.dumps(tx, indent="  "))
    if tx["type"] == "Simple Send":
        src = tx["sendingaddress"]
        if src not in balances:
            balances[src] = 0
        dst = tx["referenceaddress"]
        if dst not in balances:
            balances[dst] = 0
        amount = float(tx["amount"])
        balances[src] = balances[src] - amount
        balances[dst] = balances[dst] + amount
    elif tx["type"] == "Crowdsale Purchase":
        src = tx["sendingaddress"]
        if src not in balances:
            balances[src] = 0
        amount = float(tx["purchasedtokens"])
        balances[src] = balances[src] + amount
        totalcp = totalcp + amount
    elif tx["type"] == "Send All":
        src = tx["sendingaddress"]
        if src not in balances:
            balances[src] = 0
        dst = tx["referenceaddress"]
        if dst not in balances:
            balances[dst] = 0
        for subsend in tx["subsends"]:
            if subsend["propertyid"] == MAID:
                amount = float(subsend["amount"])
                balances[src] = balances[src] - amount
                balances[dst] = balances[dst] + amount
    elif tx["type"] == "MetaDEx trade":
        if tx["propertyiddesired"] == MAID:
            dst = tx["sendingaddress"]
            if dst not in balances:
                balances[dst] = 0
            amount = float(tx["amountdesired"])
            balances[dst] = balances[dst] + amount # Is this right?
        if tx["propertyidforsale"] == MAID:
            src = tx["sendingaddress"]
            if src not in balances:
                balances[src] = 0
            amount = float(tx["amountforsale"])
            balances[src] = balances[src] - amount # Is this right?
    elif tx["type"] == "MetaDEx cancel-price":
        if tx["propertyiddesired"] == MAID:
            dst = tx["sendingaddress"]
            if dst not in balances:
                balances[dst] = 0
            amount = float(tx["amountdesired"])
            balances[dst] = balances[dst] - amount # Is this right?
        if tx["propertyidforsale"] == MAID:
            src = tx["sendingaddress"]
            if src not in balances:
                balances[src] = 0
            amount = float(tx["amountforsale"])
            balances[src] = balances[src] + amount # Is this right?
    elif tx["type"] == "Create Property - Variable":
        continue
    elif tx["type"] == "Close Crowdsale":
        continue
    else:
        print("Unknown tx type %s %s" % (tx["type"], tx["txid"]))

print("Total maidsafecoin in crowdsale purchase: %s" % totalcp)

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
