# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="RuBLECMetric",
    version="1.0.1",
    author="Alexandra Noskova",
    description="Russian BLEC Metric for SQL-to-Text Evaluation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Alexergy/RuBLEC",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[],  
    include_package_data=True,
    package_data={
        "RuBLEC": ["config/*.json"],
    },
)
