from pypen import base


class Ink(base.CollectionItem):
    pass


class InkCollection(base.Collection):
    TYPE = Ink

    @property
    def get_prompt_params(self):
        return ['brand', 'name']
