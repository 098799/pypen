#!/usr/bin/env python3
# I want my program to make Gantt charts
import collections
import datetime
import json
import sys

import pandas
import tabulate


WORKING_DIR = "/home/grining/Dropbox/pens/pypen/"
PROGRAM_DIR = "pypen/"
FILE_DIR = WORKING_DIR + PROGRAM_DIR
TEST_DIR = "tests/"

PEN_FIELDS = ["bought", "brand", "class", "filling", "from", "model",
              "nationality", "out", "price_out", "price", "rot"]
PEN_FIELDS = [field.lower() for field in PEN_FIELDS]

INK_FIELDS = ["bought", "brand", "color", "from", "how", "name", "price", "used_up", "vol"]
# INK_FIELDS = [field.lower() for field in INK_FIELDS]

USAGE_FIELDS = ["begin", "end", "ink", "nib", "pen"]
# USAGE_FIELDS = [field.lower() for field in USAGE_FIELDS]

BIG_LIST = {'p': {}, 'i': {}, 'u': {}}
BIG_TUPLE = {'p': [], 'i': [], 'u': []}

FILE_NAME = {
    "p": "pens.json",
    "i": "inks.json",
    "u": "usage.json",
}

EXAMPLE = {
    'p': "Jinhao250",
    'i': "DeAtramentisAubergine",
    'u': "Baoer05122.03.2017",
}


def import_from_file(what):
    """Fill up BIG_LIST and BIG_TUPLE globals."""
    def import_file(what):
        BIG_LIST[what] = json.load(infile)

        for i in BIG_LIST[what][EXAMPLE[what]].keys():
            BIG_TUPLE[what].append(i)

        BIG_TUPLE[what].sort()

    with open(FILE_NAME[what], 'r') as infile:
        import_file(what)


def export_to_file():
    for which in BIG_LIST.keys():
        with open(FILE_NAME[which], 'w') as outfile:
            json.dump(BIG_LIST[which], outfile, indent=4, sort_keys=True)


def add_item(item):
    def add_core_item(item):
        temporary = {}

        for char in BIG_TUPLE[item]:
            print("\n " + "-"*len(char), "\n", char, "\n", "-"*len(char))
            association = []

            for pen in BIG_LIST[item]:
                val = BIG_LIST[item][pen][char]
                if val not in association:
                    association.append(val)

            association.sort()
            for number, thisitem in enumerate(association, 1):
                print(number, thisitem)
            print("or click enter to input yourself")
            thatInput = input("Which?")
            if thatInput == "":
                thatInput = input("Type here\n")
            else:
                thatInput = association[int(thatInput)-1]
            print(thatInput)
            temporary[char] = thatInput
    if item in ("p", "i", "u"):
        temporary = {}
        for char in BIG_TUPLE[item]:
            print("\n " + "-"*len(char), "\n", char, "\n", "-"*len(char))
            association = []
            for pen in BIG_LIST[item]:
                val = BIG_LIST[item][pen][char]
                if val not in association:
                    association.append(val)
            association.sort()
            for number, thisitem in enumerate(association, 1):
                print(number, thisitem)
            print("or click enter to input yourself")
            thatInput = input("Which?")
            if thatInput == "":
                thatInput = input("Type here\n")
            else:
                thatInput = association[int(thatInput)-1]
            print(thatInput)
            temporary[char] = thatInput
        if item == "p":
            penID = make_id(temporary["brand"], temporary["model"])
        elif item == "i":
            penID = make_id(temporary["brand"], temporary["name"])
        BIG_LIST[item][penID] = temporary
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


def change_item(item):
    print('')
    print("Which item do you want to change?")
    association = {}
    for numb, val in enumerate(sorted(BIG_LIST[item]), 1):
        association[numb] = val
        print(numb, val)
    whichpen = input()
    pen_id = association[int(whichpen)]
    print("Press the number of what you want to change:")
    for numb, val in enumerate(BIG_TUPLE[item], 1):
        print(numb, val)
    which = input()
    char_id = BIG_TUPLE[item][int(which)-1]
    print("To what are we changing it? (was:",
          BIG_LIST[item][pen_id][char_id],
          ")")
    reading = input()
    if reading == '':
        pass
    else:
        BIG_LIST[item][pen_id][char_id] = reading


# I stopped refactoring here, so go from here


