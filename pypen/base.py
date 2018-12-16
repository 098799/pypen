import json
import os

from pypen import utils


WORKING_DIR = "/home/grining/Dropbox/pens/pypen"
PROGRAM_DIR = "pypen"
FILE_DIR = os.path.join(WORKING_DIR, PROGRAM_DIR)


class CollectionItem(object):
    def __init__(self, item_id, **kwargs):
        self.item_id = item_id
        for kwarg, value in kwargs.items():
            setattr(self, kwarg.lower(), value)

    def dump(self):
        attribute_dict = self.__dict__.copy()
        attribute_dict.pop("item_id")
        return attribute_dict


class Collection(object):
    def __init__(self, file_name):
        self.file_name = file_name
        self.object_list = []
        self.raw_items = []

    @property
    def get_prompt_params(self):
        raise NotImplementedError()

    def dump(self):
        outcome_dict = {}
        for item in self.object_list:
            outcome_dict[item.item_id] = item.dump()
        return outcome_dict

    def edit(self):
        fields = self.object_list[0].__dict__.keys()

    def export_to_file(self, file_name=None, directory=FILE_DIR):
        file_name = file_name if file_name else self.file_name
        path_to_file = os.path.join(directory, file_name)
        with open(path_to_file, "w") as outfile:
            json.dump(self.dump(), outfile, indent=4, sort_keys=True)

    def import_from_file(self, file_name=None, directory=FILE_DIR):
        file_name = file_name if file_name else self.file_name
        path_to_file = os.path.join(directory, file_name)
        with open(path_to_file, "r") as infile:
            self.raw_items = json.load(infile)
        for item, description in self.raw_items.items():
            self.object_list.append(self.TYPE(item, **description))

    def prompt(self, filter_):
        print("Choose from the following:")

        mappings = utils.create_buckets(
            list(filter(filter_, self.object_list)), fields=self.get_prompt_params
        )

        for item, map_ in mappings.items():
            print((map_ + ":").ljust(8), item)

        which_one = input("Which one?\n")
        return utils.mapping_from_bins(mappings, which_one)
