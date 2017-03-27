#!/usr/bin/python3.5
import json
from sys import exit
from  collections import OrderedDict

PenTuple = ('Brand', 'Model', 'Price', 'Bought Month', 'Bought Year',
            'Bought From', 'Nibs', 'Filling system', 'Nationality',
            'Class', 'NibRemovability')
NibTuple = ('Brand', 'Size', 'Width', 'Stubness', 'Price', 'BoughtMonth', 'BoughtYear',
            'Plating', 'Material')
InkTuple = ('Brand', 'Name', 'Color', 'BottleOrSample', 'Bottle capacity',
            'BoughtOrPresent', 'BoughtMonth', 'BoughtYear', 'GotFrom', 'Price')
UsageTuple = ('Pen', 'Nib', 'Ink', 'Begin', 'End')


def DoTheImporting(item):
    if item == "p":
        with open('pens.json', 'r') as infile:
            global PenList
            PenList = json.load(infile)
    if item == "n":
        with open('nibs.json', 'r') as infile:
            global NibList
            NibList = json.load(infile)
    if item == "i":
        with open('inks.json', 'r') as infile:
            global InkList
            InkList = json.load(infile)
    if item == "u":
        with open('usage.json', 'r') as infile:
            global UsageList
            UsageList = json.load(infile)


def DoTheExporting():
    with open('pens.json', 'w') as outfile:
        json.dump(PenList, outfile)
    with open('nibs.json', 'w') as outfile:
        json.dump(NibList, outfile)
    with open('inks.json', 'w') as outfile:
        json.dump(InkList, outfile)
    with open('usage.json', 'w') as outfile:
        json.dump(UsageList, outfile)


