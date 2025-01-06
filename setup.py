from setuptools import setup, find_packages

setup(
    name='swaggen',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'click',
        'requests',
        'jsonschema',
        'openai'
    ],
    entry_points='''
        [console_scripts]
        swaggen=swaggen.swaggen:cli
    ''',
)
