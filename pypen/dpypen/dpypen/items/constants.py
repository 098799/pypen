def choice(value):
    return value, value


CLASSES = (
    choice("Modern"),
    choice("Vintage"),
)


FILLING = (
    choice("Bulkfiller"),
    choice("Eyedropper"),
    choice("Lever"),
    choice("Piston"),
    choice("Plunger"),
    choice("Shutoff valve"),
    choice("Squeeze"),
    choice("c/c"),
)


NATIONALITIES = (
    ("US", "American"),
    ("EN", "English"),
    ("CH", "Chinese"),
    ("FR", "French"),
    ("DE", "German"),
    ("IT", "Italian"),
    ("JP", "Japanese"),
    ("CH", "Swiss"),
    ("TW", "Taiwanese"),
    ("PL", "Polish"),
)


NIB_CUTS = (
    choice("round"),
    choice("stub"),
    choice("italic"),
    choice("SIG"),
    choice("WA"),
    choice("flex"),
    choice("architect"),
)


NIB_MATERIALS = (
    choice("14k Gold"),
    choice("18k Gold"),
    choice("21k Gold"),
    choice("23k Palladium"),
    choice("Steel"),
)


COLORS = (
    choice('Black'),
    choice('Blue'),
    choice('Blue Black'),
    choice('Brown'),
    choice('Burgundy'),
    choice('Green'),
    choice('Grey'),
    choice('Orange'),
    choice('Olive'),
    choice('Pink'),
    choice('Purple'),
    choice('Red'),
    choice('Royal Blue'),
    choice('Teal'),
    choice('Turquoise'),
    choice('Yellow'),
)

HOW = (
    choice('Bought'),
    choice('Present'),
)
