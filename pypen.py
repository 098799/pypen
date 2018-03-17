#!/usr/bin/env python3
# I want my program to make Gantt charts
import collections
import datetime
import json
import sys
import tabulate

import pandas as pd


possible_values = ['p', 'i', 'u']

TheList = {'p': {}, 'i': {}, 'u': {}}
TheTuple = {'p': [], 'i': [], 'u': []}

file_name = {
    "p": "pens.json",
    "i": "inks.json",
    "u": "usage.json",
}

example = {
    'p': "Jinhao250",
    'i': "DeAtramentisAubergine",
    'u': "Baoer05122.03.2017",
}


def DoTheImporting(item):
    def InsidesOfTheImporting(which):
        TheList[which] = json.load(infile)
        for i in TheList[which][example[which]].keys():
            TheTuple[which].append(i)
        TheTuple[which].sort()

    with open(file_name[item], 'r') as infile:
        InsidesOfTheImporting(item)


def DoTheExporting(item):
    for item in possible_values:
        with open(file_name[item], 'w') as outfile:
            json.dump(TheList[item], outfile, indent=4, sort_keys=True)


def DoTheAdding(item):
    if item in ("p", "i", "u"):
        temporary = {}
        for char in TheTuple[item]:
            print("\n " + "-"*len(char), "\n", char, "\n", "-"*len(char))
            association = []
            for pen in TheList[item]:
                val = TheList[item][pen][char]
                if val not in association:
                    association.append(val)
            association.sort()
            for number, item in enumerate(association, 1):
                print(number, item)
            print("or click enter to input yourself")
            thatInput = input("Which?")
            if thatInput == "":
                thatInput = input("Type here\n")
            else:
                thatInput = association[int(thatInput)]
            print(thatInput)
            temporary[char] = thatInput
        penID = make_id[temporary["Brand"], temporary["Model"]]
        TheList[item][penID] = temporary
    if item == 'u':
        AddBeginningOfUsage()
    if item == 'd':
        AddEndOfUsage()
    if item == 'b':
        AddBeginningOfUsage(isItToday=True)
    if item == 'e':
        AddEndOfUsage(isItToday=True)


def make_id(brand, model):
    return (brand + model).replace(" ", "")


def DoTheChanging(item):
    print('')
    print("Which item do you want to change?")
    association = {}
    for numb, val in enumerate(sorted(TheList[item]), 1):
        association[numb] = val
        print(numb, val)
    whichpen = input()
    pen_id = association[int(whichpen)]
    print("Press the number of what you want to change:")
    for numb, val in enumerate(TheTuple[item], 1):
        print(numb, val)
    which = input()
    char_id = TheTuple[item][int(which)-1]
    print("To what are we changing it? (was:",
          TheList[item][pen_id][char_id],
          ")")
    reading = input()
    if reading == '':
        pass
    else:
        TheList[item][pen_id][char_id] = reading


# I stopped refactoring here, so go from here


