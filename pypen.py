#!/usr/bin/python3.5
import json
from sys import exit

PenTuple = ('Brand', 'Model', 'Price', 'Bought Month', 'Bought Year',
            'Bought From', 'Nibs', 'Filling system')
NibTuple = ('Brand', 'Size', 'Width', 'Price', 'BoughtMonth', 'BoughtYear',
            'Plating', 'Material')
InkTuple = ('Brand', 'Name', 'Color', 'BottleOrSample', 'Bottle capacity')


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


def DoTheExporting():
    with open('pens.json', 'w') as outfile:
        json.dump(PenList, outfile)
    with open('nibs.json', 'w') as outfile:
        json.dump(NibList, outfile)
    with open('inks.json', 'w') as outfile:
        json.dump(InkList, outfile)


def DoTheAdding(item):
    if item == "p":
        brand = input("Pen brand?\n")
        model = input("Pen model?\n")
        penid = brand+model
        penid = penid.replace(" ", "")
        price = eval(input("Price?\n"))
        size = input("""Nib Size? Available:
a) #6,
b) #6 small [also: ab) for both],
c) #5.5,
d) #5,
e) #5 small [also: de) for both],
f) lamy,
g) hooded
h) other \n""")
        sizeDict = {'a': '#6', 'b': '#6s', 'ab': ['#6', '#6s'], 'c': '#5.5',
                    'd': '#5', 'e': '#5s', 'de': ['#5', '#5s'],
                    'f': 'lamy', 'g': 'hooded', 'h': 'other'}
        boughtmonth, boughtyear = eval(input("Bought in (month,year)?\n"))
        boughtfrom = input("Bought from?\n")
        fillingsystem = input("Filling system? enter for c/c, something else for \
piston")
        if fillingsystem == '':
            fillingsystem = "Cartridge/converter"
        elif fillingsystem == 'piston' or fillingsystem == 'p':
            fillingsystem = "Piston"
        PenList[penid] = {'Brand': brand, 'Model': model, 'Price': price,
                          'Bought Month': boughtmonth, 'Bought Year':
                          boughtyear, 'Bought From': boughtfrom, 'Nibs':
                          sizeDict[size], 'Filling system': fillingsystem}

    if item == "n":
        brand = input("Nib Brand?\n")
        steelorgold = input("Steel or gold? (press enter for steel)\n")
        if steelorgold == '':
            steelorgold = 'Steel'
        else:
            steelorgold = '14k gold'
        size = input("Size? Available:\n a) #6,\n b) #6 small,\n c) #5.5,\n \
        d) #5,\n e) #5 small,\n f) lamy,\n g) none of the above \n")
        sizeDict = {'a': '#6', 'b': '#6s', 'c': '#5.5', 'd': '#5', 'e': '#5s',
        'f': 'lamy', 'g': 'hooded', 'h': 'other'}
        width = input("Nib width? (xxf, ef, f, m, mk, b, ) \n")
        price = input("Price if sold separately?\n")
        boughtyear = input("Bought in (year) if separately?\n")
        if boughtyear != '':
            boughtmonth = input("Bought in (month)\n")
            boughtfrom = input("Bought from?\n")
        color = input("Plating? a) rhodium, b) two-tone, c) gold, d) ruthenium/n")
        colorDict = {'a': 'Rhodium','b': 'Two-tone','c': 'Gold','d': 'Ruthenium'}
        NibList.append({'Brand': brand, 'Size': sizeDict[size], 'Price': price, 'BoughtMonth': boughtmonth, 'BoughtYear': boughtyear, 'Plating': colorDict[color], 'Material': steelorgold})

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
        InkList[inkid] = {'Brand': brand, 'Name': name, 'Color': color, 'BottleOrSample': bottle, 'Bottle capacity': volume}

def DoTheChanging(val):
    if val == "p":
        print("Which pen do you want to change?")
        for item in PenList:
            print(item)
        whichpen = input()
        print("Press the number of what you want to change:")
        for numb, item in enumerate(PenTuple):
            print(numb, item)
        which = input()
        print("To what are we changing it?")
        PenList[whichpen][PenTuple[int(which)]] = input()


def DoTheListing(val):
    valDict = {'p': (PenList, PenTuple), 'n': (NibList, NibTuple),
               'i': (InkList, InkTuple)}
    print('')
    for n, item in enumerate(valDict[val][0]):
        print(str(n+1).zfill(2), end=' ')
        for items in valDict[val][1]:
            try:
                print(valDict[val][0][item][items], end=', ')
            except:
                pass
        print('')
    print('')


def main():
    DoTheImporting('p')
    DoTheImporting('n')
    DoTheImporting('i')
    print("#################")
    print("Welcome to pypen!")
    while True:
        print("#################\n")
        x = input("""What do you want to do?
Possible options are:

(lp) list pens, (li) list inks
(e)xport -- exports json files
(q)uit -- exports the database and quits the program, (qwe) -- quit without export
(ap) add pen, (an) add nib, (ai) add ink
(cp) change pen\n""")
        if x == "export" or x == "e":
            DoTheExporting()
        elif x == "quit" or x == "q":
            DoTheExporting()
            exit()
        elif x == "qwe":
            exit()
        elif x == "ap":
            DoTheAdding('p')
        elif x == "an":
            DoTheAdding('n')
        elif x == "ai":
            DoTheAdding('i')
        elif x == "cp":
            DoTheChanging('p')
        elif x == "lp":
            DoTheListing('p')
        elif x == "li":
            DoTheListing('i')
        else:
            print("Invalid command")


if __name__ == "__main__":
    main()
