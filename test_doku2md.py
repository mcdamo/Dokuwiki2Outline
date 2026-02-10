#!/usr/bin/env python3

import unittest
from doku2md import DokuWiki2MarkDown
from textwrap import dedent


class TestDokuwikiToMarkdown(unittest.TestCase):
    def setUp(self):
        self.dtm = DokuWiki2MarkDown()

    def test_no_timestamp(self):
        self.assertEqual('', self.dtm._rm_timestamp('Created Tuesday 03 April 2012\n'))
        self.assertEqual('', self.dtm._rm_timestamp(' Created Tuesday 03 April 2012\n'))
        self.assertEqual('\n', self.dtm._rm_timestamp('Created Tuesday 03 April 2012\n\n'))
        self.assertEqual('\n\n', self.dtm._rm_timestamp('\nCreated Tuesday 03 April 2012\n\n'))
        self.assertEqual('\n', self.dtm._rm_timestamp('\n'))
        self.assertEqual('Some text\n', self.dtm._rm_timestamp('Some text\n'))
        self.assertEqual(' ', self.dtm._rm_timestamp(' '))

    def test_italic(self):
        self.assertEqual('*italic*', self.dtm._tr_italic('//italic//'))
        self.assertEqual('/not italic//', self.dtm._tr_italic('/not italic//'))
        self.assertEqual('\n *italic*', self.dtm._tr_italic('\n //italic//'))
        self.assertEqual('*italic*\n', self.dtm._tr_italic('//italic//\n'))

    def test_underline(self):
        # Underline (not supported in Markdown, converted to bold)
        self.assertEqual('**underlined**', self.dtm._tr_underline('__underlined__'))
        self.assertEqual('_not_underlined_', self.dtm._tr_underline('_not_underlined_'))
        self.assertEqual('\n **underlined**', self.dtm._tr_underline('\n __underlined__'))
        self.assertEqual('**underlined** \n', self.dtm._tr_underline('__underlined__ \n'))

    def test_monospaced(self):
        self.assertEqual('`monospaced text`', self.dtm._tr_monospaced("''monospaced text''"))
        self.assertEqual('\'not monospaced text\'', self.dtm._tr_monospaced("'not monospaced text'"))
        self.assertEqual('\n `monospaced text`', self.dtm._tr_monospaced("\n ''monospaced text''"))
        self.assertEqual('`monospaced text` \n', self.dtm._tr_monospaced("''monospaced text'' \n"))

    def test_strikethrough(self):
        self.assertEqual('~~strikethrough text~~', self.dtm._tr_strikethrough('<del>strikethrough text</del>'))
        self.assertEqual('<del>not strikethrough text<del>', self.dtm._tr_strikethrough('<del>not strikethrough text<del>'))
        self.assertEqual('\n ~~strikethrough text~~', self.dtm._tr_strikethrough('\n <del>strikethrough text</del>'))
        self.assertEqual('~~strikethrough text~~ \n', self.dtm._tr_strikethrough('<del>strikethrough text</del> \n'))
        self.assertEqual('\n~~strikethrough text~~\n', self.dtm._tr_strikethrough('<del>\nstrikethrough text\n</del>'))

    def test_links(self):
        self.assertEqual('[Example](https://example.com)', self.dtm._tr_links('[[https://example.com|Example]]', True))
        self.assertEqual('<https://example.com>', self.dtm._tr_links('[[https://example.com]]', True))
        self.assertEqual('<https://example.com//two//slashes>', self.dtm._tr_links('[[https://example.com//two//slashes]]', True))
        # newline in link title
        self.assertEqual('[Example title](https://example.com)', self.dtm._tr_links('[[https://example.com|\nExample\ntitle\n]]', True))

        ## internal links
        # relative links without a page name are tricky, needs to know the current pages path
        self.assertEqual('[.:](../p3.md)', self.dtm._tr_links('[[.:]]', True, '/p1/p2/p3'))
        self.assertEqual('[..:](../../p2.md)', self.dtm._tr_links('[[..:]]', True, '/p1/p2/p3'))
        # page and folder (inks
        self.assertEqual('[..:dir1:doc#search](../dir1/doc.md)', self.dtm._tr_links('[[..:dir1:doc#search]]', True, ''))
        self.assertEqual('[..:dir1:dir2:#search](../dir1/dir2.md)', self.dtm._tr_links('[[..:dir1:dir2:#search]]', True, ''))
        self.assertEqual('[.doc](./doc.md)', self.dtm._tr_links('[[.doc]]', True, ''))
        self.assertEqual('[doc](./doc.md)', self.dtm._tr_links('[[doc]]', True, ''))
        self.assertEqual('[dir:](/dir.md)', self.dtm._tr_links('[[dir:]]', True, ''))
        self.assertEqual('[.:dir1:dir2:](./dir1/dir2.md)', self.dtm._tr_links('[[.:dir1:dir2:]]', True, ''))
        self.assertEqual('[.:dir1:dir2:doc](./dir1/dir2/doc.md)', self.dtm._tr_links('[[.:dir1:dir2:doc]]', True, ''))
        self.assertEqual('[:dir1:dir2:](/dir1/dir2.md)', self.dtm._tr_links('[[:dir1:dir2:]]', True, ''))
        self.assertEqual('[dir1:page](/dir1/page.md)', self.dtm._tr_links('[[dir1:page]]', True, ''))
        self.assertEqual('[dir1:image-1.jpg](/dir1/image-1.jpg)', self.dtm._tr_links('[[dir1:image-1.jpg]]', True, ''))

        ## page_moved=True: page moved to parent folder, so relative links need adjusting
        self.assertEqual('[.:](./p3.md)', self.dtm._tr_links('[[.:]]', True, '/p1/p2/p3', True))
        self.assertEqual('[..:](../p2.md)', self.dtm._tr_links('[[..:]]', True, '/p1/p2/p3', True))
        # page and folder (inks
        self.assertEqual('[..:dir1:doc#search](./dir1/doc.md)', self.dtm._tr_links('[[..:dir1:doc#search]]', True, '', True))
        self.assertEqual('[..:dir1:dir2:#search](./dir1/dir2.md)', self.dtm._tr_links('[[..:dir1:dir2:#search]]', True, '', True))
        self.assertEqual('[.doc](./p3/doc.md)', self.dtm._tr_links('[[.doc]]', True, '/p1/p2/p3', True))
        self.assertEqual('[doc](./p3/doc.md)', self.dtm._tr_links('[[doc]]', True, '/p1/p2/p3', True))
        self.assertEqual('[.:dir1:dir2:](./p3/dir1/dir2.md)', self.dtm._tr_links('[[.:dir1:dir2:]]', True, '/p1/p2/p3', True))
        self.assertEqual('[.:dir1:dir2:doc](./p3/dir1/dir2/doc.md)', self.dtm._tr_links('[[.:dir1:dir2:doc]]', True, '/p1/p2/p3', True))

    def test_rawlinks(self):
        self.assertEqual('<https://example.com>', self.dtm._tr_rawlinks('https://example.com'))
        self.assertEqual(' <https://example.com> ', self.dtm._tr_rawlinks(' https://example.com '))

    def test_headers(self):
        self.assertEqual('# Headline L1\n\n', self.dtm._tr_headers('====== Headline L1 ======\n'))
        self.assertEqual('# Headline L1\n\n', self.dtm._tr_headers('====== Headline L1 ======\n\n'))
        self.assertEqual('# Headline L1\n\n', self.dtm._tr_headers('====== Headline L1 ======\n \n'))
        self.assertEqual('# Headline L1\n\n', self.dtm._tr_headers('====== Headline L1 ======\n \n \n'))
        self.assertEqual('## Headline L2\n\n', self.dtm._tr_headers('===== Headline L2 =====\n'))
        self.assertEqual('### Headline L3\n\n', self.dtm._tr_headers('==== Headline L3 ====\n'))
        self.assertEqual('#### Headline L4\n\n', self.dtm._tr_headers('=== Headline L4 ===\n'))
        self.assertEqual('##### Headline L5\n\n', self.dtm._tr_headers('== Headline L5 ==\n'))
        self.assertEqual('= Not A Headline =\n', self.dtm._tr_headers('= Not A Headline =\n'))
        # handle header with mismatched number of =
        self.assertEqual('### Headline L3\n\n', self.dtm._tr_headers('==== Headline L3 ===\n'))
        self.assertEqual('### Headline L3\n\n', self.dtm._tr_headers('==== Headline L3 =====\n'))

    def test_code_blocks(self):
        self.assertEqual('```\ncode text\n```', self.dtm._tr_codeblocks('<code>\ncode text\n</code>', None))
        self.assertEqual('```\ncode text\n```', self.dtm._tr_codeblocks('<file>\ncode text\n</file>', None))
        self.assertEqual('```\ncode text\n```', self.dtm._tr_codeblocks('<file>code text</file>', None))
        self.assertEqual('```\ncode text\n```', self.dtm._tr_codeblocks('<file>\ncode text</file>', None))
        self.assertEqual('```\ncode text\n```', self.dtm._tr_codeblocks('<file>code text\n</file>', None))
        self.assertEqual('\n```\ncode text\n```', self.dtm._tr_codeblocks('\n<file>code text\n</file>', None))
        # with lang argument
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<code>\ncode text\n</code>', 'shell'))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file>\ncode text\n</file>', 'shell'))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file>code text</file>', 'shell'))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file>\ncode text</file>', 'shell'))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file>code text\n</file>', 'shell'))
        self.assertEqual('\n```shell\ncode text\n```', self.dtm._tr_codeblocks('\n<file>code text\n</file>', 'shell'))
        # with provided lang
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<code shell>\ncode text\n</code>', None))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell>\ncode text\n</file>', None))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell>code text</file>', None))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell>\ncode text</file>', None))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell>code text\n</file>', None))
        self.assertEqual('\n```shell\ncode text\n```', self.dtm._tr_codeblocks('\n<file shell>code text\n</file>', None))
        # with provided lang and filename
        self.assertEqual('`file.txt`\n\n```shell\ncode text\n```', self.dtm._tr_codeblocks('<code shell file.txt>\ncode text\n</code>', None, True))
        self.assertEqual('`file.txt`\n\n```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell file.txt>\ncode text\n</file>', None, True))
        self.assertEqual('`file.txt`\n\n```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell file.txt>code text</file>', None, True))
        self.assertEqual('`file.txt`\n\n```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell file.txt>\ncode text</file>', None, True))
        self.assertEqual('`file.txt`\n\n```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell file.txt>code text\n</file>', None, True))
        self.assertEqual('\n`file.txt`\n\n```shell\ncode text\n```', self.dtm._tr_codeblocks('\n<file shell file.txt>code text\n</file>', None, True))
        # do not apply any conversions inside code blocks
        self.assertEqual('```\n[[:not-a-link:]]\n//not-italic//\n```\n', self.dtm._dokuwiki_to_markdown('<code>[[:not-a-link:]]\n//not-italic//\n</code>', None, None))
        # code blocks nested in lists should be indented to the same level
        self.assertEqual('* ```\n  code\n  text\n  ```\n\n', self.dtm._dokuwiki_to_markdown('  * <code>code\ntext\n</code>', None, None))
        self.assertEqual('  * ```\n    code\n    text\n    ```\n\n', self.dtm._dokuwiki_to_markdown('    * <code>code\ntext\n</code>', None, None))
        # works with indented code blocks
        self.assertEqual('```\ncode\ntext\n```\n', self.dtm._dokuwiki_to_markdown('  code\n  text\n', None, None))
        self.assertEqual('```shell\ncode\ntext\n```\n', self.dtm._dokuwiki_to_markdown('  code\n  text\n', 'shell', None))


    def test_images(self):
        self.assertEqual('![alt text](image.png)', self.dtm._tr_images('{{image.png|alt text}}'))

    def test_footnotes(self):
        self.assertEqual('[^1]\n\n[^1]: Footnote text', self.dtm._tr_footnotes('((Footnote text))'))

    def test_linebreaks(self):
        self.assertEqual('Text on line  \n', self.dtm._tr_linebreaks('Text on line \\\\\n'))
        self.assertEqual('Text on line  \n', self.dtm._tr_linebreaks('Text on line \\\\   \n'))
        self.assertEqual('Text on line  \n', self.dtm._tr_linebreaks('Text on line\\\\\n'))
        self.assertEqual('Text on line  \n', self.dtm._tr_linebreaks('Text on line\\\\   \n'))
        self.assertEqual('Text on line  \n', self.dtm._tr_linebreaks('Text on line\\\\ \n'))

    def test_trailing_single_spaces(self):
        self.assertEqual('Text on line\n', self.dtm._rm_single_space_at_line_end('Text on line\n'))
        self.assertEqual('Text on line\n', self.dtm._rm_single_space_at_line_end('Text on line \n'))
        self.assertEqual('Text on line  \n', self.dtm._rm_single_space_at_line_end('Text on line  \n'))
        self.assertEqual('Text on line   \n', self.dtm._rm_single_space_at_line_end('Text on line   \n'))
        self.assertEqual('Text on line    \n', self.dtm._rm_single_space_at_line_end('Text on line    \n'))

    def test_tables(self):
        dw = dedent("""\
        ^ Heading 1      ^ Heading 2       ^ Heading 3          ^
        | Row 1 Col 1    | Row 1 Col 2     | Row 1 Col 3        |
        | Row 2 Col 1    | some colspan (note the double pipe) ||
        | Row 3 Col 1    | Row 3 Col 2     | Row 3 Col 3        |
        """)
        md = dedent("""\
        | Heading 1      | Heading 2       | Heading 3          |
        |  --- | --- | --- |
        | Row 1 Col 1    | Row 1 Col 2     | Row 1 Col 3        |
        | Row 2 Col 1    | some colspan (note the double pipe) | |
        | Row 3 Col 1    | Row 3 Col 2     | Row 3 Col 3        |
        """)
        self.assertEqual(self.dtm._tr_tables(dw), md)

    def test_lists(self):
        self.assertEqual('* Unordered item', self.dtm._tr_lists('  * Unordered item'))
        self.assertEqual('1. Ordered item', self.dtm._tr_lists('  - Ordered item'))
        self.assertEqual('  * Nested unordered item', self.dtm._tr_lists('    * Nested unordered item'))
        self.assertEqual('  1. Nested ordered item', self.dtm._tr_lists('    - Nested ordered item'))
        self.assertEqual('----', self.dtm._tr_lists('----')) # avoid horizontal rule
        self.assertEqual('* Unordered item\n  * Nested unordered item\n    * Subnested unordered item', self.dtm._tr_lists('  * Unordered item\n    * Nested unordered item\n      * Subnested unordered item'))
        self.assertEqual('1. Ordered item\n  1. Nested ordered item\n    1. Subnested ordered item\n  2. Nested ordered item 2\n2. Ordered item 2', self.dtm._tr_lists('  - Ordered item\n    - Nested ordered item\n      - Subnested ordered item\n    - Nested ordered item 2\n  - Ordered item 2'))

    def test_newlines(self):
        self.assertEqual('\n', self.dtm._rm_newlines('\n'))
        self.assertEqual('\n\n', self.dtm._rm_newlines('\n\n'))
        self.assertEqual('\n\n', self.dtm._rm_newlines('\n \n\n'))
        self.assertEqual('\n\n', self.dtm._rm_newlines('\n\n\n\n'))
        self.assertEqual('\n\n', self.dtm._rm_newlines('\n  \t  \n'))
        self.assertEqual('\nsometext\n', self.dtm._rm_newlines('\nsometext\n'))
        self.assertEqual('\nsometext\n\n', self.dtm._rm_newlines('\nsometext\n\n'))
        self.assertEqual('\nsometext\n\n', self.dtm._rm_newlines('\nsometext\n\n\n'))

    def test_nowiki(self):
        self.assertEqual('sometext', self.dtm._rm_nowiki('<nowiki>sometext</nowiki>'))

    def test_backslashes(self):
        self.assertEqual('\\\\', self.dtm._tr_backslashes('\\'))

if __name__ == '__main__':
    unittest.main(verbosity=2)
