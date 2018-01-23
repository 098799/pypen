#!/usr/bin/python3.5
# I want my program to make Gantt charts
import json
from sys import exit, argv
from collections import Counter
import pandas as pd
from tabulate import tabulate
from datetime import date

PenTuple = []
InkTuple = [] 
UsageTuple = []

class Pen:
    """A class containing all of the information about a pen"""
    def __init__(self, x):
        self.Name = x

class Ink:
    """A class containing all of the information about an ink"""
    def __init__(self, x):
        self.Name = x

class Usage:
    """A class containing all of the information about a usage"""
    def __init__(self, x):
        self.Name = x

def DoTheImporting(item):
    filename = {"p": "pens.json", "i": "inks.json", "u":"usage.json"}
    with open(filename[item], 'r') as infile:
        if item == "p":
            global PenList
            PenList = json.load(infile)
            for i in PenList["Jinhao250"].keys():
                PenTuple.append(i)
            pens = {k: Pen(k) for k in PenList}
            for k in PenList:
                pens[k].Bought = PenList[k]["Bought"]
                pens[k].Brand = PenList[k]["Brand"]
                pens[k].Class = PenList[k]["Class"]
                pens[k].Filling = PenList[k]["Filling"]
                pens[k].From = PenList[k]["From"]
                pens[k].Model = PenList[k]["Model"]
                pens[k].Nationality = PenList[k]["Nationality"]
                pens[k].Out = PenList[k]["Out"]
                pens[k].OurPr = PenList[k]["OutPr"]
                pens[k].Price = PenList[k]["Price"]
                pens[k].Rot = PenList[k]["Rot"]
        if item == "i":
            global InkList
            InkList = json.load(infile)
            for i in InkList["DeAtramentisAubergine"].keys():
                InkTuple.append(i)
            inks = {k: Ink(k) for k in InkList}
            for k in InkList:
                inks[k].BoP = InkList[k]["BoP"]
                inks[k].Bought = InkList[k]["Bought"]
                inks[k].Brand = InkList[k]["Brand"]
                inks[k].Color = InkList[k]["Color"]
                inks[k].From = InkList[k]["From"]
                inks[k].Name = InkList[k]["Name"]
                inks[k].Price = InkList[k]["Price"]
                inks[k].UsedUp = InkList[k]["UsedUp"]
                inks[k].Vol = InkList[k]["Vol"]
        if item == "u":
            global UsageList
            UsageList = json.load(infile)
            for i in UsageList["Baoer05122.03.2017"].keys():
                UsageTuple.append(i)
            usages = {k: Usage(k) for k in UsageList}
            for k in UsageList:
                usages[k].Begin = UsageList[k]["Begin"]
                usages[k].End = UsageList[k]["End"]
                usages[k].Ink = UsageList[k]["Ink"]
                usages[k].Nib = UsageList[k]["Nib"]
                usages[k].Pen = UsageList[k]["Pen"]


def DoTheExporting():
    with open('pens.json', 'w') as outfile:1
        json.dump(PenList, outfile, indent=4, sort_keys=True)
    with open('inks.json', 'w') as outfile:
        json.dump(InkList, outfile, indent=4, sort_keys=True)
    with open('usage.json', 'w') as outfile:
        json.dump(UsageList, outfile, indent=4, sort_keys=True)


def DoTheAdding(item):
    if item == "p":
        brand = input("Pen brand?\n")
        model = input("Pen model?\n")
        penid = brand+model
        penid = penid.replace(" ", "")
        price = eval(input("Price?\n"))
        boughtmonth, boughtyear = eval(input("Bought in (month,year)?\n"))
        bought = str(boughtyear)+"-"+str(boughtmonth).zfill(2)
        boughtfrom = input("Bought from?\n")
        fillingsystem = input("Filling system? enter for c/c, (p) for piston, \
        (l) for lever, (s) for squeeze, (pl) for plunger/vacuum filler \n")
        if fillingsystem == '':
            fillingsystem = "c/c"
        elif fillingsystem == 'piston' or fillingsystem == 'p':
            fillingsystem = "Piston"
        elif fillingsystem == 'l':
            fillingsystem = "Lever"
        elif fillingsystem == 's':
            fillingsystem = "Squeeze"
        elif fillingsystem == 'pl':
            fillingsystem = "Plunger"
        clas = input("Class? Enter for modern, else for vintage \n")
        if clas == '':
            clas = "Modern"
        else:
            clas = "Vintage"
        nation = input("Nationality? \n")
        rotation = input("Which Rotation? 1, 2 or Not \n")
        PenList[penid] = {'Brand': brand, 'Model': model, 'Price': price,
                          'Bought': bought, 'From': boughtfrom,
                          'Filling': fillingsystem, 'Class': clas,
                          'Nationality': nation, 'Out': "No", 'OutPr': 0,
                          'Rot': rotation}

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
        InkList[inkid] = {'Brand': brand, 'Name': name, 'Color': color,
                          'Vol': volume, "BoP": bop, 'Bought': bought,
                          'From': gf, 'Price': price}
    if item == 'u':
        AddBeginningOfUsage()
    if item == 'd':
        AddEndOfUsage()


