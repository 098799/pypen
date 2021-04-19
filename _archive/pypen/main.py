from pypen import ink
from pypen import pen


def add_pen():
    pens = pen.PenCollection("pens.json")
    pens.import_from_file()

    pens.add()

    pens.export_to_file()


def add_ink():
    inks = ink.InkCollection("inks.json")
    inks.import_from_file()

    inks.add()

    inks.export_to_file()
