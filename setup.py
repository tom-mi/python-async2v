from setuptools import setup, find_packages

setup(
    name='async2v',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'argcomplete',
        'graphviz',
        'logwood',
    ],
    extras_require={

    },
)
