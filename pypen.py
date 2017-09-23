#!/usr/bin/python3.5
# I want my program to make Gantt charts
import json
from sys import exit, argv
from collections import Counter
import pandas as pd
from tabulate import tabulate
from datetime import date

PenTuple = ('Brand', 'Model', 'Price', 'Bought'
            'From', 'Filling', 'Nationality',
            'Class')
# NibTuple = ('Brand', 'Size', 'Width', 'Stubness', 'Price', 'BoughtMonth', 'BoughtYear',
#             'Plating', 'Material')
InkTuple = ('Brand', 'Bought', 'Name', 'Color', 'Vol',
            'BoP', 'From', 'Price')
UsageTuple = ('Pen', 'Nib', 'Ink', 'Begin', 'End')


def DoTheImporting(item):
    if item == "p":
        with open('pens.json', 'r') as infile:
            global PenList
            PenList = json.load(infile)
    # if item == "n":
    #     with open('nibs.json', 'r') as infile:
    #         global NibList
    #         NibList = json.load(infile)
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
    # with open('nibs.json', 'w') as outfile:
    #     json.dump(NibList, outfile)
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
        # NibClasses = []
        # for i in PenList:
        #     item = PenList[i]["Nibs"]
        #     if item not in NibClasses:
        #         NibClasses.append(item)
        # for i, val in enumerate(NibClasses):
        #     print(i,val)
        # size = eval(input("""Nib Size? choose number from available above ^"""))
        boughtmonth, boughtyear = eval(input("Bought in (month,year)?\n"))
        bought = str(boughtyear)+"-"+str(boughtmonth).zfill(2)
        boughtfrom = input("Bought from?\n")
        fillingsystem = input("Filling system? enter for c/c, (p) for piston, \
(l) for lever, (s) for squeeze \n")
        if fillingsystem == '':
            fillingsystem = "c/c"
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
        rotation = input("Which Rotation? 1, 2 or Not \n")
        # nibremovability = input("Nib removability? yes --default, or (n)o \n")
        # nibremovabilitydict = {'': 'Removable', 'n': 'Nonremovable'}
        PenList[penid] = {'Brand': brand, 'Model': model, 'Price': price, 'Bought': bought, 'From': boughtfrom,  # 'Nibs': NibClasses[size],
                          'Filling': fillingsystem, 'Class': clas, 'Nationality': nation, 'Out': "No", 'OutPr': 0, 'Rot': rotation}

    # if item == "n":
    #     brand = input("Nib Brand?\n")
    #     steelorgold = input("Steel or gold? (press enter for steel, else for 14k gold)\n")
    #     if steelorgold == '':
    #         steelorgold = 'Steel'
    #     else:
    #         steelorgold = '14k gold'
    #     NibClasses = []
    #     for i in PenList:
    #         item = PenList[i]["Nibs"]
    #         if item not in NibClasses:
    #             NibClasses.append(item)
    #     for i, val in enumerate(NibClasses):
    #         print(i, val)
    #     size = eval(input("""Nib Size? choose number from available above ^"""))
    #     width = input("Nib width? [1) xxf, 2) ef, 3) f, 4) m, 5) mk, 6) b, 7) bb, 8) 1.1, 9) 1.5), 10) 1.9 \n")
    #     widthDict = {'1': "XXF", "2": "EF", "3": "F", "4": "M", "5": "MK", "6": "B", "7": "BB", "8": "1.1", "9": "1.5", "10": "1.9"}
    #     stubness = input("Enter for round, 's' for stub, 'i' for italic, 'a' for architect \n")
    #     if stubness == '':
    #         stubness = "Round"
    #     elif stubness == 's':
    #         stubness = "Stub"
    #     elif stubness == 'i':
    #         stubness = "Italic"
    #     elif stubness == 'a':
    #         stubness = "Architect"
    #     price = input("Price if sold separately?\n")
    #     if price != '':
    #         boughtyear = input("Bought in (year) if separately?\n")
    #         boughtmonth = input("Bought in (month)\n")
    #         boughtfrom = input("Bought from?\n")
    #     else:
    #         boughtyear = ''
    #         boughtmonth = ''
    #         boughtfrom = ''
    #     color = input("Plating? a) rhodium, b) two-tone, c) gold, d) ruthenium \n")
    #     colorDict = {'a': 'Rhodium', 'b': 'Two-tone', 'c': 'Gold', 'd': 'Ruthenium'}
    #     nibid = brand+sizeDict[size]+widthDict[width]+stubness+colorDict[color]
    #     nibid = nibid.replace(" ", "")
    #     while nibid in NibList:
    #         nibid = nibid+'i'
    #     NibList[nibid] = {'Brand': brand, 'Size': NibClasses[size], 'Width': widthDict[width], 'Stubness': stubness, 'Price': price, 'BoughtMonth':
    # boughtmonth, 'BoughtYear': boughtyear, 'Plating': colorDict[color], 'Material': steelorgold}

    if item == "i":
        brand = input("Ink brand?\n")
        name = input("Ink name\n")
        inkid = brand+name
        inkid = inkid.replace(" ", "")
        color = input("Ink actual color\n")
        volume = input("Bottle capacity in ml?\n")
        if int(volume) > 3:
            bottle = "Bottle"
        else:
            bottle = "Sample"
        bop = input("Bought or present? enter for bought\n")
        if bop == '':
            bop = 'Bought'
        else:
            bop = 'Present'
        bm, by = eval(input("Bought in (month,year)?\n"))
        bought = str(by)+"-"+str(bm).zfill(2)
        gf = input("Got from?\n")
        price = eval(input("How much did it cost?\n"))
        InkList[inkid] = {'Brand': brand, 'Name': name, 'Color': color, 'BoS': bottle, 'Vol': volume, "BoP": bop, 'Bought': bought, 'From': gf, 'Price': price}
    if item == 'u':
        AddUsage()


