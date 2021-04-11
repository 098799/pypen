from pypen import base


class Pen(base.CollectionItem):
    type_name = "Pen"
    prompt_params = ["brand", "model"]


class PenCollection(base.Collection):
    item_class = Pen
