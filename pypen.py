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

def DoTheImporting():
    with open('pens.json', 'r') as infile:
        PenList = json.load(infile)
        pioro = {}
    for number, pen in enumerate(PenList):
        pioro[number] = Pen(**pen)

    with open('nibs.json', 'r') as infile:
        NibList = json.load(infile)
        stalowka = {}
    for number, nib in enumerate(NibList):
        stalowka[number] = Nib(**nib)

    with open('inks.json', 'r') as infile:
        InkList = json.load(infile)
        atrament = {}
    for number, ink in enumerate(InkList):
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
    brand = input("Pen brand?\n")
    model = input("Pen model?\n")
    nachste = item(**{'Brand': brand, 'Model': model})

def main():
    DoTheImporting()
    while True:
        x = input("What do you want to do?\n Possible options are:\n\n export (e) -- exports json files\n quit (q) -- quits the program\n add (a) -- add or change something \n")
        if x == "export" or x == "e":
            DoTheExporting()
        elif x == "quit" or x == "q":
            exit()
        elif x == "add" or x == "ap":
            DoTheAdding(Pen)
        else:
            print("Invalid command")

        for pen in Pen.Lista:
            print(pen.Model)

if __name__ == "__main__":
   main()
