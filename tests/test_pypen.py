import tempfile
import unittest

from pypen import ink
from pypen import pen
from pypen import utils

import mock


class BasicTests(unittest.TestCase):
    def setUp(self):
        self.pens = pen.PenCollection("pens.json")
        self.inks = ink.InkCollection("inks.json")
        self.pens.import_from_file()
        self.inks.import_from_file()

    def test_import__pens(self):
        pens = [pens for pens in self.pens.raw_items.keys()]
        self.assertIn("Baoer051", pens)
        self.assertIn("KawecoAl-Sport", pens)
        self.assertIn("WingSung9133", pens)
        self.assertEqual("Baoer", self.pens[0].brand)

    def test_import__inks(self):
        inks = [inks for inks in self.inks.raw_items.keys()]
        self.assertIn("Carand'AcheBlueNight", inks)
        self.assertEqual("Caran d'Ache", self.inks[0].brand)

    def test_export(self):
        temporary_dir = tempfile.TemporaryDirectory()
        self.pens.export_to_file(directory=temporary_dir.name)
        imported_pens = pen.PenCollection("pens.json")
        imported_pens.import_from_file(directory=temporary_dir.name)
        for pen_item, imported_pen in zip(self.pens, imported_pens):
            self.assertEqual(pen_item.dump(), imported_pen.dump())
        temporary_dir.cleanup()

    def test_create_bins__pens(self):
        mapping = utils.create_buckets(self.pens, fields=["brand", "model"])
        assert mapping["ViscontiHomoSapiens"] == "VHo"

    def test_create_bins__inks(self):
        mapping = utils.create_buckets(self.inks, fields=["brand", "name"])
        assert mapping["KWZHoney"] == "KWHo"

    def test_create_single_bins(self):
        mapping = utils.create_single_bucket(self.pens[0].__dict__.keys())
        assert mapping["price"] == "pri1"

    @mock.patch("builtins.input", autospec=True)
    @mock.patch("builtins.print", autospec=True)
    def test_prompt(self, m_print, m_input):
        m_input.return_value = "TEco"
        result = self.pens.prompt_current_object()
        assert result == "TWSBIEco"

    @mock.patch("builtins.input", autospec=True)
    @mock.patch("builtins.print", autospec=True)
    def test_prompt__filtered(self, m_print, m_input):
        m_input.return_value = "TEc"
        result = self.pens.prompt_current_object(lambda pens: pens.rot == "2")
        assert result == "TWSBIEco"

    @mock.patch("builtins.input", autospec=True)
    @mock.patch("builtins.print", autospec=True)
    def test_edit(self, m_print, m_input):
        m_input.return_value = "i"
        self.pens.edit(self.pens[0])
        assert self.pens[0].item_id == "i"

    def test_generate_name(self):
        assert utils.generate_name(pen.Pen, {"brand": "foo", "model": "bar"}) == "foobar"

    @mock.patch("builtins.input", autospec=True)
    @mock.patch("builtins.print", autospec=True)
    def test_add(self, m_print, m_input):
        m_input.return_value = "iiii"
        self.pens.add()
        assert [pen for pen in self.pens if pen.item_id == "iiiiiiii"]
