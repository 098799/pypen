import unittest

from pypen import utils


class RemoveDuplicatesTests(unittest.TestCase):
    def test_remove_duplicates(self):
        list_with_duplicates = [1, 9, 3, 2, 5, 2, 3, 8, 5]
        list_without_duplicates = utils.remove_duplicates(list_with_duplicates)
        self.assertEqual(list_without_duplicates, [1, 9, 3, 2, 5, 8])