def DoTheListing(val):
    valDict = {'p': TheList['p'], 'i': TheList['i'], 'u': TheList['u']}

    def insidesOfTheListing(theList, byWhat, dropWhat):
        by = []
        for item in byWhat:
            if "=" in item:
                firstArg = (item.split("="))[0]
                secArg = (item.split("="))[1]
                newDict = {}
                for j in theList:
                    firstValue = theList[j][firstArg]
                    if "-" in firstValue:
                        firstValue = firstValue.split("-")[0]
                    if firstValue == secArg:
                        newDict[j] = theList[j]
                by.append(firstArg)
                theList = newDict
                if theList == {}:
                    print("None")
                    return
            elif ".GT." in item:
                firstArg = (item.split(".GT."))[0]
                secArg = (item.split(".GT."))[1]
                newDict = {}
                for j in theList:
                    firstValue = str(theList[j][firstArg])
                    if "-" in firstValue:
                        firstValue = firstValue.split("-")[0]
                    if float(firstValue) > float(secArg):
                        newDict[j] = theList[j]
                by.append(firstArg)
                theList = newDict
                if theList == {}:
                    print("None")
                    return
            elif ".LT." in item:
                firstArg = (item.split(".LT."))[0]
                secArg = (item.split(".LT."))[1]
                newDict = {}
                for j in theList:
                    firstValue = str(theList[j][firstArg])
                    if "-" in firstValue:
                        firstValue = firstValue.split("-")[0]
                    if float(firstValue) < float(secArg):
                        newDict[j] = theList[j]
                by.append(firstArg)
                theList = newDict
                if theList == {}:
                    print("None")
                    return
            else:
                by.append(item)
        DF = pd.DataFrame.from_dict(theList).T
        howtoascend = True
        if by == "Date":
            by = "Bought"
        if dropWhat != []:
            for i in dropWhat:
                DF = DF.drop(i, 1)
        DF = DF.sort_values(by=by, ascending=howtoascend)

        formatt = "psql"
        DF = DF.reset_index()
        DF.index = range(1, len(DF.index)+1)
        print(tabulate.tabulate(DF, headers='keys', tablefmt=formatt))
        # nice formats: pipe, psql, rst

    byWhat = []
    dropWhat = []
    for item in sys.argv[2:]:
        if item[0] == "-":
            dropWhat.append(item[1:])
        else:
            byWhat.append(item)

    if val == "i":
        theList = {}
        theUsedUpList = {}
        if byWhat == []:
            byWhat = ["Brand"]
        for ink in valDict[val]:
            if valDict[val][ink]["UsedUp"] == "No":
                theList[ink] = valDict[val][ink]
            else:
                theUsedUpList[ink] = valDict[val][ink]
        print("\n** Used Up ***")
        insidesOfTheListing(theUsedUpList, byWhat, dropWhat)
        print("\n** In Rotation ***")
        dropWhat.append("UsedUp")
        insidesOfTheListing(theList, byWhat, dropWhat)
    elif val == "p":
        theList = {}
        theOutList = {}
        if byWhat == []:
            byWhat = ["Brand"]
        for pen in valDict[val]:
            if valDict[val][pen]["Rot"] not in ["Out", "Broken"]:
                theList[pen] = valDict[val][pen]
            else:
                theOutList[pen] = valDict[val][pen]
        print("\n** Left the rotation ***")
        insidesOfTheListing(theOutList, byWhat, dropWhat)
        print("\n** In Rotation ***")
        dropWhat.append("Out")
        dropWhat.append("OutPr")
        insidesOfTheListing(theList, byWhat, dropWhat)
    else:
        theList = valDict[val]
        if byWhat == []:
            byWhat = ["End"]
        insidesOfTheListing(theList, byWhat, dropWhat)


def AddUsage():
    print("Which pen has been used?\n")
    association = {}
    for numb, item in enumerate(sorted(TheList['p']), 1):
        association[numb] = item
        print(numb, item)
    whichpen = association[int(input())]
    whichnib = input("What sized nib? ")
    print("Which ink has been used? enter for ink sample \n")
    association = {}
    for numb, item in enumerate(sorted(TheList['i']), 1):
        association[numb] = item
        print(numb, item)
    inkzi = input()
    if inkzi == "":
        inkzii = input("Write down the name of the sample ")
        whichink = "(s) "+inkzii
    else:
        whichink = association[int(inkzi)]
    begd = input("When inked up? day (enter for today)   ")
    if begd == "":
        begd = datetime.date.today().day
        begm = datetime.date.today().month
        begy = datetime.date.today().year
    else:
        begm = input("When inked up? month ")
        begy = '2018'
        begyq = input("When inked up? year (2018 as a default) ")
        if not (begyq == ''):
            begy = begyq
    endd = input("When inked down? day (enter for today)   ")
    if endd == "":
        endd = datetime.date.today().day
        endm = datetime.date.today().month
        endy = datetime.date.today().year
    else:
        endm = input("When inked down? month ")
        endy = '2018'
        endyq = input("When inked down? year (2018 as a default) ")
        if not (endyq == ''):
            endy = endyq
    usageid = whichpen+str(begd)+"."+str(begm)+"."+str(begy)
    TheList['u'][usageid] = {'Pen': whichpen, 'Nib': whichnib, 'Ink': whichink,
                             'Begin': dateFormat(begy, begm, begd),
                             'End': dateFormat(endy, endm, endd)}


