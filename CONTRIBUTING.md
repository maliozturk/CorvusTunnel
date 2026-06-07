# Contributing to CorvusTunnel

Thank you for your interest in contributing to CorvusTunnel! 🪶

We welcome contributions of all kinds — bug fixes, features, documentation, tests, and ideas. This guide will help you get started.

## 📋 Before You Begin

### Contributor License Agreement (CLA)

By submitting a pull request, you agree to our [Contributor License Agreement](https://corvustunnel.com/landing/cla.html). In short:

- You retain ownership of your contributions
- You grant KALAI a license to use your code under the MIT License
- You confirm the work is original (or you have permission)

Your first PR constitutes acceptance of the CLA.

### Requirements

- **Python 3.10+** (we use modern type hints and syntax)
- **Git** for version control
- A GitHub account

## 🚀 How to Contribute

### 1. Fork & Clone

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/corvustunnel.git
cd corvustunnel
```

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bugfix-name
```

Use descriptive branch names:
- `feature/voice-language-detection`
- `fix/websocket-reconnect`
- `docs/api-reference`

### 3. Set Up Development Environment

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"
```

### 4. Make Your Changes

Write your code, tests, and documentation. Follow the code style guidelines below.

### 5. Run Tests & Lint

```bash
# Run tests
pytest tests/

# Run linter
ruff check .

# Auto-fix lint issues
ruff check . --fix

# Format code
ruff format .
```

All tests must pass and code must be lint-free before submitting.

### 6. Commit & Push

```bash
git add .
git commit -m "feat: add support for custom relay URLs"
git push origin feature/your-feature-name
```

We follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `test:` — Adding or updating tests
- `refactor:` — Code refactoring (no functional change)
- `chore:` — Maintenance tasks

### 7. Open a Pull Request

1. Go to the [CorvusTunnel repository](https://github.com/corvustunnel/corvustunnel)
2. Click "New Pull Request"
3. Select your fork and branch
4. Fill in the PR template with a clear description
5. Link any related issues

## 🎨 Code Style

We use **[ruff](https://docs.astral.sh/ruff/)** for linting and formatting. Configuration is in [`pyproject.toml`](pyproject.toml).

Key guidelines:

- **Line length**: 120 characters max
- **Quotes**: Double quotes
- **Type hints**: Use them everywhere — we target Python 3.10+
- **Docstrings**: Google style
- **Imports**: Sorted by ruff (isort-compatible)

```python
# ✅ Good
def encrypt_message(plaintext: str, key: bytes) -> bytes:
    """Encrypt a message using NaCl SecretBox.

    Args:
        plaintext: The message to encrypt.
        key: The 32-byte encryption key.

    Returns:
        The encrypted ciphertext as bytes.
    """
    box = SecretBox(key)
    return box.encrypt(plaintext.encode())
```

## 🧪 Testing

- Write tests for all new functionality
- Place tests in the `tests/` directory, mirroring the source structure
- Use `pytest` fixtures and parametrize for clean test code
- Aim for meaningful coverage, not just line coverage

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=corvustunnel

# Run a specific test file
pytest tests/test_encryption.py

# Run in verbose mode
pytest tests/ -v
```

## 📁 Project Structure

```
corvustunnel/
├── corvustunnel/          # Main package
│   ├── server/            # FastAPI server
│   ├── client/            # Mobile web client
│   ├── crypto/            # Encryption (NaCl/libsodium)
│   ├── agents/            # Agent adapters (Claude, Codex, etc.)
│   └── utils/             # Shared utilities
├── tests/                 # Test suite
├── docs/                  # Documentation
├── landing/               # Website
├── pyproject.toml         # Project config & ruff settings
└── LICENSE                # MIT License
```

## 🐛 Reporting Bugs

1. Check [existing issues](https://github.com/corvustunnel/corvustunnel/issues) first
2. Use the bug report template
3. Include: Python version, OS, CorvusTunnel version, steps to reproduce

## 🔒 Security Vulnerabilities

**Do NOT create public issues for security vulnerabilities.**

Email: **security@kalai-tech.com**

See [SECURITY.md](SECURITY.md) for our full security policy.

## 💬 Questions?

- [GitHub Discussions](https://github.com/corvustunnel/corvustunnel/discussions)
- [Discord](https://discord.gg/corvustunnel)
- [Telegram](https://t.me/corvustunnel)

---

Thank you for helping make CorvusTunnel better! 🪶
