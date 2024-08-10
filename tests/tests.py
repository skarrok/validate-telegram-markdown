import pytest

from validate_telegram_markdown import MarkdownV2Parser

official_telegram_example = r"""
*bold \*text*
_italic \*text_
__underline__
~strikethrough~
||spoiler||
*bold _italic bold ~italic bold strikethrough ||italic bold strikethrough spoiler||~ __underline italic bold___ bold*
[inline URL](http://www.example.com/)
[inline mention of a user](tg://user?id=123456789)
![👍](tg://emoji?id=5368324170671202286)
`inline fixed-width code`
```
pre-formatted fixed-width code block
```
```python
pre-formatted fixed-width code block written in the Python programming language
```
>Block quotation started
>Block quotation continued
>Block quotation continued
>Block quotation continued
>The last line of the block quotation
**>The expandable block quotation started right after the previous block quotation
>It is separated from the previous block quotation by an empty bold entity
>Expandable block quotation continued
>Hidden by default part of the expandable block quotation started
>Expandable block quotation continued
>The last line of the expandable block quotation with the expandability mark||
"""


@pytest.mark.parametrize(
    ("text", "expected_result", "errors"),
    [
        # Valid
        (official_telegram_example, True, []),
        (">expandable quote||\n**>quote", True, []),
        (">expandable quote||\n**abc", True, []),
        (">quote with a spoiler||\n>||quote", True, []),
        ("*bold*\n>*quote*", True, []),
        (">*bold quote*\n*abc*", True, []),
        ("```allowed \\бэкслэш symbol```", True, []),
        ("___italic underline_**__", True, []),
        ("*bold over\n*newline", True, []),
        ("*bold over\nnewline*", True, []),
        ("_italic over\n_newline", True, []),
        ("_italic over\nnewline_", True, []),
        ("__underline over\n__newline", True, []),
        ("__underline over\nnewline__", True, []),
        (">quote *bold\n>still quote* not bold", True, []),
        ("*bold ``` code ``` bold*", True, []),
        ("*bold ``` co*de ``` bold*", True, []),
        (">quote||spoiler||\nnot quote", True, []),
        (">quote||spoiler||\n>quote", True, []),
        (">quote||spoiler||\n**>new quote", True, []),
        (">quote`inline\n>code`", True, []),
        ("![some emoji](tg://emoji?id=1)", True, []),
        # Valid, but not supported
        pytest.param(
            ">block\n____>new block",
            True,
            [],
            marks=pytest.mark.skip(reason="Not supported"),
        ),
        # Invalid
        ("", False, ["text is empty"]),
        ("___italic underline___", False, ["Unclosed __ entity at 1"]),
        ("*unescaped star **", False, ["Unclosed * entity at 17"]),
        ("*bold _italic*italic_", False, ["Unclosed * entity at 0"]),
        (
            ">unclosed\n__>underline",
            False,
            ["Unescaped > at 12", "Unclosed __ entity at 11"],
        ),
        (
            ">unclosed||\n||>spoiler",
            False,
            ["Unescaped > at 14", "Unclosed || entity at 13"],
        ),
        (">unclosed||\n>spoiler", False, ["Unclosed || entity at 10"]),
        ("*bold\n>quote*", False, ["Unclosed * entity at 0"]),
        (
            "*bold\n**>quote",
            False,
            ["Unescaped > at 8", "Unclosed * entity at 7"],
        ),
        (
            "*bold\n**>quote*",
            False,
            ["Unescaped > at 8", "Unclosed * entity at 7"],
        ),
        (">*bold\n>quote", False, ["Unclosed * entity at 1"]),
        (">*bold\n**>new quote*", False, ["Unclosed * entity at 1"]),
        (">*bold quote\nabc", False, ["Unclosed * entity at 1"]),
        ("*bold `code`", False, ["Unclosed * entity at 0"]),
        ("`unclosed inline\\` code", False, ["Unclosed inline code tag"]),
        (
            "```unclosed code` block",
            False,
            ["Unescaped ` at 17", "Unclosed code block"],
        ),
        (
            "```unescaped ` symbol```",
            False,
            ["Unescaped ` at 14", "Unclosed code block"],
        ),
        ("broken [link]", False, ["Unescaped [ at 7"]),
        ("broken [link] (http://example.com)", False, ["Unescaped [ at 7"]),
        (
            "[фы!ва](http://example.org/pa*th)",
            False,
            ["Unescaped ! at 3", "Unescaped [ at 0"],
        ),
        (
            "![some emoji](http://example.com)",
            False,
            ["Invalid emoji url at 14"],
        ),
        ("![some emoji](tg://notemoji)", False, ["Invalid emoji url at 14"]),
        ("Unescaped _ symbol", False, ["Unclosed _ entity at 10"]),
        ("Unescaped [ symbol", False, ["Unescaped [ at 10"]),
        ("Unescaped ] symbol", False, ["Unescaped ] at 10"]),
        ("Unescaped ( symbol", False, ["Unescaped ( at 10"]),
        ("Unescaped ) symbol", False, ["Unescaped ) at 10"]),
        ("Unescaped ~ symbol", False, ["Unclosed ~ entity at 10"]),
        ("Unescaped ` symbol", False, ["Unclosed inline code tag"]),
        ("Unescaped > symbol", False, ["Unescaped > at 10"]),
        ("Unescaped + symbol", False, ["Unescaped + at 10"]),
        ("Unescaped - symbol", False, ["Unescaped - at 10"]),
        ("Unescaped = symbol", False, ["Unescaped = at 10"]),
        ("Unescaped | symbol", False, ["Unescaped | at 10"]),
        ("Unescaped { symbol", False, ["Unescaped { at 10"]),
        ("Unescaped } symbol", False, ["Unescaped } at 10"]),
        ("Unescaped . symbol", False, ["Unescaped . at 10"]),
        ("Unescaped ! symbol", False, ["Unescaped ! at 10"]),
    ],
)
def test_markdownv2_validator(
    text: str, expected_result: bool, errors: list[str]
) -> None:
    parser = MarkdownV2Parser(text)
    result = parser.validate()
    assert parser.errors == errors
    assert result is expected_result
