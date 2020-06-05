from setuptools import setup, find_packages


setup(
    name="xiuminglib",
    version="0.1.0",
    description="Utilities for working with Blender in Python",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "Pillow",
        "scipy",
        "tqdm",
    ])
