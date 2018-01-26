#!/usr/bin/env python3
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

def DoTheImporting(item):
    filename = {"p": "pens.json", "i": "inks.json", "u": "usage.json"}
    with open(filename[item], 'r') as infile:
        if item == "p":
            global PenList, PenTuple
            PenList = json.load(infile)
            for i in PenList["Jinhao250"].keys():
                PenTuple.append(i)
            PenTuple.sort()
        if item == "i":
            global InkList, InkTuple
            InkList = json.load(infile)
            for i in InkList["DeAtramentisAubergine"].keys():
                InkTuple.append(i)
            InkTuple.sort()
        if item == "u":
            global UsageList, UsageTuple
            UsageList = json.load(infile)
            for i in UsageList["Baoer05122.03.2017"].keys():
                UsageTuple.append(i)
            UsageTuple.sort()


def DoTheExporting():
    with open('pens.json', 'w') as outfile:
        json.dump(PenList, outfile, indent=4, sort_keys=True)
    with open('inks.json', 'w') as outfile:
        json.dump(InkList, outfile, indent=4, sort_keys=True)
    with open('usage.json', 'w') as outfile:
        json.dump(UsageList, outfile, indent=4, sort_keys=True)


def DoTheAdding(item):
    valDict = {'p': PenList, 'i': InkList, 'u': UsageList}
    if item == "p":
        whatWeList = ValDict[item]
        for char in whatWeList:
            print("\n "+"-"*len(char),"\n",char,"\n","-"*len(char))
            association = []
            for pen in whatWeList:
                val = whatWeList[pen][char]
                if val not in association:
                    association.append(val)
            association.sort()
            for number, item in enumerate(association):
                print(number, item)
            print("or click enter to input yourself")
            thatInput = input("Which?")
            if thatInput == "":
                thatInput = input("Type here\n")
            else:
                thatInput = association[int(thatInput)]
            print(thatInput)
    if item == 'u':
        AddBeginningOfUsage()
    if item == 'd':
        AddEndOfUsage()
    if item == 'b':
        AddBeginningOfUsage(isItToday=True)
    if item == 'e':
        AddEndOfUsage(isItToday=True)


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


def AddBeginningOfUsage(**kwargs):
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
    if 'isItToday' in kwargs:
        begd = date.today().day
        begm = date.today().month
        begy = date.today().year
    else:
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

def AddEndOfUsage(**kwargs):
    print("We're adding an end date to one of those pens:")
    association = {}
    i = 0
    for item in UsageList:
        if UsageList[item]["End"] == "":
            i += 1
            print(i, item)
            association[i] = item
    whichusage = association[int(input("Which one?"))]
    if 'isItToday' in kwargs:
        begd = date.today().day
        begm = date.today().month
        begy = date.today().year
    else:
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
                           'Grey': 'Grey', 'Teal': 'Teal', "Burgundy": "Purple"}
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
        elif thing == "Nib":
            print("**"+thing+"**")
            counterek = []
            for item in valDict[val][0]:
                counterek.append(valDict[val][0][item][thing])
                Counterek = Counter(counterek)
            printing(Counterek)
            print("**"+"Nib materials"+"**")
            counterek = []
            for item in valDict[val][0]:
                if valDict[val][0][item][thing].split(" ")[0] == "14k":
                    counterek.append("14k")
                elif valDict[val][0][item][thing].split(" ")[0] == "23k":
                    counterek.append("23k palladium")
                else:
                    counterek.append("steel")
                Counterek = Counter(counterek)
            printing(Counterek)
        else:
            print("**"+thing+"**")
            counterek = []
            for item in valDict[val][0]:
                counterek.append(valDict[val][0][item][thing])
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

    Note: important usage functions are:
(ab): add beginnig of usage of a pen for today
(ae): add done pen for today.
\n""")
            ParsingInput(x)
    exit()


if __name__ == "__main__":
    main()
