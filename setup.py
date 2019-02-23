from setuptools import setup, find_packages

with open('README.md') as f:
    long_description = f.read()

setup(
    name='async2v',
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
)
