__all__ = [
    "MarkdownV2Parser",
    "validate_markdown",
]

import re
from collections import deque
from typing import NamedTuple

escape_code = ["`", "\\"]
escape_link = [")", "\\"]
escape = [
    "_",
    "*",
    "[",
    "]",
    "(",
    ")",
    "~",
    "`",
    ">",
    "#",
    "+",
    "-",
    "=",
    "|",
    "{",
    "}",
    ".",
    "!",
]
emoji_link = re.compile(r"^tg://emoji\?id=\d+$")


class Token(NamedTuple):
    entity: str
    start: int


class Range(NamedTuple):
    start: int
    end: int


class MarkdownV2Parser:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.read_pos = 0
        self.length = len(self.text)
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.stack: deque[Token] = deque()

        self.prev_char: str | None = None
        self.prev_char2: str | None = None
        self.cur_char: str | None = None
        self.read_char()

    def validate(self) -> bool:  # noqa: C901, PLR0912
        """
        Validate that the given text is a valid Telegram Markdown v2 document
        """

        if not self.length:
            self.errors.append("text is empty")
            return False

        inline_code = False
        code_block = False
        blockquote = False
        unescaped_symbol = False

        while self.pos < self.length:
            match self.cur_char:
                # bold or strikethrough
                case "*" | "~" as ch:
                    if not self.read_entity(ch):
                        break
                # underline
                case "_" if self.peek_char() == "_":
                    self.read_char()
                    if not self.read_entity("__"):
                        break
                # italic
                case "_":
                    if not self.read_entity("_"):
                        break
                # spoiler
                case "|" if self.peek_char() == "|":
                    self.read_char()
                    if not self.read_entity("||"):
                        break
                # escaped character
                case "\\":
                    if self.peek_char() in escape:
                        self.read_char()
                # url link
                case "[":
                    if not self.read_link():
                        unescaped_symbol = True
                        break
                # custom emoji link
                case "!" if self.peek_char() == "[":
                    self.read_char()
                    if not self.read_emoji_link():
                        unescaped_symbol = True
                        break
                # inline code or code block
                case "`":
                    if self.peek_char() != "`":
                        inline_code = True
                        if self.read_code():
                            inline_code = False
                    elif self.peek_char() == "`":
                        if self.peek_char2() == "`":
                            code_block = True
                            if self.read_code_block():
                                code_block = False
                        else:
                            inline_code = False
                # deal with blockquotes
                case "\n":
                    if (
                        (next_ch := self.peek_char())
                        and next_ch in ["*", "`", "~"]
                        and self.entity_in_stack(next_ch)
                        and not blockquote
                    ):
                        self.read_entity(next_ch)
                        self.read_char()
                    elif (
                        self.peek_char() in ["*", "`", "~"]
                        and self.peek_char2() == self.peek_char()
                    ):
                        if (
                            self.prev_char == "|"
                            and self.prev_char2 == "|"
                            and self.stack
                        ):
                            self.stack.pop()
                        if self.stack:
                            break
                        if self.peek_char3() == ">":
                            self.read_char()
                            self.read_char()
                            self.read_char()
                            blockquote = True
                        elif blockquote:
                            self.read_char()
                            self.read_char()
                            blockquote = False
                            if self.stack:
                                break
                    elif self.peek_char() != ">" and blockquote:
                        if (
                            self.prev_char == "|"
                            and self.prev_char2 == "|"
                            and self.stack
                        ):
                            self.stack.pop()
                        if self.stack:
                            break
                        blockquote = False
                # more blockquotes
                case ">" if self.prev_char == "\n" or self.prev_char is None:
                    if not blockquote and self.stack:
                        break
                    blockquote = True
                # must escape this
                case (
                    "]"
                    | "("
                    | ")"
                    | ">"
                    | "#"
                    | "+"
                    | "-"
                    | "="
                    | "|"
                    | "{"
                    | "}"
                    | "."
                    | "!" as ch
                ):
                    self.errors.append(f"Unescaped {ch} at {self.pos}")
                    unescaped_symbol = True
                    break

            self.read_char()

        if self.stack:
            first_token = self.stack[0]
            self.errors.append(
                f"Unclosed {first_token.entity} entity at {first_token.start}"
            )
        if inline_code:
            self.errors.append("Unclosed inline code tag")
        if code_block:
            self.errors.append("Unclosed code block")

        valid = (
            not self.stack
            and not inline_code
            and not code_block
            and not unescaped_symbol
        )

        return valid

    def read_code(self) -> bool:
        self.read_char()  # skip `
        return bool(self.read_till("`", must_escape=escape_code))

    def read_code_block(self) -> bool:
        self.read_char()  # skip first `
        self.read_char()  # skip second `
        self.read_char()  # skip third `
        found = self.read_till("`", must_escape=escape_code)
        if found:
            if self.cur_char == "`" and self.peek_char() == "`":
                self.read_char()
                self.read_char()
                return True
            else:
                self.errors.append(
                    f"Unescaped {self.text[self.pos - 1]} at {self.pos}"
                )
        return False

    def read_link(self) -> Range | None:
        """
        Returns start and end position of the url in text or None
        """
        start_pos = self.pos
        self.read_char()  # skip [
        if self.read_till("]", must_escape=escape):
            if self.cur_char == "(":
                self.read_char()  # skip (
                return self.read_till(")", must_escape=escape_link)
            else:
                self.errors.append(f"Unescaped [ at {start_pos}")
                return None
        else:
            self.errors.append(f"Unescaped [ at {start_pos}")
            return None

    def read_emoji_link(self) -> bool:
        found = self.read_link()
        if not found:
            return False
        start, end = found
        url = self.text[start:end]
        if emoji_link.fullmatch(url):
            return True
        self.errors.append(f"Invalid emoji url at {start}")
        return False

    def read_till(
        self, char: str, must_escape: list[str] | None = None
    ) -> Range | None:
        """
        Returns start and end position in text if char is found or None
        """
        must_escape = must_escape or []
        start_pos = self.pos
        while self.cur_char:
            if self.cur_char == char:
                self.read_char()
                break
            elif self.cur_char == "\\":
                if self.peek_char() not in must_escape:
                    self.warnings.append(
                        f"Unneaded escape of {self.peek_char()} at {self.pos}"
                    )
                self.read_char()
                self.read_char()
            elif self.cur_char in must_escape:
                self.errors.append(f"Unescaped {self.cur_char} at {self.pos}")
                return None
            else:
                self.read_char()
        else:
            return None
        return Range(start_pos, self.pos - 1)

    def read_char(self) -> None:
        if self.read_pos >= self.length:
            self.cur_char = None
        else:
            self.prev_char2 = self.prev_char
            self.prev_char = self.cur_char
            self.cur_char = self.text[self.read_pos]
        self.pos = self.read_pos
        self.read_pos += 1

    def peek_char(self) -> str | None:
        if self.read_pos >= self.length:
            return None
        return self.text[self.read_pos]

    def peek_char2(self) -> str | None:
        if self.read_pos + 1 >= self.length:
            return None
        return self.text[self.read_pos + 1]

    def peek_char3(self) -> str | None:
        if self.read_pos + 2 >= self.length:
            return None
        return self.text[self.read_pos + 2]

    def read_entity(self, ch: str) -> bool:
        if self.stack:
            last_token = self.stack[-1]
            if last_token.entity == ch:
                self.stack.pop()
                return True
            elif self.entity_in_stack(ch):
                return False
        self.stack.append(Token(entity=ch, start=self.pos))
        return True

    def entity_in_stack(self, ch: str) -> bool:
        return any(token.entity == ch for token in self.stack)


def validate_markdown(text: str | None) -> str | None:
    if text is None:
        return None
    parser = MarkdownV2Parser(text)
    if parser.validate():
        return text
    raise ValueError(", ".join(parser.errors))