def AddBeginningOfUsage(**kwargs):
    print("Which pen has been used?\n")
    association = {}
    for numb, item in enumerate(sorted(TheList['p']), 1):
        association[numb] = item
        print(numb, item)
    whichpen = association[int(input())]
    whichnib = input("What sized nib? ")
    print("Which ink has been used? enter for ink sample \n")
    association = {}
    for numb, item in enumerate(sorted(TheList['i']), 1):
        association[numb] = item
        print(numb, item)
    inkzi = input()
    if inkzi == "":
        inkzii = input("Write down the name of the sample ")
        whichink = "(s) "+inkzii
    else:
        whichink = association[int(inkzi)]
    if 'isItToday' in kwargs:
        begd = datetime.date.today().day
        begm = datetime.date.today().month
        begy = datetime.date.today().year
    else:
        begd = input("When inked up? day (enter for today)   ")
        if begd == "":
            begd = datetime.date.today().day
            begm = datetime.date.today().month
            begy = datetime.date.today().year
        else:
            begm = input("When inked up? month ")
            begy = '2018'
            begyq = input("When inked up? year (2018 as a default) ")
            if not (begyq == ''):
                begy = begyq
    usageid = whichpen+str(begd)+"."+str(begm)+"."+str(begy)
    TheList['u'][usageid] = {'Pen': whichpen, 'Nib': whichnib, 'Ink': whichink,
                             'Begin': dateFormat(begy, begm, begd),
                             'End': ""}


def AddEndOfUsage(**kwargs):
    print("We're adding an end date to one of those pens:")
    association = {}
    i = 0
    for item in TheList['u']:
        if TheList['u'][item]["End"] == "":
            i += 1
            print(i, item)
            association[i] = item
    whichusage = association[int(input("Which one?"))]
    if 'isItToday' in kwargs:
        begd = datetime.date.today().day
        begm = datetime.date.today().month
        begy = datetime.date.today().year
    else:
        begd = input("When inked down? day (enter for today)   ")
        if begd == "":
            begd = datetime.date.today().day
            begm = datetime.date.today().month
            begy = datetime.date.today().year
        else:
            begm = input("When inked down? month ")
            begy = '2018'
            begyq = input("When inked down? year (2018 as a default) ")
            if not (begyq == ''):
                begy = begyq
    TheList['u'][whichusage]["End"] = dateFormat(begy, begm, begd)


def dateFormat(a, b, c):
    return str(a)+"-"+str(b).zfill(2)+"-"+str(c).zfill(2)


