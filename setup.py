from setuptools import setup, find_packages

setup(
    name='async2v',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
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
