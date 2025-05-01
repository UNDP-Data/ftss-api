from setuptools import find_packages, setup

setup(
    name="ftss-api",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "psycopg",
        "pydantic",
    ],
) 