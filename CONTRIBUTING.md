# Contributing to Aether

Thank you for your interest in contributing to Aether! We appreciate your help in making this tool better for the Roblox community.

## Getting Started

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally:
    ```bash
    git clone https://github.com/yourusername/aether.git
    cd aether
    ```
3.  **Install development dependencies**:
    ```bash
    pip install -e .
    pip install build twine black pylint
    ```

## Development Workflow

1.  Create a new branch for your feature or fix:
    ```bash
    git checkout -b feature/my-awesome-feature
    ```
2.  Make your changes.
3.  Run tests locally to ensure everything works (see "Running Tests" below).
4.  Commit your changes with clear, descriptive messages.
5.  Push to your fork and submit a **Pull Request**.

## Running Tests

To run the internal tests (if available) or manual verification:

```bash
aether run
```

We recommend setting up a test place on Roblox and testing against it.

## Coding Style

- We follow **PEP 8** guidelines for Python code.
- Use **black** for formatting.
- Ensure your code is well-documented with docstrings.

## Reporting Issues

If you find a bug or have a feature request, please open an issue on GitHub. include:
- A clear description of the issue.
- Steps to reproduce (if applicable).
- Expected vs. actual behavior.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
