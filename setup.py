from setuptools import setup, find_packages

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='async2v',
    license='MIT',
    author='Thomas Reifenberger',
    description='Framework for building computer-vision prototypes',
    long_description=long_description,
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
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
    ],
    project_urls={
        'Source on GitHub': 'https://github.com/tom-mi/python-async2v',
        'Documentation': 'https://async2v.readthedocs.io/',
        'Tests on Travis CI': 'https://travis-ci.com/tom-mi/python-async2v',
    },
)
