from setuptools import setup
from setuptools import find_packages

numerapi_version = '0.9.0'


classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 3",
    "Topic :: Scientific/Engineering"]


setup(
    name="numerapi",
    version=numerapi_version,
    maintainer="uuazed",
    maintainer_email="uuazed@gmail.com",
    description="Automatically download and upload data for the Numerai machine learning competition",
    url='https://github.com/uuazed/numerapi',
    platforms="OS Independent",
    classifiers=classifiers,
    license='MIT License',
    package_data={'numerai': ['LICENSE', 'README.md']},
    packages=find_packages(exclude=['tests']),
    install_requires=["requests", "pytz", "python-dateutil", "tqdm"]
)
