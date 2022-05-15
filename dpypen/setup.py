from setuptools import find_packages, setup

setup(
    name="dpypen",
    version="0.0.1",
    packages=find_packages(exclude=[]),
    entry_points={
        "console_scripts": [
            "supen=dpypen.supen:supen",
            "suink=dpypen.supen:suink",
        ],
    },
)
