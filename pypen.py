#!/usr/bin/python3.5
from datetime import date
import json
from sys import argv, exit

PenTuple = ('Brand', 'Model', 'Price', 'Bought Month', 'Bought Year', 'Nibs')#, 'Filling system')
NibTuple = ('Brand', 'Size', 'Price', 'BoughtMonth', 'BoughtYear', 'Plating', 'Material')
InkTuple = ()

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
        json.dump(PenList,outfile)
    with open('nibs.json', 'w') as outfile:
        json.dump(NibList,outfile)
    with open('inks.json', 'w') as outfile:
        json.dump(InkList,outfile)

def DoTheAdding(item):
    if item == "p":
        brand = input("Pen brand?\n")
        model = input("Pen model?\n")
        price = eval(input("Price?\n"))
        nibs = eval(input("Nibs?\n"))
        boughtmonth, boughtyear = eval(input("Bought in (month,year)?\n"))
        boughtfrom = input("Bought from?\n")
        fillingsystem = input("Filling system? enter for c/c, something else for piston")
        if fillingsystem == '':
            fillingsystem = "Cartridge/converter"
        else:
            fillingsystem = "Piston"
        PenList.append({'Brand': brand, 'Model': model, 'Price': price, 'Bought Month': boughtmonth, 'Bought Year': boughtyear, 'Nibs': nibs, 'Filling system': fillingsystem})

    if item == "n":
        brand = input("Nib Brand?\n")
        steelorgold = input("Steel or gold? (press enter for steel)\n")
        if steelorgold == '':
            steelorgold = 'Steel'
        else:
            steelorgold = '14k gold'
        size = input("Size? Available:\n a) #6,\n b) #6 small,\n c) #5.5,\n d) #5,\n e) #5 small,\n f) lamy,\n g) none of the above \n")
        sizeDict = {'a': '#6', 'b': '#6s', 'c': '#5.5', 'd': '#5', 'e': '#5s', 'f': 'lamy', 'g': 'hooded', 'h': 'other'}
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
        pass

def DoTheChanging():
    change = input("What do you want to change? (p)en, (n)ib or (i)nk \n")
    changeDict = {'p': Pen, 'n': Nib, 'i': Ink}
    print("Which of the items below do you want to modify? Type a number")
    i = 0
    association = {}
    for item in changeDict[change].Lista:
        i += 1
        association[i] = item
        print(i,item.Brand,item.Model)
    ourpen = association[int(input())].__dict__
    print("Which thing do you want to change? Type a number")
    i = 0
    association2 = {}
    for thing in ourpen:
        i += 1
        association2[i] = thing
        print(i,thing,"--",ourpen[thing])
    thingtobechanged = association2[int(input())]
    ourpen[thingtobechanged] = input("Type the correct value\n")

def DoTheListing():
    val = input("What do you want to list? (p)ens, (n)ibs or (i)nks?\n")
    valDict = {'p': (PenList, PenTuple), 'n': (NibList, NibTuple), 'i': (InkList, InkTuple)}
    for item in valDict[val][0]:
        for items in valDict[val][1]:
            print(items,":",item[items],end=', ')
        print('')

def main():
    DoTheImporting('p')
    DoTheImporting('n')
    DoTheImporting('i')
    print("#################")
    print("Welcome to pypen!")
    print("#################\n")
    for pen in PenList:
        print(pen['Model'])
    while True:
        x = input("What do you want to do?\n Possible options are:\n\n (l)ist -- lists items\n (e)xport -- exports json files\n (q)uit -- quits the program\n (ap) add pen\n (an) add nib\n (ai) add ink\n (c)hange something\n")
        if x == "export" or x == "e":
            DoTheExporting()
        elif x == "quit" or x == "q":
            exit()
        elif x == "ap":
            DoTheAdding('p')
        elif x == "an":
            DoTheAdding('n')
        elif x == "ai":
            DoTheAdding('i')
        elif x == "c":
            DoTheChanging()
        elif x == "l":
            DoTheListing()
        else:
            print("Invalid command")

if __name__ == "__main__":
    main()
