from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="intelligent-invoice-processor",
    version="0.1.0",
    author="Shoban Ravichandran",
    author_email="x23272040@student.ncirl.ie",
    description="An intelligent OCR and ML-based invoice processing system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Shoban-Ravichandran-23272040/IAPA_CA",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "invoice-processor=invoice_processor.main:main",
        ],
    },
)
