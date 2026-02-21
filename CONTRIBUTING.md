# Contributing to AutoXMail v2

First off, thanks for taking the time to contribute! 🎉

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to build something great together.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce**
- **Expected behavior**
- **Actual behavior**
- **Screenshots** (if applicable)
- **Environment details** (OS, Python version, Docker version)
- **Logs** (relevant error messages)

**Example:**

```markdown
**Bug:** Bot crashes when viewing message with large attachment

**Steps to Reproduce:**
1. Add Gmail account
2. Click "Inbox"
3. Click message with 20MB attachment
4. Bot crashes

**Expected:** Message displays with attachment info
**Actual:** Bot crashes with MemoryError

**Environment:**
- OS: Ubuntu 22.04
- Python: 3.11.2
- Docker: 24.0.5
- Memory limit: 100MB

**Logs:**
```
MemoryError: Unable to allocate memory
```
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Clear title and description**
- **Use case** (why is this needed?)
- **Proposed solution**
- **Alternatives considered**
- **Additional context**

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Test your changes**
5. **Commit with clear messages** (`git commit -m 'Add amazing feature'`)
6. **Push to your fork** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request**

## Development Setup

### Prerequisites

- Python 3.11+
- Git
- Docker/Podman (optional)

### Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/AutoXMail_v2.git
cd AutoXMail_v2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
python3 setup.py

# Run bot
python main.py
```

### Running Tests

```bash
# Unit tests (when implemented)
pytest tests/

# Integration tests (when implemented)
pytest tests/integration/

# Coverage
pytest --cov=. tests/
```

### Code Style

We follow PEP 8 with some modifications:

- **Line length:** 100 characters (not 79)
- **Indentation:** 4 spaces
- **Quotes:** Single quotes for strings, double for docstrings
- **Imports:** Grouped (standard, third-party, local)

**Format your code:**

```bash
# Install formatters
pip install black isort

# Format
black .
isort .
```

**Lint your code:**

```bash
# Install linters
pip install flake8 pylint

# Lint
flake8 .
pylint *.py
```

## Project Structure

```
AutoXMail_v2/
├── main.py                 # Entry point
├── config.py               # Configuration
├── database.py             # Database layer
├── crypto.py               # Encryption
├── gmail_service.py        # Gmail API
├── handlers.py             # Telegram handlers
├── oauth_handler.py        # OAuth flow
├── utils.py                # Utilities
├── tests/                  # Tests (future)
│   ├── test_database.py
│   ├── test_crypto.py
│   └── test_handlers.py
└── docs/                   # Documentation
```

## Coding Guidelines

### Python

```python
# Good
async def get_messages(account_id: int, max_results: int = 20) -> List[Dict[str, Any]]:
    """Get messages from Gmail account.
    
    Args:
        account_id: Gmail account ID
        max_results: Maximum messages to fetch
        
    Returns:
        List of message dictionaries
        
    Raises:
        ValueError: If account not found
    """
    service = await self.get_service(account_id)
    results = service.users().messages().list(
        userId='me',
        maxResults=max_results
    ).execute()
    return results.get('messages', [])

# Bad
def get_msgs(acc_id, max=20):
    svc = get_svc(acc_id)
    res = svc.users().messages().list(userId='me', maxResults=max).execute()
    return res.get('messages', [])
```

### Database

```python
# Good - Use async/await
async def add_user(self, user_id: int, username: str = None):
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute(
            "INSERT INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()

# Bad - Blocking operations
def add_user(self, user_id, username):
    conn = sqlite3.connect(self.db_path)
    conn.execute("INSERT INTO users VALUES (?, ?)", (user_id, username))
    conn.commit()
```

### Error Handling

```python
# Good - Specific exceptions
try:
    account = await db.get_gmail_account(account_id)
    if not account:
        raise ValueError(f"Account {account_id} not found")
except ValueError as e:
    logger.error(f"Account error: {e}")
    await update.message.reply_text(f"❌ {str(e)}")
except Exception as e:
    logger.exception("Unexpected error")
    await update.message.reply_text("❌ An error occurred")

# Bad - Catch all
try:
    account = db.get_account(account_id)
except:
    pass
```

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add email composition feature
fix: resolve memory leak in gmail service
docs: update deployment guide
style: format code with black
refactor: simplify oauth handler
test: add database tests
chore: update dependencies
```

**Examples:**

```bash
# Good
git commit -m "feat: add search UI with filters"
git commit -m "fix: handle expired tokens correctly"
git commit -m "docs: add troubleshooting section"

# Bad
git commit -m "updates"
git commit -m "fixed stuff"
git commit -m "WIP"
```

## Testing

### Unit Tests

```python
# tests/test_crypto.py
import pytest
from crypto import CryptoManager

def test_encrypt_decrypt():
    crypto = CryptoManager()
    user_id = 12345
    data = b"test data"
    
    encrypted = crypto.encrypt(data, user_id)
    decrypted = crypto.decrypt(encrypted, user_id)
    
    assert decrypted == data

def test_per_user_encryption():
    crypto = CryptoManager()
    data = b"test data"
    
    enc1 = crypto.encrypt(data, user_id=1)
    enc2 = crypto.encrypt(data, user_id=2)
    
    assert enc1 != enc2  # Different users = different encryption
```

### Integration Tests

```python
# tests/integration/test_oauth_flow.py
import pytest
from telegram import Update
from oauth_handler import oauth_handler

@pytest.mark.asyncio
async def test_oauth_flow():
    # Test complete OAuth flow
    # 1. Start OAuth
    # 2. Upload credentials
    # 3. Process auth code
    # 4. Verify account added
    pass
```

## Documentation

### Code Documentation

```python
def parse_email_headers(message: dict) -> Tuple[str, str, str]:
    """Extract subject, sender, and date from Gmail message.
    
    Args:
        message: Gmail message dictionary from API
        
    Returns:
        Tuple of (subject, sender, date)
        
    Example:
        >>> message = {'payload': {'headers': [...]}}
        >>> subject, sender, date = parse_email_headers(message)
        >>> print(subject)
        'Welcome to Gmail'
    """
    headers = message['payload']['headers']
    # ... implementation
```

### User Documentation

- Write clear, concise instructions
- Include examples and screenshots
- Explain why, not just how
- Keep it up-to-date

## Review Process

1. **Automated checks** run on PR (build, tests, linting)
2. **Code review** by maintainer
3. **Testing** by maintainer
4. **Merge** if approved

**Review criteria:**
- Code quality
- Test coverage
- Documentation
- Performance
- Security
- Backward compatibility

## Release Process

1. Update version in `config.py`
2. Update `CHANGELOG.md`
3. Create git tag (`v2.1.0`)
4. Push tag to GitHub
5. GitHub Actions creates release
6. Update documentation

## Questions?

- **GitHub Issues:** For bugs and features
- **GitHub Discussions:** For questions and ideas
- **Email:** theasimgrphics@gmail.com

## Recognition

Contributors will be:
- Listed in `CHANGELOG.md`
- Mentioned in release notes
- Added to `CONTRIBUTORS.md` (if significant contribution)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to AutoXMail v2!** 🚀
