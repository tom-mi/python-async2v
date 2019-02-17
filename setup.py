from setuptools import setup, find_packages

setup(
    name='async2v',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'argcomplete',
        'dataclasses; python_version < "3.7"',
        'graphviz',
        'logwood',
    ],
    include_package_data=True,
    extras_require={
        'pygame': ['pygame'],
        'opencv': ['opencv-python', 'numpy'],
    },
)
