from os import path

from setuptools import setup, find_packages


here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md')) as f:
    long_description = f.read()

setup(
    name="awslog",
    version="0.1.6",
    packages=find_packages(),
    install_requires=[
        'boto3==1.9',
        'six==1.11',
        'dateparser==0.7.0',
        'crayons==0.1.2',
    ],
    author="Kristóf Jakab",
    author_email="jaksi07c8@gmail.com",
    description="Show the history and changes between configuration versions of AWS resources",
    license="MIT",
    keywords="amazon aws config log diff",
    url="https://github.com/jaksi/awslog",
    entry_points={
        'console_scripts': [
            'awslog = awslog:main',
        ],
    },
    long_description=long_description,
    long_description_content_type="text/markdown",
)