def DoTheChanging(val):
    valDict = {'p': (PenList, PenTuple), 'i': (InkList, InkTuple)}
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
        valDict[val][0][association[int(whichpen)]][valDict[val][1][int(which)]]
          , ")")
    reading = input()
    if reading == '':
        pass
    else:
        valDict[val][0][association[int(whichpen)]][valDict[val][1][int(which)]] = reading


def DoTheListing(val):
    valDict = {'p': (PenList, PenTuple),
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
                    if ("-" in str(valDict[val][0][j][(i.split(".GT."))[0]])):
                        if float(valDict[val][0][j][(i.split(".GT."))[0]].split("-")[0])>float((i.split(".GT."))[1]):
                            overnewdict[j]=valDict[val][0][j]
                    else:
                        if float((valDict[val][0][j][(i.split(".GT."))[0]]))>float((i.split(".GT."))[1]):
                            overnewdict[j]=valDict[val][0][j]
                bai[number]=(i.split(".GT."))[0]
                newdict = overnewdict
        for number, i in enumerate(bai):
            if ".LT." in i:
                overnewdict = {}
                for j in newdict:
                    if ("-" in str(valDict[val][0][j][(i.split(".LT."))[0]])):
                        if float(valDict[val][0][j][(i.split(".LT."))[0]].split("-")[0])<float((i.split(".GT."))[1]):
                            overnewdict[j]=valDict[val][0][j]
                    else:
                        if float((valDict[val][0][j][(i.split(".LT."))[0]]))<float((i.split(".LT."))[1]):
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
    begy = '2018'
    begyq = input("When inked up? year (2018 as a default) ")
    if not (begyq == ''):
        begy = begyq
    endd = input("When inked down? day   ")
    endm = input("When inked down? month ")
    endy = '2018'
    endyq = input("When inked down? year (2018 as a default) ")
    if not (endyq == ''):
        endy = endyq
    usageid = whichpen+str(begd)+"."+str(begm)+"."+str(begy)
    UsageList[usageid] = {'Pen': whichpen, 'Nib': whichnib, 'Ink': whichink,
                          'Begin': str(begy)+"-"+str(begm).zfill(2)+"-"+str(begd).zfill(2),
                          'End': str(endy)+"-"+str(endm).zfill(2)+"-"+str(endd).zfill(2)}


def AddBeginningOfUsage():
    print("Which pen has been used?\n")
    association = {}
    for numb, item in enumerate(sorted(PenList)):
        association[numb] = item
        print(numb, item)
    whichpen = association[int(input())]
    whichnib = input("What sized nib? ")
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
    begd = input("When inked up? day (enter for today)   ")
    if begd == "":
        begd = date.today().day
        begm = date.today().month
        begy = date.today().year
    else:
        begm = input("When inked up? month ")
        begy = '2018'
        begyq = input("When inked up? year (2018 as a default) ")
        if not (begyq == ''):
            begy = begyq
    usageid = whichpen+str(begd)+"."+str(begm)+"."+str(begy)
    UsageList[usageid] = {'Pen': whichpen, 'Nib': whichnib, 'Ink': whichink,
                          'Begin': str(begy)+"-"+str(begm).zfill(2)+"-"+str(begd).zfill(2),
                          'End': ""}

def AddEndOfUsage():
    print("We're adding an end date to one of those pens:")
    association = {}
    i = 0
    for item in UsageList:
        if UsageList[item]["End"] == "":
            i += 1
            print(i, item)
            association[i] = item
    whichusage = association[int(input("Which one?"))]
    begd = input("When inked down? day (enter for today)   ")
    if begd == "":
        begd = date.today().day
        begm = date.today().month
        begy = date.today().year
    else:
        begm = input("When inked down? month ")
        begy = '2018'
        begyq = input("When inked down? year (2018 as a default) ")
        if not (begyq == ''):
            begy = begyq
    UsageList[whichusage]["End"] = str(begy)+"-"+str(begm).zfill(2)+"-"+str(begd).zfill(2)
    

def DoTheSumming(val):
    valDict = {'p': (PenList, PenTuple),
               'i': (InkList, InkTuple), 'u': (UsageList, UsageTuple)}
    coDict = {'p': "pen", 'u': "usage", 'i': "ink"}
    if val == '':
        val = 'p'

    def printing(a):
        print(tabulate(pd.DataFrame(a.most_common()), tablefmt="psql"))

    def numberOfDays(a,b):
        if a == "":
            return (date.today()-date.today()).days
        if b == "":
            return (date.today()-date(*[int(i) for i in a.split("-")])).days
        else:
            return (date(*[int(i) for i in b.split("-")])-date(*[int(i) for i in a.split("-")])).days
        
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
            print("Wasted", suma, "PLN on stupid", coDict[val]+'s. By year:')
            sumapre  = 0
            suma2015 = 0
            suma2016 = 0
            suma2017 = 0
            for item in valDict[val][0]:
                dateofbuying=int(valDict[val][0][item]["Bought"].split("-")[0])
                if dateofbuying<2015:
                    sumapre += valDict[val][0][item]["Price"]
                elif dateofbuying<2016:
                    suma2015 += valDict[val][0][item]["Price"]
                elif dateofbuying<2017:
                    suma2016 += valDict[val][0][item]["Price"]
                elif dateofbuying<2018:
                    suma2017 += valDict[val][0][item]["Price"]
            print("pre2015:",sumapre)
            print("   2015:",suma2015)
            print("   2016:",suma2016)
            print("   2017:",suma2017)
        elif thing == "ColorClass":
            print("**ColorClass**")
            itemziocounter = []
            itemzioDict = {'Brown': 'Brown', 'Black': 'Black', 'Green': 'Green',
                           'Red': 'Red', 'Purple': 'Purple',
                           'Blue Black': 'Blue', 'Blue': 'Blue',
                           'Turquoise': 'Blue', 'Pink': 'Pink',
                           'Orange': 'Orange', 'Royal Blue': 'Blue',
                           'Grey': 'Grey', 'Teal': 'Teal'}
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
            for rotation in sorted(rotations)[::-1]:
                howlong = {}
                print("*Rotation number "+rotation+"*")
                for item in searchlist:
                    val1 = searchlist[item]
                    val1th = searchlist[item][thing]
                    if PenList[val1th]["Rot"] == rotation:
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
                vvalues = pd.DataFrame(howlong)
                print(
                    tabulate(vvalues.T.sort_values(
                        by="WhenLast",
                        ascending=True
                    ),
                             tablefmt="psql",
                             headers='keys'))
        elif thing == "Ink":
            print("**"+thing+"**")
            counterek = []
            howlong = {}
            searchlist = valDict[val][0]
            howlong = {}
            rotations = ["Bottle", "Sample"]
            for rotation in rotations[::-1]:
                howlong = {}
                print("*"+rotation+"*")
                for item in searchlist:
                    val1 = searchlist[item]
                    val1th = searchlist[item][thing]
                    if rotation == "Bottle":
                        if val1th[0:3] != "(s)":
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
                    elif rotation == "Sample":
                        if val1th[0:3] == "(s)":
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
                    tabulate(
                        pd.DataFrame(howlong).T.sort_values(
                            by="WhenLast", ascending=True
                        ),
                        tablefmt="psql",
                        headers='keys'
                    )
                )
        else:
            print("**"+thing+"**")
            counterek = []
            for item in valDict[val][0]:
                counterek.append(valDict[val][0][item][thing])
                Counterek = Counter(counterek)
            printing(Counterek)
            print("**"+"Nib materials"+"**")
            counterek = []
            for item in valDict[val][0]:
                if valDict[val][0][item]["Nib"].split(" ")[0] == "14k":
                    counterek.append("14k")
                elif valDict[val][0][item]["Nib"].split(" ")[0] == "23k":
                    counterek.append("23k palladium")
                else:
                    counterek.append("steel")
                Counterek = Counter(counterek)
            printing(Counterek)
            
    print("***Summary of", coDict[val], "collection***")
    summingdict = {'p': ["Bought", "Brand", "Model", "Class", "Filling", "From", "Nationality", "Price"],
                   'i': ['Brand', 'Bought', 'Color', 'ColorClass', 'Vol', 'BoP', 'From', 'Price'],
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
    print(pens["Lamy2000"])
    exit()
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
            x = input("""You basically should be:

(e)xporting -- exports json files
(q)uitting -- exports the database and quits the program
(l)isting, (a)dding, (c)hanging:
        X: (p)ens, (i)nks, (u)sages
\n""")
            ParsingInput(x)
    exit()


if __name__ == "__main__":
    main()
