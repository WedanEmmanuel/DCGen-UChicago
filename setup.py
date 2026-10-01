from setuptools import setup, find_packages


setup(
    name="DCGen",
    version="1.1",
    author="Wedan Emmanuel GNIBGA, Andrew A. CHIEN",
    description="Datacenter configuration tool",
    author_email="wgnibga@uchicago.edu, aachien@uchicago.edu",
    license="DCGen License",
    license_files=("LICENSE",),

    packages=find_packages(),

    install_requires=["pydantic","numpy", "pandas"],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "run-dcgen-examples=DCGen.cli:run_examples",
        ],
    },
)