from setuptools import setup, find_packages
setup(
    name="awslog",
    version="0.1",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'awslog = awslog:main',
        ],
    },
    install_requires=[
        'boto3==1.9',
        'six==1.11',
        'dateparser==0.7.0',
    ]
)
