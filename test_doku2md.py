#!/usr/bin/env python3

import unittest
from textwrap import dedent

from lib.dokuwiki_converter import Dokuwiki2Markdown


class TestDokuwikiToMarkdown(unittest.TestCase):
    def setUp(self):
        self.dtm = Dokuwiki2Markdown()

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
        self.assertEqual('[Example](https://example.com)', self.dtm._tr_links('[[https://example.com|Example]]', outline=True))
        self.assertEqual('<https://example.com>', self.dtm._tr_links('[[https://example.com]]', outline=True))
        self.assertEqual('<https://example.com//two//slashes>', self.dtm._tr_links('[[https://example.com//two//slashes]]', outline=True))
        # newline in link title
        self.assertEqual('[Example title](https://example.com)', self.dtm._tr_links('[[https://example.com|\nExample\ntitle\n]]', outline=True))

    def test_internal_links_special(self):
        # relative links without a page name are tricky, needs to know the current pages path
        with self.subTest('special link to current dir .:'):
            self.assertEqual('[p3](/p1/p2/p3.md)', self.dtm._tr_links('[[.:]]', outline=True, dirpath='/p1/p2/p3'))
        with self.subTest('special link to current dir .: page_moved=True'):
            self.assertEqual('[p3](/p1/p2/p3.md)', self.dtm._tr_links('[[.:]]', outline=True, dirpath='/p1/p2/p3', page_moved=True))
        with self.subTest('special link to parent dir ..:'):
            self.assertEqual('[p2](/p1/p2.md)', self.dtm._tr_links('[[..:]]', outline=True, dirpath='/p1/p2/p3'))
        with self.subTest('special link to parent dir ..: paged_moved=True'):
            self.assertEqual('[p2](/p1/p2.md)', self.dtm._tr_links('[[..:]]', outline=True, dirpath='/p1/p2/p3', page_moved=True))
    
    def test_internal_links_relative(self):
        # page and folder (inks
        with self.subTest('link to parent file'):
            self.assertEqual('[doc](/p1/p2/dir1/doc.md)', self.dtm._tr_links('[[..:dir1:doc#search]]', outline=True, dirpath='/p1/p2/p3'))
        with self.subTest('link to parent file page_moved'):
            self.assertEqual('[doc](/p1/p2/dir1/doc.md)', self.dtm._tr_links('[[..:dir1:doc#search]]', outline=True, dirpath='/p1/p2/p3', page_moved=True))
        with self.subTest('link to parent dir'):
           self.assertEqual('[dir2](/p1/p2/dir1/dir2.md)', self.dtm._tr_links('[[..:dir1:dir2:#search]]', outline=True, dirpath='/p1/p2/p3'))
        with self.subTest('link to parent dir page_moved'):
            self.assertEqual('[dir2](/p1/p2/dir1/dir2.md)', self.dtm._tr_links('[[..:dir1:dir2:#search]]', outline=True, dirpath='/p1/p2/p3', page_moved=True))
        with self.subTest('special test'):
            self.assertEqual('[Title](/p1/dir1/doc.md)', self.dtm._tr_links('[[..:dir1:doc#Search|Title]]', outline=True, dirpath='/p1/p2', page_moved=True))

        with self.subTest('link to file in current dir with dot'):
            self.assertEqual('[doc](/p1/p2/p3/doc.md)', self.dtm._tr_links('[[.doc]]', outline=True, dirpath='/p1/p2/p3'))
        with self.subTest('link to file in current dir with dot page_moved'):
            self.assertEqual('[doc](/p1/p2/p3/doc.md)', self.dtm._tr_links('[[.doc]]', outline=True, dirpath='/p1/p2/p3', page_moved=True))
        
        with self.subTest('link to dir starting with dot'):
            self.assertEqual('[page](/p1/p2/p3/dir1/page.md)', self.dtm._tr_links('[[.dir1:page#search]]', outline=True, dirpath='/p1/p2/p3'))
        with self.subTest('link to dir starting with dot page_moved'):
            self.assertEqual('[page](/p1/p2/p3/dir1/page.md)', self.dtm._tr_links('[[.dir1:page#search]]', outline=True, dirpath='/p1/p2/p3', page_moved=True))

        with self.subTest('link to a page with no path segments'):
            self.assertEqual('[doc](/p1/p2/p3/doc.md)', self.dtm._tr_links('[[doc]]', outline=True, dirpath='/p1/p2/p3'))
        with self.subTest('link to a page with no path segments page_moved'):
            self.assertEqual('[doc](/p1/p2/p3/doc.md)', self.dtm._tr_links('[[doc]]', outline=True, dirpath='/p1/p2/p3', page_moved=True))

        with self.subTest('special relative link to dir'):
            self.assertEqual('[dir2](/p1/p2/p3/dir1/dir2.md)', self.dtm._tr_links('[[.:dir1:dir2:]]', outline=True, dirpath='/p1/p2/p3'))
        with self.subTest('special relative link to dir page_moved'):
            self.assertEqual('[dir2](/p1/p2/p3/dir1/dir2.md)', self.dtm._tr_links('[[.:dir1:dir2:]]', outline=True, dirpath='/p1/p2/p3', page_moved=True))

        with self.subTest('special relative link to file'):
            self.assertEqual('[doc](/p1/p2/p3/dir1/dir2/doc.md)', self.dtm._tr_links('[[.:dir1:dir2:doc]]', outline=True, dirpath='/p1/p2/p3'))
        with self.subTest('special relative link to file page_moved'):
            self.assertEqual('[doc](/p1/p2/p3/dir1/dir2/doc.md)', self.dtm._tr_links('[[.:dir1:dir2:doc]]', outline=True, dirpath='/p1/p2/p3', page_moved=True))


    def test_internal_links_absolute(self):
        self.assertEqual('[dir](/dir.md)', self.dtm._tr_links('[[dir:]]', outline=True, dirpath=''))
        self.assertEqual('[dir2](/dir1/dir2.md)', self.dtm._tr_links('[[:dir1:dir2:]]', outline=True, dirpath=''))
        self.assertEqual('[page](/dir1/page.md)', self.dtm._tr_links('[[dir1:page]]', outline=True, dirpath=''))
        self.assertEqual('[image-1.jpg](/dir1/image-1.jpg)', self.dtm._tr_links('[[dir1:image-1.jpg]]', outline=True, dirpath=''))

    def test_internal_links_start(self):
        self.assertEqual('[dir](/dir.md)', self.dtm._tr_links('[[dir:start]]', outline=True, dirpath=''))

    def test_internal_links_lowercase(self):
        self.assertEqual('[page](/dir/page.md)', self.dtm._tr_links('[[Dir:PAGE]]', outline=True, dirpath=''))

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
        # test handling header promotion
        self.assertEqual('# Headline L1\n\n', self.dtm._tr_headers('====== Headline L1 ======\n', promote=True))
        self.assertEqual('# Headline L2\n\n', self.dtm._tr_headers('===== Headline L2 =====\n', promote=True))
        self.assertEqual('## Headline L3\n\n', self.dtm._tr_headers('==== Headline L3 ====\n', promote=True))
        self.assertEqual('### Headline L4\n\n', self.dtm._tr_headers('=== Headline L4 ===\n', promote=True))
        self.assertEqual('#### Headline L5\n\n', self.dtm._tr_headers('== Headline L5 ==\n', promote=True))

    def test_code_blocks(self):
        self.assertEqual('```\ncode text\n```', self.dtm.convert('<code>code text</code>'))
        self.assertEqual('```\ncode text\n```', self.dtm._tr_codeblocks('<code>\ncode text\n</code>'))
        self.assertEqual('```\ncode text\n```', self.dtm._tr_codeblocks('<file>\ncode text\n</file>'))
        self.assertEqual('```\ncode text\n```', self.dtm._tr_codeblocks('<file>code text</file>'))
        self.assertEqual('```\ncode text\n```', self.dtm._tr_codeblocks('<file>\ncode text</file>'))
        self.assertEqual('```\ncode text\n```', self.dtm._tr_codeblocks('<file>code text\n</file>'))
        self.assertEqual('\n```\ncode text\n```', self.dtm._tr_codeblocks('\n<file>code text\n</file>'))
        # with lang argument
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<code>\ncode text\n</code>', lang='shell'))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file>\ncode text\n</file>', lang='shell'))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file>code text</file>', 'shell'))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file>\ncode text</file>', lang='shell'))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file>code text\n</file>', lang='shell'))
        self.assertEqual('\n```shell\ncode text\n```', self.dtm._tr_codeblocks('\n<file>code text\n</file>', lang='shell'))
        # with provided lang
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<code shell>\ncode text\n</code>'))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell>\ncode text\n</file>'))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell>code text</file>'))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell>\ncode text</file>'))
        self.assertEqual('```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell>code text\n</file>'))
        self.assertEqual('\n```shell\ncode text\n```', self.dtm._tr_codeblocks('\n<file shell>code text\n</file>'))
        # with provided lang and filename
        self.assertEqual('`file.txt`\n\n```shell\ncode text\n```', self.dtm._tr_codeblocks('<code shell file.txt>\ncode text\n</code>', filename=True))
        self.assertEqual('`file.txt`\n\n```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell file.txt>\ncode text\n</file>', filename=True))
        self.assertEqual('`file.txt`\n\n```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell file.txt>code text</file>', filename=True))
        self.assertEqual('`file.txt`\n\n```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell file.txt>\ncode text</file>', filename=True))
        self.assertEqual('`file.txt`\n\n```shell\ncode text\n```', self.dtm._tr_codeblocks('<file shell file.txt>code text\n</file>', filename=True))
        self.assertEqual('\n`file.txt`\n\n```shell\ncode text\n```', self.dtm._tr_codeblocks('\n<file shell file.txt>code text\n</file>', filename=True))

    def test_code_blocks_nowiki(self):
        # do not apply any conversions inside code blocks
        self.assertEqual('```\n[[:not-a-link:]]\n//not-italic//\n```', self.dtm.convert('<code>[[:not-a-link:]]\n//not-italic//\n</code>'))

    def test_code_blocks_nested_in_lists(self):
        # code blocks nested in lists should be indented to the same level
        with self.subTest('inline code'):
            self.assertEqual('* `code text`',
                self.dtm.convert("  * ''code text''"))
        with self.subTest('code block'):
            self.assertEqual('* text\n  ```\n  code text\n  ```',
                self.dtm.convert('  * text <code>code text</code>'))
        with self.subTest('code block spanning lines'):
            self.assertEqual('* normal list item\n* ```\n  code\n  text\n  ```',
                self.dtm.convert('  * normal list item\n  * <code>code\ntext\n</code>'))
            self.assertEqual('* ```\n  code\n  text\n  ```',
                self.dtm.convert('  * <code>code\ntext\n</code>'))
        with self.subTest('code block after list item'):
            self.assertEqual('\n* normal list item\n* ```\n  code text\n  ```\n\n',
                self.dtm.convert('\n  * normal list item\n  * <code>code text</code>\n'))
        with self.subTest('code block after list item with trailing list'):
            self.assertEqual('\n* normal list item\n* ```\n  code text\n  ```\n* another list item\n\n',
                self.dtm.convert('\n  * normal list item\n  * <code>code text</code>\n  * another list item\n'))
        with self.subTest('code block spanning lines after list item'):
            self.assertEqual('\n* normal list item\n* ```\n  code\n  text\n  ```\n\n',
                self.dtm.convert('\n  * normal list item\n  * <code>code\ntext\n</code>\n'))
        with self.subTest('code block with prefix and suffix'):
            self.assertEqual('* preceeding\n  ```\n  code text\n  ```\n  trailing\n',
                self.dtm.convert('  * preceeding <code>code text</code> trailing'))
        with self.subTest('code block spanning lines with prefix and suffix'):
            self.assertEqual('* preceeding\n  ```\n  code\n  text\n  ```\n  trailing\n',
                self.dtm.convert('  * preceeding <code>code\ntext\n</code> trailing'))
        with self.subTest('nested code block'):
            self.assertEqual('    * ```\n    code\n    text\n    ```',
                self.dtm.convert('    * <code>code\ntext\n</code>'))

    def test_code_blocks_indented(self):
        # works with indented code blocks
        self.assertEqual('```\ncode\ntext\n```\n\n',
            self.dtm.convert('  code\n  text\n'))
        self.assertEqual('```\ncode\ntext\n```\n\n',
            self.dtm.convert('  code\n  text\n', codeblock_lang='shell')) # unsupported
        self.assertEqual('\n```\n<code>\ntext\n</code>\n```\n\n',
            self.dtm.convert('\n  <code>\n  text\n  </code>\n'))
        self.assertEqual('\n```\nfirst block\nanother line\n```\n\nnot a block\n```\nsecond block\n```\n\n',
            self.dtm.convert('\n  first block\n  another line\nnot a block\n  second block\n'))
        self.assertEqual('\n```\nfirst block\n```\n\n\n```\nsecond block\n```\n\n',
            self.dtm.convert('\n  first block\n\n  second block\n'))


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
        This is not part of the table
        """)
        md = dedent("""\
        | Heading 1      | Heading 2       | Heading 3          |
        |  --- | --- | --- |
        | Row 1 Col 1    | Row 1 Col 2     | Row 1 Col 3        |
        | Row 2 Col 1    | some colspan (note the double pipe) | |
        | Row 3 Col 1    | Row 3 Col 2     | Row 3 Col 3        |

        This is not part of the table
        """)
        self.assertEqual(self.dtm._tr_tables(dw), md)

    def test_lists(self):
        self.assertEqual('* Unordered item', self.dtm._tr_lists('  * Unordered item'))
        self.assertEqual('1. Ordered item', self.dtm._tr_lists('  - Ordered item'))
        self.assertEqual('    * Nested unordered item', self.dtm._tr_lists('    * Nested unordered item'))
        self.assertEqual('    1. Nested ordered item', self.dtm._tr_lists('    - Nested ordered item'))
        self.assertEqual('----', self.dtm._tr_lists('----')) # avoid horizontal rule
        self.assertEqual("""* Unordered item
    * Nested unordered item
        * Subnested unordered item""",
            self.dtm._tr_lists("""  * Unordered item
    * Nested unordered item
      * Subnested unordered item"""))
        self.assertEqual("""1. Ordered item
    1. Nested ordered item
        1. Subnested ordered item
    2. Nested ordered item 2
