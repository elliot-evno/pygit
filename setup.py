from setuptools import setup

setup(
    name="pygit",
    version="0.1",
    py_modules=["pygit"],
    entry_points={
        'console_scripts': [
            'pygit=pygit:main',
        ],
    },
)