def DoTheAdding(item):
    if item == "p":
        brand = input("Pen brand?\n")
        model = input("Pen model?\n")
        penid = brand+model
        penid = penid.replace(" ", "")
        price = eval(input("Price?\n"))
        size = input("""Nib Size? Available:
a) #6,
b) #6 small [also: ab) for both]
c) #5.5,
d) #5,
e) #5 small [also: de) for both],
f) lamy,
g) hooded,
h) Pilot number 5,
i) Waterman Hemisphere,
j) Parker Frontier,
k) Sheaffer Agio,
l) Preppy,
m) WingSung -- Pilot steel,
o) other
p) Platinum 3776 Century
s) Sailor 1911 Promenade \n""")
        sizeDict = {'a': '#6', 'b': '#6s', 'ab': ['#6', '#6s'], 'c': '#5.5',
                    'd': '#5', 'e': '#5s', 'de': ['#5', '#5s'],
                    'f': 'lamy', 'g': 'hooded', 'h': 'Pilot5', 'i': 'Hemi',
                    'j': 'Front', 'k': 'Agio', 'l': 'Preppy', 'm': 'PilotSteel', 'o': 'other',
                    'p': 'Platinum3776', 's': 'Sailor1911'}
        boughtmonth, boughtyear = eval(input("Bought in (month,year)?\n"))
        boughtfrom = input("Bought from?\n")
        fillingsystem = input("Filling system? enter for c/c, (p) for piston, \
(l) for lever, (s) for squeeze \n")
        if fillingsystem == '':
            fillingsystem = "Cartridge/converter"
        elif fillingsystem == 'piston' or fillingsystem == 'p':
            fillingsystem = "Piston"
        elif fillingsystem == 'l':
            fillingsystem = "Lever"
        elif fillingsystem == 's':
            fillingsystem = "Squeeze"
        clas = input("Class? Enter for modern, else for vintage \n")
        if clas == '':
            clas = "Modern"
        else:
            clas = "Vintage"
        nation = input("Nationality? \n")
        PenList[penid] = {'Brand': brand, 'Model': model, 'Price': price,
                          'Bought Month': boughtmonth, 'Bought Year':
                          boughtyear, 'Bought From': boughtfrom, 'Nibs':
                          sizeDict[size], 'Filling system': fillingsystem,
                          'Class': clas, 'Nationality': nation}

    if item == "n":
        brand = input("Nib Brand?\n")
        steelorgold = input("Steel or gold? (press enter for steel, else for 14k gold)\n")
        if steelorgold == '':
            steelorgold = 'Steel'
        else:
            steelorgold = '14k gold'
        size = input("""Nib Size? Available:
a) #6,
b) #6 small [also: ab) for both]
c) #5.5,
d) #5,
e) #5 small [also: de) for both],
f) lamy,
g) hooded,
h) Pilot number 5,
i) Waterman Hemisphere,
j) Parker Frontier,
k) Sheaffer Agio,
l) Preppy,
m) Pilot steel (Wingsung659/Lorelei),
o) other
p) Platinum 3776 Century
s) Sailor 1911 Promenade \n""")
        sizeDict = {'a': '#6', 'b': '#6s', 'ab': ['#6', '#6s'], 'c': '#5.5',
                    'd': '#5', 'e': '#5s', 'de': ['#5', '#5s'],
                    'f': 'lamy', 'g': 'hooded', 'h': 'Pilot5', 'i': 'Hemi',
                    'j': 'Front', 'k': 'Agio', 'l': 'Preppy', 'm': 'PilotSteel', 'o': 'other',
                    'p': 'Platinum3776', 's': 'Sailor1911'}
        width = input("Nib width? [1) xxf, 2) ef, 3) f, 4) m, 5) mk, 6) b, 7) bb, 8) 1.1, 9) 1.5), 10) 1.9 \n")
        widthDict = {'1': "XXF", "2": "EF", "3": "F", "4": "M", "5": "MK", "6": "B", "7": "BB", "8": "1.1", "9": "1.5", "10": "1.9"}
        stubness = input("Enter for round, 's' for stub, 'i' for italic, 'a' for architect \n")
        if stubness == '':
            stubness = "Round"
        elif stubness == 's':
            stubness = "Stub"
        elif stubness == 'i':
            stubness = "Italic"
        elif stubness == 'a':
            stubness = "Architect"
        price = input("Price if sold separately?\n")
        if price != '':
            boughtyear = input("Bought in (year) if separately?\n")
            boughtmonth = input("Bought in (month)\n")
            boughtfrom = input("Bought from?\n")
        else:
            boughtyear = ''
            boughtmonth = ''
            boughtfrom = ''
        color = input("Plating? a) rhodium, b) two-tone, c) gold, d) ruthenium \n")
        colorDict = {'a': 'Rhodium','b': 'Two-tone','c': 'Gold','d': 'Ruthenium'}
        nibid = brand+sizeDict[size]+widthDict[width]+stubness+colorDict[color]
        nibid = nibid.replace(" ", "")
        while nibid in NibList:
            nibid = nibid+'i'
        NibList[nibid] = {'Brand': brand, 'Size': sizeDict[size], 'Width': widthDict[width], 'Stubness': stubness, 'Price': price, 'BoughtMonth': boughtmonth, 'BoughtYear': boughtyear, 'Plating': colorDict[color], 'Material': steelorgold}

    if item == "i":
        brand =  input("Ink brand?\n")
        name  =  input("Ink name\n")
        inkid = brand+name
        inkid = inkid.replace(" ", "")
        color =  input("Ink actual color\n")
        volume = input("Bottle capacity in ml?\n")
        if int(volume)>3:
            bottle = "Bottle"
        else:
            bottle = "Sample"
        bop = input("Bought or present? enter for bought\n")
        if bog == '':
            bop = 'Bought'
        else:
            bop = 'Present'
        bm, by = eval(input("Bought in (month,year)?\n"))
        gf = input("Got from?\n")
        price = input("How much did it cost?\n")
        InkList[inkid] = {'Brand': brand, 'Name': name, 'Color': color, 'BottleOrSample': bottle, 'Bottle capacity': volume, "BoughtOrPresent": bop, 'BoughtMonth': bm, 'BoguhtYear': by, 'GotFrom': gf, 'Price': price}
    if item == 'u':
        AddUsage()

