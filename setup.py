import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="moonraker-api",
    python_requires=">=3.8",
    install_requires=requirements,
    author="Clifford Roche",
    author_email="",
    description="Async websocket API client for Moonraker",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cmroche/moonraker-api",
    packages=setuptools.find_packages(exclude=["tests"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
)
