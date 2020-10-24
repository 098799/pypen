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
    ("CH", "Chinese"),
    ("FR", "French"),
    ("DE", "German"),
    ("IT", "Italian"),
    ("JP", "Japanese"),
    ("CH", "Swiss"),
    ("TW", "Taiwanese"),
)