def DoTheChanging(val):
    valDict = {'p': (PenList, PenTuple), 'n': (NibList, NibTuple),
               'i': (InkList, InkTuple)}
    print('')
    print("Which item do you want to change?")
    association = {}
    for numb, item in enumerate(sorted(valDict[val][0])):
        association[numb] = item
        print(numb, item)
    whichpen = input()
    print("Press the number of what you want to change:")
    for numb, item in enumerate(valDict[val][1]):
        print(numb, item)
    which = input()
    print("To what are we changing it? (was:",
          valDict[val][0][association[int(whichpen)]][valDict[val][1][int(which)]], ")")
    reading = input()
    if reading == '':
        pass
    else:
        valDict[val][0][association[int(whichpen)]][valDict[val][1][int(which)]] = reading


def DoTheListing(vval):
    val = vval[0]
    valDict = {'p': (PenList, PenTuple), 'n': (NibList, NibTuple),
               'i': (InkList, InkTuple), 'u': (UsageList, UsageTuple)}
    sortedby = valDict[val][1]
    try: sortedby = vval[1]
    except: pass
    print('')
    adjusting = []
    for i in valDict[val][1]:
        adjusting.append(len(i))
    for numb, i in enumerate(valDict[val][1]):
        for j in valDict[val][0]:
            # print(i,j,valDict[val][0][j][i],adjusting[numb])
            if len(str(valDict[val][0][j][i])) > adjusting[numb]:
                adjusting[numb] = len(str(valDict[val][0][j][i]))
    print("-"*(sum(adjusting)+6+len(valDict[val][1]*3)))
    print('| lp', end=' | ')
    for nn, i in enumerate(valDict[val][1]):
        print(i.ljust(adjusting[nn]), end=' | ')
    print("")
    print("-"*(sum(adjusting)+6+len(valDict[val][1]*3)))
    for n, item in enumerate(sorted(valDict[val][0])):
        print("| ",end='')
        print(str(n+1).ljust(2), end=' | ')
        for nn, items in enumerate(valDict[val][1]):
            try:
                print(str(valDict[val][0][item][items]).ljust(adjusting[nn]), end=' | ')
            except:
                pass
        print('')
    print("-"*(sum(adjusting)+6+len(valDict[val][1]*3)))
    exit()


def AddUsage():
    print("Which pen has been used?\n")
    association = {}
    for numb, item in enumerate(sorted(PenList)):
        association[numb] = item
        print(numb, item)
    whichpen = association[int(input())]
    if PenList[whichpen]["NibRemovability"] == "Nonremovable":
        whichnib = PenList[whichpen]["OriginalNib"]
    else:
        print("Which nib has been used?\n")
        association = {}
        for numb, item in enumerate(sorted(NibList)):
            association[numb] = item
            print(numb, item)
        whichnib = association[int(input())]
    print("Which ink has been used?\n")
    association = {}
    for numb, item in enumerate(sorted(InkList)):
        association[numb] = item
        print(numb, item)
    whichink = association[int(input())]
    begd,begm,begy = eval(input("When inked up? d,m,y   "))
    endd,endm,endy = eval(input("When inked down? d,m,y   "))
    usageid = whichpen+str(begd)+"."+str(begm)+"."+str(begy)
    UsageList[usageid] = {'Pen': whichpen, 'Nib': whichnib, 'Ink': whichink,
                          'Begin': [begd,begm,begy], 'End': [endd,endm,endy]}


def main():
    DoTheImporting('p')
    DoTheImporting('n')
    DoTheImporting('i')
    DoTheImporting('u')
    # total=0
    # for pen in sorted(PenList):
    #     total+= int(PenList[pen]['Price'])
    # print("total",total)
    print("#################")
    print("Welcome to pypen!")
    while True:
        print("#################\n")
        x = input("""What do you want to do?
Possible options are:

(e)xport -- exports json files
(q)uit -- exports the database and quits the program
(lX) list:
        X: (p)ens, (n)ibs, (i)nks, (u)sages
(aX) add
(cX) change \n""")
        if x[0] == "e":
            DoTheExporting()
        elif x[0] == "q":
            DoTheExporting()
            exit()
        elif x[0] == "a":
            DoTheAdding(x[1])
        elif x[0] == "c":
            DoTheChanging(x[1])
        elif x[0] == "l":
            DoTheListing(x[1:])
        else:
            print("Invalid command")



if __name__ == "__main__":
    main()
