from datetime import date
import json
from sys import argv, exit

class Pen():
    Lista = []
    def __init__(self, **entries):
        self.__dict__.update(entries)
        self.Lista.append(self)

class Nib():
    Lista = []
    def __init__(self, **entries):
        self.__dict__.update(entries)
        self.Lista.append(self)

class Ink():
    Lista = []
    def __init__(self, **entries):
        self.__dict__.update(entries)
        self.Lista.append(self)

def DoTheImporting(item):
    if item == "p":
        with open('pens.json', 'r') as infile:
            Lista = json.load(infile)
            global pioro
            pioro = {}
        for number, pen in enumerate(Lista):
            pioro[number] = Pen(**pen)
    elif item == "n":
        with open('nibs.json', 'r') as infile:
            Lista = json.load(infile)
            stalowka = {}
        for number, nib in enumerate(Lista):
            stalowka[number] = Nib(**nib)
    elif item == "i":
        with open('inks.json', 'r') as infile:
            Lista = json.load(infile)
            atrament = {}
        for number, ink in enumerate(Lista):
            atrament[number] = Ink(**ink)

def DoTheExporting():
    PenList = []
    NibList = []
    InkList = []
    for pen in Pen.Lista:
        PenList.append(pen.__dict__)
    for nib in Nib.Lista:
        NibList.append(nib.__dict__)
    for ink in Ink.Lista:
        InkList.append(ink.__dict__)
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
        pioro[len(Pen.Lista)] = Pen(**{'Brand': brand, 'Model': model, 'Price': price, 'BoughtMonth': boughtmonth, 'BoughtYear': boughtyear, 'Nibs': nibs})
    if item == "n":
        pass
    if item == "i":
        pass

def main():
    DoTheImporting('p')
    DoTheImporting('n')
    DoTheImporting('i')
    while True:
        print(pioro)
        x = input("What do you want to do?\n Possible options are:\n\n export (e) -- exports json files\n quit (q) -- quits the program\n add pen (ap)\n add nib (an)\n add ink (ai)\n")
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
        else:
            print("Invalid command")

        for pen in Pen.Lista:
            print(pen.Model)

if __name__ == "__main__":
   main()