def list_items(val):
    valDict = {'p': BIG_LIST['p'], 'i': BIG_LIST['i'], 'u': BIG_LIST['u']}

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
        DF = pandas.DataFrame.from_dict(theList).T
        howtoascend = True
        if by == "date":
            by = "bought"
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
            byWhat = ["brand"]
        for ink in valDict[val]:
            if valDict[val][ink]["used_up"] == "No":
                theList[ink] = valDict[val][ink]
            else:
                theUsedUpList[ink] = valDict[val][ink]
        print("\n** Used Up ***")
        insidesOfTheListing(theUsedUpList, byWhat, dropWhat)
        print("\n** In Rotation ***")
        dropWhat.append("used_up")
        insidesOfTheListing(theList, byWhat, dropWhat)
    elif val == "p":
        theList = {}
        theOutList = {}
        if byWhat == []:
            byWhat = ["brand"]
        for pen in valDict[val]:
            if valDict[val][pen]["rot"] not in ["Out", "Broken"]:
                theList[pen] = valDict[val][pen]
            else:
                theOutList[pen] = valDict[val][pen]
        print("\n** Left the rotation ***")
        insidesOfTheListing(theOutList, byWhat, dropWhat)
        print("\n** In Rotation ***")
        dropWhat.append("out")
        dropWhat.append("price_out")
        insidesOfTheListing(theList, byWhat, dropWhat)
    else:
        theList = valDict[val]
        if byWhat == []:
            byWhat = ["end"]
        insidesOfTheListing(theList, byWhat, dropWhat)


def AddUsage():
    print("Which pen has been used?\n")
    association = {}
    for numb, item in enumerate(sorted(BIG_LIST['p']), 1):
        association[numb] = item
        print(numb, item)
    whichpen = association[int(input())]
    whichnib = input("What sized nib? ")
    print("Which ink has been used? enter for ink sample \n")
    association = {}
    for numb, item in enumerate(sorted(BIG_LIST['i']), 1):
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
    BIG_LIST['u'][usageid] = {'pen': whichpen, 'nib': whichnib, 'ink': whichink,
                             'begin': dateFormat(begy, begm, begd),
                             'end': dateFormat(endy, endm, endd)}


def AddBeginningOfUsage(**kwargs):
    print("Which pen has been used?\n")
    association = {}
    for numb, item in enumerate(sorted(BIG_LIST['p']), 1):
        association[numb] = item
        print(numb, item)
    whichpen = association[int(input())]
    whichnib = input("What sized nib? ")
    print("Which ink has been used? enter for ink sample \n")
    association = {}
    for numb, item in enumerate(sorted(BIG_LIST['i']), 1):
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
    BIG_LIST['u'][usageid] = {'pen': whichpen, 'nib': whichnib, 'ink': whichink,
                             'begin': dateFormat(begy, begm, begd),
                             'end': ""}


def AddEndOfUsage(**kwargs):
    print("We're adding an end date to one of those pens:")
    association = {}
    i = 0
    for item in BIG_LIST['u']:
        if BIG_LIST['u'][item]["end"] == "":
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
    BIG_LIST['u'][whichusage]["end"] = dateFormat(begy, begm, begd)


def dateFormat(a, b, c):
    return str(a)+"-"+str(b).zfill(2)+"-"+str(c).zfill(2)


