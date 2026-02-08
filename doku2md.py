#!/usr/bin/env python3

import argparse
import os
import re
from functools import reduce
import uuid

class DokuWiki2MarkDown:

    codeblks = []

    @staticmethod
    def convert_file(filepath, lang, ts, codeblk_filename):
        try:
            with open(filepath, 'r') as f:
                dokuwiki_text = f.read()
        except FileNotFoundError:
            print(f"Error: File {filepath} not found.")
            return

        markdown_text = DokuWiki2MarkDown._dokuwiki_to_markdown(dokuwiki_text, lang, ts, codeblk_filename)

        new_filepath = os.path.splitext(filepath)[0] + '.md'
        with open(new_filepath, 'w') as f:
            print(f"Saving {new_filepath}")
            f.write(markdown_text)

    @staticmethod
    def convert_directory(directory, lang, ts, codeblk_filename):
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.txt'):
                        DokuWiki2MarkDown.convert_file(os.path.join(root, file), lang, ts, codeblk_filename)
        except NotADirectoryError:
            print(f"Error: Directory {directory} not found.")

    @staticmethod
    def _dokuwiki_to_markdown(dokuwiki_text, codeblk_lang, timestamps, codeblk_filename=False):

        DokuWiki2MarkDown.codeblks = []
        # Remove timestamps if elected
        if not timestamps:
            dokuwiki_text = DokuWiki2MarkDown._rm_timestamp(dokuwiki_text)
        dokuwiki_text = DokuWiki2MarkDown._extract_codeblocks(dokuwiki_text, codeblk_lang, codeblk_filename)

        # Transform the rest ()
        # - bold and block quotes share the same syntax in DokuWiki and MarkDown
        transforms = [
            DokuWiki2MarkDown._tr_links_initial_escape,
            DokuWiki2MarkDown._tr_headers,
            DokuWiki2MarkDown._tr_italic,
            DokuWiki2MarkDown._tr_underline,
            DokuWiki2MarkDown._tr_monospaced,
            DokuWiki2MarkDown._tr_strikethrough,
            DokuWiki2MarkDown._tr_images,
            DokuWiki2MarkDown._tr_footnotes,
            DokuWiki2MarkDown._tr_tables,
            DokuWiki2MarkDown._tr_lists,
            DokuWiki2MarkDown._tr_linebreaks,
            DokuWiki2MarkDown._tr_links_unescape,
            DokuWiki2MarkDown._rm_single_space_at_line_end,
            DokuWiki2MarkDown._rm_nowiki,
            DokuWiki2MarkDown._rm_newlines,
        ]
        dokuwiki_text = reduce(lambda text, func: func(text), transforms, dokuwiki_text)

        for (unique_id, codeblk) in DokuWiki2MarkDown.codeblks:
            dokuwiki_text = dokuwiki_text.replace(unique_id, codeblk)

        return dokuwiki_text

    @staticmethod
    def _rm_timestamp(text: str) -> str:
        return re.sub(r' *Created \w+ \d{2} \w+ \d{4}\n', '', text)

    @staticmethod
    def _tr_italic(text: str) -> str:
        return re.sub(r'//(.*?)//', r'*\1*', text)

    @staticmethod
    def _tr_underline(text: str) -> str:
        # Underline (not supported in Markdown, converted to bold)
        return re.sub(r'__(.*?)__', r'**\1**', text)

    @staticmethod
    def _tr_monospaced(text: str) -> str:
        return re.sub(r'\'\'(.*?)\'\'', r'`\1`', text)

    @staticmethod
    def _tr_strikethrough(text: str) -> str:
        return re.sub(r'<del>(.*?)</del>', r'~~\1~~', text)

    @staticmethod
    def _tr_links_initial_escape(text: str) -> str:
        def replace_link(match):
            url = match.group('url')
            title = match.group('title')
            if not title:
                title = url

            # strip newlines from title
            title = re.sub(r'\n', ' ', title.strip())

            # hack to avoid italic, bold, underline getting crushed
            url = re.sub(r'/', "##URL#ESCAPED#SLASH##", url)
            url = re.sub(r'\*', "##URL#ESCAPED#ASTERISK##", url)
            url = re.sub(r'_', "##URL#ESCAPED#UNDERSCORE##", url)

            title = re.sub(r'/', "##URL#ESCAPED#SLASH##", title)
            title = re.sub(r'\*', "##URL#ESCAPED#ASTERISK##", title)
            title = re.sub(r'_', "##URL#ESCAPED#UNDERSCORE##", title)
            
            return f'[{title}]({url})'
        return re.sub(r'\[\[(?P<url>[^|]*?)(\|(?P<title>.*?))?\]\]', replace_link, text, flags=re.DOTALL)

    @staticmethod
    def _tr_links_unescape(text: str) -> str:
        text = re.sub("##URL#ESCAPED#SLASH##", "/", text)
        text = re.sub("##URL#ESCAPED#ASTERISK##", "*", text)
        text = re.sub("##URL#ESCAPED#UNDERSCORE##", "_", text)
        
        return text

    @staticmethod
    def _tr_headers(text: str) -> str:
        for i in range(6, 1, -1):
            text = re.sub(rf" *{'=' * i} *(.*?) *{'=' * i} *\s+", rf"{'#' * (7 - i)} \1\n\n", text)
        return text

    @staticmethod
    def _extract_codeblocks(text: str, lang, codeblk_filename=False) -> str:
        def replace_block(match):
            unique_id = '[' + str(uuid.uuid4()) + ']'
            listitem = match.group('listitem')
            listitem = '' if listitem is None else listitem
            indent = ' ' * (len(listitem) - 2) # adjust for markdown indentation
            ret = DokuWiki2MarkDown._tr_codeblocks(match.group('block'), lang, codeblk_filename, indent)
            DokuWiki2MarkDown.codeblks.append((unique_id, ret))
            return f'{listitem}{unique_id}\n'

        return re.sub(r'(?P<listitem> +[*-] +)?(?P<block><(?:code|file)[^>]*>\n{0,}(.*?)\n{0,}</(?:code|file)>)', replace_block, text, flags=re.DOTALL)

    @staticmethod
    def _tr_codeblocks(text: str, lang, codeblk_filename=False, indent='') -> str:
        def replace_block(match):
            lang_type = '' if match.group('lang') is None else match.group('lang')
            lang_type = lang_type if lang is None else lang
            content = match.group('content')
            content = re.sub(r'^', indent, content, flags=re.MULTILINE)
            ret = f'```{lang_type}\n{content}\n{indent}```'
            if codeblk_filename and match.group('filename'):
                ret = f'`{match.group('filename')}`\n\n{ret}'
            return ret

        return re.sub(r'<(?:code|file)(\s+(?P<lang>[^> ]+))?(\s+(?P<filename>[^> ]+))?[^>]*>\n{0,}(?P<content>.*?)\n{0,}</(?:code|file)>', replace_block, text, flags=re.DOTALL)

    @staticmethod
    def _tr_images(text: str) -> str:
        return re.sub(r'\{\{(.*?)(\|(.*?))?\}\}', r'![\3](\1)', text)

    @staticmethod
    def _tr_footnotes(text: str) -> str:
        return re.sub(r'\(\((.*?)\)\)', r'[^1]\n\n[^1]: \1', text)

    @staticmethod
    def _tr_linebreaks(text: str) -> str:
        return re.sub(r' *\\{2} *\n', r'  \n', text)

    @staticmethod
    def _tr_lists(text: str) -> str:
        lines = text.split('\n')
        ordered_list_counter = 0
        for i, line in enumerate(lines):
            match = re.match(r'(\s*)([-*])(.*)', line)
            if match and not line.startswith("----"):
                spaces, bullet, rest = match.groups()
                indentation = len(spaces) // 2 - 1
                if bullet == '-':
                    ordered_list_counter += 1
                    bullet = str(ordered_list_counter) + '.'
                else:
                    # It's an unordered list item
                    bullet = '*'
                    # Reset counter when encountering an unordered list item
                    ordered_list_counter = 0
                lines[i] = '  '*indentation + bullet + rest
        return '\n'.join(lines)

    @staticmethod
    def _tr_tables(input_dokuwiki):
        lines = input_dokuwiki.split('\n')  # Splitting the DokuWiki text into lines
        in_table = False  # Flag to indicate whether we are currently processing a table
        output_markdown = []  # List to store the converted Markdown lines
        added_separator = False  # Flag to indicate whether the separator line has been added

        for line in lines:
            # Check if the line is part of a table (starts with ^ for headers or | for regular cells)
            if re.match(r'\s*(\^|\|).*', line):
                if not in_table:  # Entering a table
                    in_table = True
                    added_separator = False  # Reset the separator flag

                # Replace ^ with | for headers
                line = re.sub(r'\^', '|', line)

                # Handle colspan (||) by replacing it with empty cell markers (| |)
                line = re.sub(r'\|\|', '| |', line)

                # Remove rowspan indicators (:::)
                line = re.sub(r':::', '', line)

                # Add table separator after header row, if not already added
                if re.match(r'\|.*\|', line) and not added_separator:
                    output_markdown.append(line.strip())
                    num_columns = line.count('|') - 1
                    separator = '| ' + ' --- |' * num_columns
                    output_markdown.append(separator)
                    added_separator = True  # Set the separator flag
                elif not added_separator:
                    # If it's a header row but the separator is not yet added
                    output_markdown.append(line.strip())
                else:
                    # Append other processed lines to the Markdown text
                    output_markdown.append(line.strip())

            else:
                # We are outside a table, reset the flag
                if in_table:
                    in_table = False
                output_markdown.append(line)

        # no empty line found after the table, so add one:
        if (in_table):
            output_markdown.append('')
        # Join the Markdown lines into a single string and return
        text = '\n'.join(output_markdown)
        return text

    @staticmethod
    def _rm_newlines(text: str) -> str:
        """Remove any excessive (2+) newlines and replace with 2 \n"""
        return re.sub(r'(\n\s*){2,}', r'\n\n', text, flags=re.MULTILINE)

    @staticmethod
    def _rm_nowiki(text: str) -> str:
        return re.sub(r'<nowiki>(.*?)</nowiki>', r'\1', text)

    @staticmethod
    def _rm_single_space_at_line_end(text: str) -> str:
        return re.sub(r'(?<! ) (?! )$', '', text, flags=re.MULTILINE)


def main():
    parser = argparse.ArgumentParser(description='Convert Dokuwiki to Markdown.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file', help='File to convert.')
    group.add_argument('-d', '--directory', help='Directory of files to convert.')
    parser.add_argument('-l', '--lang', help='Codeblocks will be labeled with this Language (eg. shell).')
    parser.add_argument('-T', '--timestamps', dest='timestamps', action='store_true',
                        help='Keep textual timestamps in documents. (Default is to remove timestamps)')
    parser.add_argument('-c', '--codefile', dest='codefile', action='store_true',
                        help='Add code-block file name in code block header. (Default is to remove code-block file name)')

    args = parser.parse_args()
    dw2md = DokuWiki2MarkDown()
    if args.file:
        dw2md.convert_file(args.file, args.lang, args.timestamps, args.codefile)
    elif args.directory:
        dw2md.convert_directory(args.directory, args.lang, args.timestamps, args.codefile)


if __name__ == '__main__':
    main()
