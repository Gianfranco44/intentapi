from setuptools import setup

setup(
    name="intentapi",
    version="1.0.0",
    description="Official Python SDK for IntentAPI - automate anything with natural language",
    long_description=open("README_SDK.md").read(),
    long_description_content_type="text/markdown",
    author="Gianfranco",
    url="https://github.com/Gianfranco44/intentapi",
    py_modules=["intentapi"],
    package_dir={"": "."},
    python_requires=">=3.9",
    install_requires=["httpx>=0.25.0"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries",
    ],
)
