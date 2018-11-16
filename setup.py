from setuptools import setup
from setuptools import find_packages


def convert_md_to_rst(path):
    try:
        from pypandoc import convert_file
    except ImportError:
        print("warning: pypandoc module not found, could not convert Markdown to RST")
        return open(path, 'r').read()

    return convert_file(path, 'rst')


numerapi_version = '1.4.0'


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


if __name__ == "__main__":
    setup(
        name="numerapi",
        version=numerapi_version,
        maintainer="uuazed",
        maintainer_email="uuazed@gmail.com",
        description="Automatically download and upload data for the Numerai machine learning competition",
        long_description=convert_md_to_rst('README.md'),
        url='https://github.com/uuazed/numerapi',
        platforms="OS Independent",
        classifiers=classifiers,
        license='MIT License',
        package_data={'numerai': ['LICENSE', 'README.md']},
        packages=find_packages(exclude=['tests']),
        install_requires=["requests", "pytz", "python-dateutil",
                          "tqdm", "click"],
        entry_points={
          'console_scripts': [
              'numerapi = numerapi.cli:cli'
          ]
          },
        )
