import json
import logging
import os

from pypen import utils


WORKING_DIR = "/home/grining/Dropbox/pens/pypen"
PROGRAM_DIR = "pypen"
FILE_DIR = os.path.join(WORKING_DIR, PROGRAM_DIR)

logging.basicConfig(level=logging.DEBUG)


class CollectionItem(object):
    type_name = None

    def __init__(self, item_id, **kwargs):
        self.item_id = item_id
        for kwarg, value in kwargs.items():
            setattr(self, kwarg.lower(), value)

    def __repr__(self):
        return f"{self.type_name}: {self.item_id}"

    def dump(self):
        attribute_dict = self.__dict__.copy()
        attribute_dict.pop("item_id")
        return attribute_dict

    @property
    def prompt_params(self):
        raise NotImplementedError()


class Collection(list):
    item_class = None

    def __init__(self, file_name):
        self.file_name = file_name
        self.raw_items = []

    def add(self):
        print(f"Adding {self[0].type_name} object")

        description = {}

        for field in list(self[0].__dict__.keys()):
            if field != "item_id":
                from_what = {getattr(item, field) for item in self}
                mapping = utils.create_single_bucket(from_what)
                description[field] = self.prompt(mapping)

        self.append(self.item_class(utils.generate_name(self.item_class, description), **description))
        self.sort(key=lambda x: x.item_id)

    def dump(self):
        outcome_dict = {}
        for item in self:
            outcome_dict[item.item_id] = item.dump()
        return outcome_dict

    def edit(self, object_):
        mapping = utils.create_single_bucket(object_.__dict__.keys())
        field = self.prompt(mapping)
        previous_value = getattr(object_, field, None)
        self.edit_value(object_, field)
        print(
            f"{object_.type_name}'s field {field} has been changed from {previous_value} to {getattr(object_, field)}"
        )

    def edit_value(self, object_, field):
        final_value = input("To what do we change this value?\n")
        setattr(object_, field, final_value)

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
            self.append(self.item_class(item, **description))

    def prompt(self, mapping):
        print("Choose from the following:")

        for item, map_ in mapping.items():
            print((map_ + ":").ljust(8), item)

        which_one = input("Which one?\n")

        if which_one:
            try_one = utils.mapping_from_bins(mapping, which_one)

            if try_one is not None:
                return try_one
            else:
                return which_one
        else:
            print("Write now:\n")
            what = input()
            return what

    def prompt_current_object(self, filter_=lambda x: x):
        mappings = utils.create_buckets(list(filter(filter_, self)), fields=self[0].prompt_params)
        return self.prompt(mappings)
