# Validate Telegram Markdown

[![Lint and Test](https://github.com/skarrok/validate-telegram-markdown/actions/workflows/test.yml/badge.svg)](https://github.com/skarrok/validate-telegram-markdown/actions/workflows/test.yml)
[![pypi package](https://img.shields.io/pypi/v/validate-telegram-markdown)](https://pypi.org/project/validate-telegram-markdown)
[![python](https://img.shields.io/pypi/pyversions/validate-telegram-markdown)](https://pypi.org/project/validate-telegram-markdown)

This package tries to validate that telegram-flavored markdown is correct and
safe to use in [sendMessage](https://core.telegram.org/bots/api#sendmessage).

Simple and naive implementation, probably has bugs but good enough for my
personal use case.

Supports all features of [MarkdownV2 Style](https://core.telegram.org/bots/api#markdownv2-style).

Contributions are welcome!

## Installation

```bash
pip install validate-telegram-markdown
```

## Usage

```python
from validate_telegram_markdown import validate_markdown

message = "*bold*"
try:
    validate_markdown(message)
except ValueError:
    # something isn't right
    raise

# or here you can safely use message in telegram sendMessage method
```
