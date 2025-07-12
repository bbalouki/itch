import io
from os import path

from setuptools import setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with io.open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with io.open(path.join(here, "requirements.txt"), encoding="utf-8") as f:
    REQUIREMENTS = [line.rstrip() for line in f]

VERSION = "1.0.4"
DESCRIPTION = "Simple parser for ITCH messages"

KEYWORDS = [
    "Finance",
    "Financial",
    "Quantitative",
    "Equities",
    "Totalview-ITCH",
    "Totalview",
    "Nasdaq-ITCH",
    "Nasdaq",
    "ITCH",
    "Data",
    "Feed",
    "ETFs",
    "Funds",
    "Trading",
    "Investing",
]

CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Intended Audience :: Financial and Insurance Industry",
    "Topic :: Office/Business :: Financial :: Investment",
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
]

INLCUDE = ["itch"]
EXCLUDE = ["tests"]

# Setting up
setup(
    name="itchfeed",
    version=VERSION,
    author="Bertin Balouki SIMYELI",
    url="https://github.com/bbalouki/itch",
    download_url="https://pypi.org/project/itchfeed/",
    project_urls={
        "Source Code": "https://github.com/bbalouki/itch",
    },
    license="The MIT License (MIT)",
    author_email="<bertin@bbstrader.com>",
    maintainer="Bertin Balouki SIMYELI",
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=INLCUDE,
    install_requires=REQUIREMENTS,
    keywords=KEYWORDS,
    classifiers=CLASSIFIERS,
)
