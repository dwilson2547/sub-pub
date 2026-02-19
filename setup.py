from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="sub-pub",
    version="0.1.0",
    author="David Wilson",
    description="Extreme performance pub-sub message processor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dwilson2547/sub-pub",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "PyYAML>=6.0",
    ],
    extras_require={
        "kafka": ["kafka-python>=2.0.2"],
        "pulsar": ["pulsar-client>=3.3.0"],
        "eventhubs": ["azure-eventhub>=5.11.0"],
        "google_pubsub": ["google-cloud-pubsub>=2.18.0"],
        "all": [
            "kafka-python>=2.0.2",
            "pulsar-client>=3.3.0",
            "azure-eventhub>=5.11.0",
            "google-cloud-pubsub>=2.18.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "sub-pub=sub_pub.main:main",
        ],
    },
)
