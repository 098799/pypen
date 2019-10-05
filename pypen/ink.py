from pypen import base


class Ink(base.CollectionItem):
    type_name = "Ink"
    prompt_params = ["brand", "name"]


class InkCollection(base.Collection):
    item_class = Ink
