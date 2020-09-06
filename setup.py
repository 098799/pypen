from setuptools import setup, find_packages


setup(
    name="pypen",
    packages=find_packages(),
    entry_points={"console_scripts": ["addpen=pypen.main:add_pen", "addink=pypen.main:add_ink"]},
)