def sum_items(val='p'):
    valDict = {'p': BIG_LIST['p'], 'i': BIG_LIST['i'], 'u': BIG_LIST['u']}
    theList = valDict[val]
    coDict = {'p': "pen", 'u': "usage", 'i': "ink"}

    def printing(a):
        print(tabulate.tabulate(pandas.DataFrame(a.most_common()), tablefmt="psql"))

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
        if thing == "bought":
            print("**Bought**")
            boughtcounter = []
            for item in theList:
                boughtcounter.append(theList[item]["bought"].split("-")[0])
            boughtCounter = collections.Counter(boughtcounter)
            printing(boughtCounter)
        elif thing == "price":
            print("**Price**")
            suma = 0
            for item in theList:
                suma += theList[item]["price"]
            print("Wasted", suma, "PLN on stupid", coDict[val]+'s. By year:')
            sumapre = 0
            suma2015 = 0
            suma2016 = 0
            suma2017 = 0
            suma2018 = 0
            for item in theList:
                itemPrice = theList[item]["price"]
                dateofbuying = int(theList[item]["bought"].split("-")[0])
                if dateofbuying < 2015:
                    sumapre += itemPrice
                elif dateofbuying < 2016:
                    suma2015 += itemPrice
                elif dateofbuying < 2017:
                    suma2016 += itemPrice
                elif dateofbuying < 2018:
                    suma2017 += itemPrice
                elif dateofbuying < 2019:
                    suma2018 += itemPrice
            print("pre2015:", sumapre)
            print("   2015:", suma2015)
            print("   2016:", suma2016)
            print("   2017:", suma2017)
            print("   2018:", suma2018)
        elif thing == "colorclass":
            print("**ColorClass**")
            itemziocounter = []
            itemziDict = {'Brown': 'Brown', 'Black': 'Black', 'Green': 'Green',
                          'Red': 'Red', 'Purple': 'Purple',
                          'Blue Black': 'Blue', 'Blue': 'Blue',
                          'Turquoise': 'Blue', 'Pink': 'Pink',
                          'Orange': 'Orange', 'Royal Blue': 'Blue',
                          'Grey': 'Grey', 'Teal': 'Teal', "Burgundy": "Purple",
                          "Yellow": "Yellow"}
            for item in theList:
                itemzio = theList[item]['color']
                itemziocounter.append(itemziDict[itemzio])
            itemzioCounter = collections.Counter(itemziocounter)
            printing(itemzioCounter)
        elif thing == "pen":
            print("**"+thing+"**")
            counterek = []
            howlong = {}
            rotations = []
            for i in BIG_LIST['p']:
                val2 = BIG_LIST['p'][i]["rot"]
                if val2 not in rotations:
                    rotations.append(val2)
            rotations.remove("Broken")
            for rotation in sorted(rotations)[::-1]:
                howlong = {}
                print("*Rotation number "+rotation+"*")
                for item in theList:
                    val1 = theList[item]
                    val1th = theList[item][thing]
                    if BIG_LIST['p'][val1th]["rot"] == rotation:
                        if val1th not in howlong:
                            howlong[val1th] = {
                                "HowMany": 1,
                                "HowLong": numberOfDays(
                                    val1["begin"],
                                    val1["end"]
                                ),
                                "WhenLast": numberOfDays(
                                    val1["end"],
                                    ""
                                )
                            }
                        else:
                            howlong[val1th]["HowMany"] += 1
                            howlong[val1th]["HowLong"] += numberOfDays(
                                val1["begin"], val1["end"]
                            )
                            if numberOfDays(
                                    val1["begin"], ""
                            ) < howlong[val1th]["WhenLast"]:
                                howlong[val1th]["WhenLast"] = numberOfDays(
                                    val1["end"], ""
                                )
                for item in BIG_LIST['p']:
                    if BIG_LIST['p'][item]["rot"] == rotation:
                        if item not in howlong:
                            howlong[item] = {
                                "HowMany": 0,
                                "HowLong": 0,
                                "WhenLast": float('Inf')
                            }
                vvalues = pandas.DataFrame(howlong)
                vvalues = vvalues.T.sort_values(by=sortedBy, ascending=True)
                vvalues = vvalues.reset_index()
                vvalues.index = range(1, len(vvalues.index)+1)
                print(tabulate.tabulate(vvalues, headers='keys', tablefmt="psql"))
        elif thing == "ink":
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
                    if cond1a:
                        cond1b = val1th[0:3] != "(s)"
                        if cond1b:
                            cond1c = BIG_LIST['i'][val1th]["used_up"] == "No"
                    cond2 = (rotation == "Sample") and (val1th[0:3] == "(s)")
                    if (cond1a and cond1b and cond1c) or cond2:
                        if val1th not in howlong:
                            howlong[val1th] = {
                                "HowMany": 1,
                                "HowLong": numberOfDays(
                                    val1["begin"],
                                    val1["end"]
                                ),
                                "WhenLast": numberOfDays(
                                    val1["end"],
                                    ""
                                    )
                            }
                        else:
                            howlong[val1th]["HowMany"] += 1
                            howlong[val1th]["HowLong"] += numberOfDays(
                                val1["begin"], val1["end"]
                                )
                            if numberOfDays(val1["begin"], "") < howlong[val1th]["WhenLast"]:
                                howlong[val1th]["WhenLast"] = numberOfDays(
                                    val1["end"], ""
                                )
                vvalues = pandas.DataFrame(howlong)
                vvalues = vvalues.T.sort_values(by=sortedBy, ascending=True)
                vvalues = vvalues.reset_index()
                vvalues.index = range(1, len(vvalues.index)+1)
                print(tabulate.tabulate(vvalues, headers='keys', tablefmt="psql"))
        elif thing == "nib":
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
                elif theList[item][thing].split(" ")[0] == "18k":
                    counterek.append("18k")
                elif theList[item][thing].split(" ")[0] == "23k":
                    counterek.append("23k palladium")
                else:
                    counterek.append("steel")
                Counterek = collections.Counter(counterek)
            printing(Counterek)
        elif thing == "model":
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
    summingdict = {'p': ["bought", "brand", "model", "class", "filling",
                         "from", "nationality", "price"],
                   'i': ['brand', 'bought', 'color', 'colorclass', 'vol',
                         'how', 'from', 'price'],
                   'u': ['pen', 'ink', 'nib']}
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


def parse_input(x):
    if x[0] == "e":
        export_to_file()
    elif x[0] == "q":
        export_to_file()
        sys.exit()
    elif x[0] == "a":
        add_item(x[1])
    elif x[0] == "c":
        change_item(x[1])
    elif x[0] == "l":
        list_items(x[1])
    elif x[0] == "s":
        sum_items(x[1])
    else:
        print("Invalid command")


def main():
    import_from_file('p')
    import_from_file('i')
    import_from_file('u')
    try:
        parse_input(sys.argv[1])
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
            parse_input(x)
    sys.exit()


if __name__ == "__main__":
    main()