def DoTheSumming(val='p'):
    valDict = {'p': TheList['p'], 'i': TheList['i'], 'u': TheList['u']}
    theList = valDict[val]
    coDict = {'p': "pen", 'u': "usage", 'i': "ink"}

    def printing(a):
        print(tabulate.tabulate(pd.DataFrame(a.most_common()), tablefmt="psql"))

    def numberOfDays(a, b):
        if a == "":
            first = datetime.date.today()
            second = first
        elif b == "":
            first = datetime.date.today()
            second = datetime.date(*[int(i) for i in a.split("-")])
        else:
            first = datetime.date(*[int(i) for i in b.split("-")])
            second = datetime.date(*[int(i) for i in a.split("-")])
        return (first-second).days

    def DoTheThing(thing):
        if thing == "Bought":
            print("**Bought**")
            boughtcounter = []
            for item in theList:
                boughtcounter.append(theList[item]["Bought"].split("-")[0])
            boughtCounter = collections.Counter(boughtcounter)
            printing(boughtCounter)
        elif thing == "Price":
            print("**Price**")
            suma = 0
            for item in theList:
                suma += theList[item]["Price"]
            print("Wasted", suma, "PLN on stupid", coDict[val]+'s. By year:')
            sumapre = 0
            suma2015 = 0
            suma2016 = 0
            suma2017 = 0
            for item in theList:
                itemPrice = theList[item]["Price"]
                dateofbuying = int(theList[item]["Bought"].split("-")[0])
                if dateofbuying < 2015:
                    sumapre += itemPrice
                elif dateofbuying < 2016:
                    suma2015 += itemPrice
                elif dateofbuying < 2017:
                    suma2016 += itemPrice
                elif dateofbuying < 2018:
                    suma2017 += itemPrice
            print("pre2015:", sumapre)
            print("   2015:", suma2015)
            print("   2016:", suma2016)
            print("   2017:", suma2017)
        elif thing == "ColorClass":
            print("**ColorClass**")
            itemziocounter = []
            itemziDict = {'Brown': 'Brown', 'Black': 'Black', 'Green': 'Green',
                          'Red': 'Red', 'Purple': 'Purple',
                          'Blue Black': 'Blue', 'Blue': 'Blue',
                          'Turquoise': 'Blue', 'Pink': 'Pink',
                          'Orange': 'Orange', 'Royal Blue': 'Blue',
                          'Grey': 'Grey', 'Teal': 'Teal', "Burgundy": "Purple"}
            for item in theList:
                itemzio = theList[item]['Color']
                itemziocounter.append(itemziDict[itemzio])
            itemzioCounter = collections.Counter(itemziocounter)
            printing(itemzioCounter)
        elif thing == "Pen":
            print("**"+thing+"**")
            counterek = []
            howlong = {}
            rotations = []
            for i in TheList['p']:
                val2 = TheList['p'][i]["Rot"]
                if val2 not in rotations:
                    rotations.append(val2)
            rotations.remove("Broken")
            for rotation in sorted(rotations)[::-1]:
                howlong = {}
                print("*Rotation number "+rotation+"*")
                for item in theList:
                    val1 = theList[item]
                    val1th = theList[item][thing]
                    if TheList['p'][val1th]["Rot"] == rotation:
                        if val1th not in howlong:
                            howlong[val1th] = {
                                "HowMany": 1,
                                "HowLong": numberOfDays(
                                    val1["Begin"],
                                    val1["End"]
                                ),
                                "WhenLast": numberOfDays(
                                    val1["End"],
                                    ""
                                )
                            }
                        else:
                            howlong[val1th]["HowMany"] += 1
                            howlong[val1th]["HowLong"] += numberOfDays(
                                val1["Begin"], val1["End"]
                            )
                            if numberOfDays(
                                    val1["Begin"], ""
                            ) < howlong[val1th]["WhenLast"]:
                                howlong[val1th]["WhenLast"] = numberOfDays(
                                    val1["End"], ""
                                )
                for item in TheList['p']:
                    if TheList['p'][item]["Rot"] == rotation:
                        if item not in howlong:
                            howlong[item] = {
                                "HowMany": 0,
                                "HowLong": 0,
                                "WhenLast": float('Inf')
                            }
                vvalues = pd.DataFrame(howlong)
                print(
                    tabulate.tabulate(vvalues.T.sort_values(
                        by=sortedBy,
                        ascending=True
                    ),
                             tablefmt="psql",
                             headers='keys'))
        elif thing == "Ink":
            print("**"+thing+"**")
            counterek = []
            howlong = {}
            howlong = {}
            rotations = ["Bottle", "Sample"]
            for rotation in rotations[::-1]:
                howlong = {}
                print("*"+rotation+"*")
                for item in theList:
                    val1 = theList[item]
                    val1th = theList[item][thing]
                    cond1a = rotation == "Bottle"
                    cond1b = val1th[0:3] != "(s)"
                    cond1c = TheList['i'][val1th]["UsedUp"] == "No"
                    cond2 = (rotation == "Sample") and (val1th[0:3] == "(s)")
                    if (cond1a and cond1b and cond1c) or cond2:
                        if val1th not in howlong:
                            howlong[val1th] = {
                                "HowMany": 1,
                                "HowLong": numberOfDays(
                                    val1["Begin"],
                                    val1["End"]
                                ),
                                "WhenLast": numberOfDays(
                                    val1["End"],
                                    ""
                                    )
                            }
                        else:
                            howlong[val1th]["HowMany"] += 1
                            howlong[val1th]["HowLong"] += numberOfDays(
                                val1["Begin"], val1["End"]
                                )
                            if numberOfDays(val1["Begin"], "") < howlong[val1th]["WhenLast"]:
                                howlong[val1th]["WhenLast"] = numberOfDays(
                                    val1["End"], ""
                                )
                print(
                    tabulate.tabulate(
                        pd.DataFrame(howlong).T.sort_values(
                            by=sortedBy, ascending=True
                        ),
                        tablefmt="psql",
                        headers='keys'
                    )
                )
        elif thing == "Nib":
            print("**"+thing+"**")
            counterek = []
            for item in theList:
                counterek.append(theList[item][thing])
                Counterek = collections.Counter(counterek)
            printing(Counterek)
            print("**"+"Nib materials"+"**")
            counterek = []
            for item in theList:
                if theList[item][thing].split(" ")[0] == "14k":
                    counterek.append("14k")
                elif theList[item][thing].split(" ")[0] == "23k":
                    counterek.append("23k palladium")
                else:
                    counterek.append("steel")
                Counterek = collections.Counter(counterek)
            printing(Counterek)
        elif thing == "Model":
            print("**"+thing+"**")
            counterek = []
            for item in theList:
                counterek.append(theList[item][thing].split(" ")[0])
                Counterek = collections.Counter(counterek)
            printing(Counterek)
        else:
            print("**"+thing+"**")
            counterek = []
            for item in theList:
                counterek.append(theList[item][thing])
                Counterek = collections.Counter(counterek)
            printing(Counterek)

    print("***Summary of", coDict[val], "collection***")
    summingdict = {'p': ["Bought", "Brand", "Model", "Class", "Filling",
                         "From", "Nationality", "Price"],
                   'i': ['Brand', 'Bought', 'Color', 'ColorClass', 'Vol',
                         'BoP', 'From', 'Price'],
                   'u': ['Pen', 'Ink', 'Nib']}
    try:
        what = sys.argv[2]
        if len(sys.argv) > 3:
            sortedBy = sys.argv[3]
        else:
            sortedBy = "WhenLast"
    except:
        what = "All"
    if what in summingdict[val]:
        DoTheThing(what)
    elif what == "All" or what == "all":
        for i in summingdict[val]:
            DoTheThing(i)
    else:
        print("Not a valid request")


def ParsingInput(x):
    if x[0] == "e":
        DoTheExporting()
    elif x[0] == "q":
        DoTheExporting()
        sys.exit()
    elif x[0] == "a":
        DoTheAdding(x[1])
    elif x[0] == "c":
        DoTheChanging(x[1])
    elif x[0] == "l":
        DoTheListing(x[1])
    elif x[0] == "s":
        DoTheSumming(x[1])
    else:
        print("Invalid command")


def main():
    DoTheImporting('p')
    DoTheImporting('i')
    DoTheImporting('u')
    try:
        ParsingInput(sys.argv[1])
    except IndexError:
        print("#################")
        print("Welcome to pypen!")
        while True:
            print("#################\n")
            x = input("""You basically should be:

            (e)xporting -- exports json files
            (q)uitting -- exports the database and quits the program
            (l)isting, (a)dding, (c)hanging:
            X: (p)ens, (i)nks, (u)sages

            Note: important usage functions are:
            (ab): add beginnig of usage of a pen for today
            (ae): add done pen for today.
            \n""")
            ParsingInput(x)
    sys.exit()


if __name__ == "__main__":
    main()