2. Ordered item 2""",
            self.dtm._tr_lists("""  - Ordered item
    - Nested ordered item
      - Subnested ordered item
    - Nested ordered item 2
  - Ordered item 2"""))

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
        self.assertEqual('<code>', self.dtm._rm_nowiki('%%<code>%%'))

    def test_backslashes(self):
        self.assertEqual('\\\\', self.dtm._tr_backslashes('\\'))

    def test_strikethrough_codeblock(self):
        # markdown does not allow strikethrough around a code block
        self.assertEqual(f' ~~`strikethrough text`~~ ', self.dtm.convert('<del><code>strikethrough text</code></del>'))
        self.assertEqual(f' ~~`strikethrough`~~\n~~`block`~~ ', self.dtm.convert('<del><code>strikethrough\nblock</code></del>'))
        self.assertEqual(f' ~~`strikethrough block`~~ ', self.dtm.convert('<del><code shell filename.xml>strikethrough block</code></del>', codeblock_filename=True))
        self.assertEqual(f'~~preceeding text~~ ~~`strikethrough`~~\n~~`block`~~ ~~trailing text~~',
            self.dtm.convert('<del>preceeding text\n<code>\nstrikethrough\nblock</code>\ntrailing text</del>'))
        self.assertEqual(f'~~preceeding text~~\n~~code~~\n~~block~~\n', self.dtm.convert('<del>preceeding text\n  code\n  block\n</del>'))

    def test_strikethrough_links(self):
        self.assertEqual(f'~~[title](https://example.com)~~', self.dtm.convert('<del>[[https://example.com|title]]</del>'))

if __name__ == '__main__':
    unittest.main(verbosity=2)