def DoTheChanging(val):
    valDict = {'p': (PenList, PenTuple),  # 'n': (NibList, NibTuple),
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


def LegacyDoTheListing(vval):
    val = vval[0]
    valDict = {'p': (PenList, PenTuple),  # 'n': (NibList, NibTuple),
               'i': (InkList, InkTuple), 'u': (UsageList, UsageTuple)}
    # sortedby = valDict[val][1]
    # try: sortedby = vval[1]
    # except: pass
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
        print("| ", end='')
        print(str(n+1).ljust(2), end=' | ')
        for nn, items in enumerate(valDict[val][1]):
            try:
                print(str(valDict[val][0][item][items]).ljust(adjusting[nn]), end=' | ')
            except:
                pass
        print('')
    print("-"*(sum(adjusting)+6+len(valDict[val][1]*3)))


def DoTheListing(val):
    valDict = {'p': (PenList, PenTuple),  # 'n': (NibList, NibTuple),
               'i': (InkList, InkTuple), 'u': (UsageList, UsageTuple)}
    try:
        bai = argv[2:]
        newdict = valDict[val][0]
        for number, i in enumerate(bai):
            if "=" in i:
                overnewdict = {}
                for j in newdict:
                    if ("-" in valDict[val][0][j][(i.split("="))[0]]):
                        if int(valDict[val][0][j][(i.split("="))[0]].split("-")[0])==int((i.split("="))[1]):
                            overnewdict[j]=valDict[val][0][j]
                    else:
                        if valDict[val][0][j][(i.split("="))[0]]==(i.split("="))[1]:
                            overnewdict[j]=valDict[val][0][j]
                bai[number]=(i.split("="))[0]
                newdict = overnewdict
        for number, i in enumerate(bai):
            if ".GT." in i:
                overnewdict = {}
                for j in newdict:
                    if ("-" in valDict[val][0][j][(i.split(".GT."))[0]]):
                        if float(valDict[val][0][j][(i.split(".GT."))[0]].split("-")[0])>float((i.split(".GT."))[1]):
                            overnewdict[j]=valDict[val][0][j]
                    else:
                        if float((valDict[val][0][j][(i.split(".GT."))[0]]).split("-"))>float((i.split(".GT."))[1]):
                            overnewdict[j]=valDict[val][0][j]
                bai[number]=(i.split(".GT."))[0]
                newdict = overnewdict
        for number, i in enumerate(bai):
            if ".LT." in i:
                overnewdict = {}
                for j in newdict:
                    if ("-" in valDict[val][0][j][(i.split(".LT."))[0]]):
                        if float(valDict[val][0][j][(i.split(".LT."))[0]].split("-")[0])<float((i.split(".LT."))[1]):
                            overnewdict[j]=valDict[val][0][j]
                    else:
                        if float((valDict[val][0][j][(i.split(".LT."))[0]]).split("-"))<float((i.split(".LT."))[1]):
                            overnewdict[j]=valDict[val][0][j]
                bai[number]=(i.split(".LT."))[0]
                newdict = overnewdict
        # for number, j in enumerate(bai):
        #     if j == ".":
        #         for numberre, i in enumerate(sorted(newdict)):
        #             newdict[i][".lp"] = numberre+1
        #         print(bai)
        #         del bai[number]
        DF = pd.DataFrame.from_dict(newdict).T
        formatt = "psql"
        dai = []
        for i in DF.axes[1]:
            dai.append(i)
        if "-All" not in bai:
            bai.append("-All")
        for item in bai:
            if item == "-All":
                dai = []
                bai.remove("-All")
                break
            else:
                dai.remove(item)
        howtoascend = True
        if bai == "Date":
            bai = "Bought"
        if dai != []:
            for i in dai:
                DF = DF.drop(i, 1)
        DF=DF.sort_values(by=bai, ascending=howtoascend)
        DF=DF.reset_index()
        DF.index=range(1,len(DF.index)+1)
        print(tabulate(DF, headers='keys', tablefmt=formatt))
    except:
        DF = pd.DataFrame.from_dict(valDict[val][0]).T
        formatt = "psql"
        DF=DF.reset_index()
        DF.index=range(1,len(DF.index)+1)
        print(tabulate(DF, headers='keys', tablefmt=formatt))
        # nice formats: pipe, psql, rst


def AddUsage():
    print("Which pen has been used?\n")
    association = {}
    for numb, item in enumerate(sorted(PenList)):
        association[numb] = item
        print(numb, item)
    whichpen = association[int(input())]
    whichnib = input("What sized nib? ")
    # if PenList[whichpen]["NibRemove"] == "Nonremovable":
    #     whichnib = PenList[whichpen]["OriginalNib"]
    # else:
    #     association = {}
    #     for numb, item in enumerate(sorted(NibList)):
    #         association[str(numb)] = item
    #         print(numb, item)
    #     try:
    #         orig = PenList[whichpen]["OriginalNib"]
    #         print("Which nib? (enter for original, that is",orig,")\n")
    #         association['']=orig
    #     except:
    #         print("Which nib has been used?\n")
    #     whichnib = association[input()]
    print("Which ink has been used? enter for ink sample \n")
    association = {}
    for numb, item in enumerate(sorted(InkList)):
        association[numb] = item
        print(numb, item)
    inkzi = input()
    if inkzi == "":
        inkzii = input("Write down the name of the sample ")
        whichink = "(s) "+inkzii
    else:
        whichink = association[int(inkzi)]
    begd = input("When inked up? day   ")
    begm = input("When inked up? month ")
    begy = '2017'
    begyq = input("When inked up? year (2017 as a default) ")
    if not (begyq == ''):
        begy = begyq
    endd = input("When inked down? day   ")
    endm = input("When inked down? month ")
    endy = '2017'
    endyq = input("When inked down? year (2017 as a default) ")
    if not (endyq == ''):
        endy = endyq
    usageid = whichpen+str(begd)+"."+str(begm)+"."+str(begy)
    UsageList[usageid] = {'Pen': whichpen, 'Nib': whichnib, 'Ink': whichink,
                          'Begin': str(begy)+"-"+str(begm).zfill(2)+"-"+str(begd).zfill(2),
                          'End': str(endy)+"-"+str(endm).zfill(2)+"-"+str(endd).zfill(2)}


def DoTheSumming(val):
    valDict = {'p': (PenList, PenTuple),
               'i': (InkList, InkTuple), 'u': (UsageList, UsageTuple)}
    coDict = {'p': "pen", 'u': "usage", 'i': "ink"}
    if val == '':
        val = 'p'

    def printing(a):
        print(tabulate(pd.DataFrame(a.most_common()), tablefmt="psql"))

    def DoTheThing(thing):
        dzis = date.today()
        if thing == "Bought":
            print("**Bought**")
            boughtcounter = []
            for item in valDict[val][0]:
                boughtcounter.append(valDict[val][0][item]["Bought"].split("-")[0])
            boughtCounter = Counter(boughtcounter)
            printing(boughtCounter)
        elif thing == "Price":
            print("**Price**")
            suma = 0
            for item in valDict[val][0]:
                suma += valDict[val][0][item]["Price"]
            print("Wasted", suma, "PLN on stupid", coDict[val]+'s')
        elif thing == "ColorClass":
            print("**ColorClass**")
            itemziocounter = []
            itemzioDict = {'Brown': 'Brown', 'Black': 'Black', 'Green': 'Green', 'Red': 'Red', 'Purple': 'Purple', 'Blue Black': 'Blue', 'Blue': 'Blue',
                           'Turquoise': 'Blue', 'Pink': 'Pink', 'Orange': 'Orange', 'Royal Blue': 'Blue', 'Grey': 'Grey', 'Teal': 'Teal'}
            for item in valDict[val][0]:
                itemzio = valDict[val][0][item]['Color']
                itemziocounter.append(itemzioDict[itemzio])
            itemzioCounter = Counter(itemziocounter)
            printing(itemzioCounter)
        elif thing == "Pen":
            print("**"+thing+"**")
            counterek = []
            howlong = {}
            searchlist = valDict[val][0]
            rotations = []
            for i in PenList:
                val2 = PenList[i]["Rot"]
                if val2 not in rotations:
                    rotations.append(val2)
            rotations.remove("Broken")
            for rotation in sorted(rotations):
                howlong = {}
                print("*Rotation number "+rotation+"*")
                for item in searchlist:
                    val1 = searchlist[item]
                    #print(val1)
                    #print("lol",val1)
                    if PenList[val1[thing]]["Rot"] == rotation:
                        #print("lal",val1)
                        #print((dzis-date(*[int(i) for i in val1["End"].split("-")])).days)
                        if val1[thing] not in howlong:
                            howlong[val1[thing]] = {"HowMany": 1, "HowLong": (date(*[int(i) for i in val1["End"].split("-")])-date(*[int(i) for i in val1["Begin"].split("-")])).days,
                                                    "WhenLast": (dzis-date(*[int(i) for i in val1["End"].split("-")])).days}
                        else:
                            howlong[val1[thing]]["HowMany"] += 1
                            howlong[val1[thing]]["HowLong"] += (date(*[int(i) for i in val1["End"].split("-")])-date(*[int(i) for i in val1["Begin"].split("-")])).days
                            if (dzis-date(*[int(i) for i in val1["End"].split("-")])).days < howlong[val1[thing]]["WhenLast"]:
                                howlong[val1[thing]]["WhenLast"] = (dzis-date(*[int(i) for i in val1["End"].split("-")])).days
                vvalues = pd.DataFrame(howlong)
                print(tabulate(vvalues.T.sort_values(by="WhenLast", ascending=True), tablefmt="psql", headers='keys'))
        elif thing == "Ink":
            print("**"+thing+"**")
            counterek = []
            howlong = {}
            searchlist = valDict[val][0]
            howlong = {}
            rotations = ["Bottle", "Sample"]
            for rotation in rotations:
                howlong = {}
                print("*"+rotation+"*")
                for item in searchlist:
                    val1 = searchlist[item]
                    if rotation == "Bottle":
                        if val1[thing][0:3] != "(s)":
                            if val1[thing] not in howlong:
                                howlong[val1[thing]] = {"HowMany": 1, "HowLong": (date(*[int(i) for i in val1["End"].split("-")])-date(*[int(i) for i in val1["Begin"].split("-")])).days,
                                                        "WhenLast": (dzis-date(*[int(i) for i in val1["End"].split("-")])).days}
                            else:
                                howlong[val1[thing]]["HowMany"] += 1
                                howlong[val1[thing]]["HowLong"] += (date(*[int(i) for i in val1["End"].split("-")])-date(*[int(i) for i in val1["Begin"].split("-")])).days
                                if (dzis-date(*[int(i) for i in val1["End"].split("-")])).days < howlong[val1[thing]]["WhenLast"]:
                                    howlong[val1[thing]]["WhenLast"] = (dzis-date(*[int(i) for i in val1["End"].split("-")])).days
                    elif rotation == "Sample":
                        if val1[thing][0:3] == "(s)":
                            if val1[thing] not in howlong:
                                howlong[val1[thing]] = {"HowMany": 1, "HowLong": (date(*[int(i) for i in val1["End"].split("-")])-date(*[int(i) for i in val1["Begin"].split("-")])).days,
                                                        "WhenLast": (dzis-date(*[int(i) for i in val1["End"].split("-")])).days}
                            else:
                                howlong[val1[thing]]["HowMany"] += 1
                                howlong[val1[thing]]["HowLong"] += (date(*[int(i) for i in val1["End"].split("-")])-date(*[int(i) for i in val1["Begin"].split("-")])).days
                                if (dzis-date(*[int(i) for i in val1["End"].split("-")])).days < howlong[val1[thing]]["WhenLast"]:
                                    howlong[val1[thing]]["WhenLast"] = (dzis-date(*[int(i) for i in val1["End"].split("-")])).days
                print(tabulate(pd.DataFrame(howlong).T.sort_values(by="WhenLast", ascending=True), tablefmt="psql", headers='keys'))
        else:
            print("**"+thing+"**")
            counterek = []
            for item in valDict[val][0]:
                counterek.append(valDict[val][0][item][thing])
                Counterek = Counter(counterek)
            printing(Counterek)

    print("***Summary of", coDict[val], "collection***")
    summingdict = {'p': ["Bought", "Brand", "Model", "Class", "Filling", "From", "Nationality", "Price"],
                   'i': ['Brand', 'Bought', 'Color', 'ColorClass', 'BoS', 'Vol', 'BoP', 'From', 'Price'],
                   'u': ['Pen', 'Ink', 'Nib']}
    try:
        what = argv[2]
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
        exit()
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
    # DoTheImporting('n')
    DoTheImporting('i')
    DoTheImporting('u')
    if len(argv) > 1:
        x = argv[1]
        ParsingInput(x)
    else:
        print("#################")
        print("Welcome to pypen!")
        while True:
            print("#################\n")
            x = input("""What do you want to do?
Possible options are:

(e)xport -- exports json files
(q)uit -- exports the database and quits the program
(lX Y) list:
        X: (p)ens, (n)ibs, (i)nks, (u)sages
        (additional) Y: Brand, Class, Model, Nationality, Nibs, Price, Date etc.
(aX) add
(cX) change
\n""")
            ParsingInput(x)
    exit()


if __name__ == "__main__":
    main()
