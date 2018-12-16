from pypen import base


class Pen(base.CollectionItem):
    pass


class PenCollection(base.Collection):
    TYPE = Pen

    @property
    def get_prompt_params(self):
        return ['brand', 'model']
