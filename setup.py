from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="aether-runner",
    version="0.3.6",
    author="WildLink Team",
    description="Execute Luau tests on Roblox Cloud",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/aether",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={
        "aether": ["vendor/**/*"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "watchdog>=3.0.0",
        "tomli>=2.0.1; python_version < '3.11'",
    ],
    entry_points={
        "console_scripts": [
            "aether=aether.cli:main",
        ],
    },
)
