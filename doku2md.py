#!/usr/bin/env python3

import argparse
import os
import re
from functools import reduce
import uuid
from pathlib import Path

class DokuWiki2MarkDown:

    codeblks = []
    lines = []
    line_idx = 0

    @staticmethod
    def convert_file(filepath, lang, ts, codeblk_filename, outputpath, outline):
        try:
            with open(filepath, 'r') as f:
                dokuwiki_text = f.read()
        except FileNotFoundError:
            print(f"Error: File {filepath} not found.")
            return

        if outputpath:
            new_filepath = os.path.splitext(os.path.join(outputpath, filepath))[0] + '.md'
        else:
            new_filepath = os.path.splitext(filepath)[0] + '.md'

        filename = os.path.splitext(os.path.basename(new_filepath))[0]
        dirpath = os.path.dirname(new_filepath)
        dirname = os.path.basename(dirpath)

        if outline and filename == 'start':
            dirpath = os.path.dirname(new_filepath)
            dirname = os.path.basename(dirpath)
            parent = Path(dirpath).parent
            new_filepath = os.path.join(parent, f'{dirname}.md')
            if os.path.exists(new_filepath):
                print(f"WARNING overwriting: {new_filepath}")
            filename = os.path.splitext(os.path.basename(new_filepath))[0]

        os.makedirs(os.path.dirname(new_filepath), exist_ok=True)

        markdown_text = DokuWiki2MarkDown._dokuwiki_to_markdown(
                dokuwiki_text=dokuwiki_text,
                codeblk_lang=lang,
                timestamps=ts,
                codeblk_filename=codeblk_filename,
                outline=outline,
                filename=filename,
                dirpath=dirpath
            )

        with open(new_filepath, 'w') as f:
            print(f"Saving: {new_filepath}")
            f.write(markdown_text)

    @staticmethod
    def convert_directory(directory, lang, ts, codeblk_filename, outputpath, outline):
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.txt'):
                        DokuWiki2MarkDown.convert_file(
                                filepath=os.path.join(root, file),
                                lang=lang,
                                ts=ts,
                                codeblk_filename=codeblk_filename,
                                outputpath=outputpath,
                                outline=outline
                            )

        except NotADirectoryError:
            print(f"Error: Directory {directory} not found.")

    @staticmethod
    def _dokuwiki_to_markdown(dokuwiki_text, codeblk_lang, timestamps, codeblk_filename=False, outline=False, filename=None, dirpath=None):

        DokuWiki2MarkDown.codeblks = []
        # Remove timestamps if elected
        if not timestamps:
            dokuwiki_text = DokuWiki2MarkDown._rm_timestamp(dokuwiki_text)
        dokuwiki_text = DokuWiki2MarkDown._extract_codeblocks(dokuwiki_text, codeblk_lang, codeblk_filename)
        dokuwiki_text = DokuWiki2MarkDown._extract_indentcode(dokuwiki_text, codeblk_lang)
        dokuwiki_text = DokuWiki2MarkDown._extract_monospaced(dokuwiki_text)
        dokuwiki_text = DokuWiki2MarkDown._extract_links(dokuwiki_text, outline, dirpath)
        dokuwiki_text = DokuWiki2MarkDown._extract_rawlinks(dokuwiki_text)

        # Transform the rest ()
        # - bold and block quotes share the same syntax in DokuWiki and MarkDown
        transforms = [
            DokuWiki2MarkDown._tr_headers,
            DokuWiki2MarkDown._tr_italic,
            DokuWiki2MarkDown._tr_underline,
            DokuWiki2MarkDown._tr_strikethrough,
            DokuWiki2MarkDown._tr_images,
            DokuWiki2MarkDown._tr_footnotes,
            DokuWiki2MarkDown._tr_tables,
            DokuWiki2MarkDown._tr_lists,
            DokuWiki2MarkDown._tr_backslashes,
            DokuWiki2MarkDown._tr_linebreaks,
            DokuWiki2MarkDown._rm_single_space_at_line_end,
            DokuWiki2MarkDown._rm_nowiki,
            DokuWiki2MarkDown._rm_newlines,
        ]
        dokuwiki_text = reduce(lambda text, func: func(text), transforms, dokuwiki_text)

        if outline:
            dokuwiki_text = DokuWiki2MarkDown._tr_outline_pagetitle(dokuwiki_text, filename)

        # Insert code blocks back into doc
        for (unique_id, codeblk) in DokuWiki2MarkDown.codeblks:
            dokuwiki_text = dokuwiki_text.replace(unique_id, codeblk)

        return dokuwiki_text

    @staticmethod
    def _store_codeblock(code_block):
        unique_id = '{' + str(uuid.uuid4()) + '}'
        DokuWiki2MarkDown.codeblks.append((unique_id, code_block))
        return unique_id

    @staticmethod
    def _tr_outline_pagetitle(text: str, file) -> str:
        # Outline requires the page heading to match the filename exactly
        return re.sub(rf"^# *([^\n]+)", rf"# {file}\n\n> Original Heading: \1\n", text)

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
    def _extract_monospaced(text: str) -> str:
        def replace_block(match):
            block = DokuWiki2MarkDown._tr_monospaced(match.group(1))
            block = DokuWiki2MarkDown._rm_nowiki(block)
            unique_id = DokuWiki2MarkDown._store_codeblock(block)
            return unique_id

        return re.sub(r'(\'\'.*?\'\')', replace_block, text)

    @staticmethod
    def _tr_monospaced(text: str) -> str:
        return re.sub(r'\'\'(.*?)\'\'', r'`\1`', text)

    @staticmethod
    def _tr_strikethrough(text: str) -> str:
        return re.sub(r'<del>(.*?)</del>', r'~~\1~~', text)

    @staticmethod
    def _extract_links(text: str, outline=False, dirpath='') -> str:
        def replace_link(match):
            link = DokuWiki2MarkDown._tr_links(match.group(1), outline, dirpath)
            unique_id = DokuWiki2MarkDown._store_codeblock(link)
            return unique_id

        return re.sub(r'(\[\[[^|]*?(\|(.*?)?)\]\])', replace_link, text, flags=re.DOTALL)

    @staticmethod
    def _tr_links(text: str, outline=False, dirpath='') -> str:
        def replace_link(match):
            url = match.group('url').strip()
            title = match.group('title')
            link = ''

            def fix_internal_link(url):
                '''
                translate some special internal page links
                '''
                # two levels up should be enough
                if re.match(r'..:..:(#.*)?$', url):
                    dirname = os.path.basename(Path(dirpath).parent.parent)
                    return re.sub(r'^..:..:(#.*)?$', rf'../../../{dirname}.md', url)
                # one level up
                if re.match(r'..:(#.*)?$', url):
                    dirname = os.path.basename(Path(dirpath).parent)
                    return re.sub(r'^..:(#.*)?$', rf'../../{dirname}.md', url)
                # current dir
                if re.match(r'^.:(#.*)?$', url):
                    dirname = os.path.basename(dirpath)
                    return re.sub(r'^.:(#.*)?$', rf'../{dirname}.md', url)

                # remove #search part
                url = re.sub(r'^([^#]+?)(#.*)?$', rf'\1', url)
                # convert path separators
                url = re.sub(r':', r'/', url)
                if url.find('/') >= 0:
                    # add initial slash for absolute links: 'page/' => '/page/'
                    url = re.sub(r'^([^./])', rf'/\1', url)
                else:
                    # add initial dotslash for relative links: 'page' => './page'
                    url = re.sub(r'^([^./])', rf'./\1', url)
                # add slash between dots and page name: '.page' => './page'
                url = re.sub(r'^(\.+)([^./])', rf'\1/\2', url)
                # remove trailing slash
                url = url[:-1] if url.endswith('/') else url
                # add .md extension if no extension present
                url = url if re.search(r'\.\w+$', url) else f'{url}.md'

                return url

            if outline and re.match(r"([\.:].*)|([\w]+(:([^/].*)?)?)$", url):
                url = fix_internal_link(url)

            if title:
                # strip newlines from title
                title = re.sub(r'\n', ' ', title.strip())
                link = f'[{title}]({url})'
            else:
                link = f'<{url}>'
            return link

        return re.sub(r'\[\[(?P<url>[^|]*?)(\|(?P<title>.*?))?\]\]', replace_link, text, flags=re.DOTALL)

    @staticmethod
    def _extract_rawlinks(text: str) -> str:
        def replace_link(match):
            link = DokuWiki2MarkDown._tr_rawlinks(match.group(1))
            unique_id = DokuWiki2MarkDown._store_codeblock(link)
            return unique_id

        return re.sub(r'(https?://[^\s]+)', replace_link, text, flags=re.DOTALL)

    @staticmethod
    def _tr_rawlinks(text: str) -> str:
        def replace_link(match):
            url = match.group(1)
            link = f'<{url}>'
            return link

        return re.sub(r'(https?://[^\s]+)', replace_link, text, flags=re.DOTALL)

    @staticmethod
    def _tr_headers(text: str) -> str:
        for i in range(6, 1, -1):
            text = re.sub(rf" *{'=' * i} *(.*?) *{'=' * i} *\s+", rf"{'#' * (7 - i)} \1\n\n", text)
        return text

    @staticmethod
    def _extract_codeblocks(text: str, lang, codeblk_filename=False) -> str:
        def replace_block(match):
            listitem = match.group('listitem')
            listitem = '' if listitem is None else listitem
            indent = ' ' * (len(listitem) - 2) # adjust for markdown indentation
            code_block = DokuWiki2MarkDown._tr_codeblocks(match.group('block'), lang, codeblk_filename, indent)
            unique_id = DokuWiki2MarkDown._store_codeblock(code_block)
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
    def _tr_images(text: str, outline=False) -> str:
        def replace_url(match):
            url = match.group(1).strip()
            if re.match(r"([\.:])|([\w]+(:[^/]){0,1})", url):
                # quick fix for internal links
                url = re.sub(r':', r'/', url)
            return f'![{match.group(3)}]({url})'
        return re.sub(r'\{\{(.*?)(\|(.*?))?\}\}', replace_url, text)

    @staticmethod
    def _tr_footnotes(text: str) -> str:
        return re.sub(r'\(\((.*?)\)\)', r'[^1]\n\n[^1]: \1', text)

    @staticmethod
    def _tr_linebreaks(text: str) -> str:
        return re.sub(r' *\\{2} *\n', r'  \n', text)

    @staticmethod
    def _tr_backslashes(text: str) -> str:
        return re.sub(r'\\', r'\\\\', text)

    @staticmethod
    def _tr_list_items(indentation, i, line):
        def process_line(i, match, ordered_list_counter):
            spaces, bullet, rest = match.groups()
            if bullet == '-':
                ordered_list_counter += 1
                bullet = str(ordered_list_counter) + '.'
            else:
                # It's an unordered list item
                bullet = '*'
                # Reset counter when encountering an unordered list item
                ordered_list_counter = 0
            DokuWiki2MarkDown.lines[i] = '  '*indentation + bullet + rest
            return (ordered_list_counter, bullet)

        ordered_list_counter = 0

        while True:
            match = DokuWiki2MarkDown._tr_lists_match(line)
            if match:
                spaces, bullet, rest = match.groups()
                next_indentation = len(spaces) // 2 - 1
                if next_indentation > indentation:
                    (i, line) = DokuWiki2MarkDown._tr_list_items(next_indentation, i, line)
                    if i is not None:
                        continue
                elif next_indentation < indentation:
                    return (i, line)
                else:
                    (ordered_list_counter, bullet) = process_line(i, match, ordered_list_counter)
            else:
                return (None, None)

            (i, line) = DokuWiki2MarkDown._tr_lists_line()
            if i is None:
                return (None, None)

    @staticmethod
    def _tr_lists_line():
        idx = DokuWiki2MarkDown.line_idx
        if idx > len(DokuWiki2MarkDown.lines) - 1:
            return (None, None)
        line = DokuWiki2MarkDown.lines[idx]
        DokuWiki2MarkDown.line_idx = idx + 1
        return (idx, line)

    @staticmethod
    def _tr_lists_match(line):
        return re.match(r'(  \s*)([-*])(.*)', line)

    @staticmethod
    def _tr_lists(text: str) -> str:
        DokuWiki2MarkDown.lines = text.split('\n')
        DokuWiki2MarkDown.line_idx = 0

        while True:
            (i, line) = DokuWiki2MarkDown._tr_lists_line()
            if i is None:
                break
            DokuWiki2MarkDown._tr_list_items(0, i, line)

        return '\n'.join(DokuWiki2MarkDown.lines)

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
    def _extract_indentcode(input_dokuwiki, codeblk_lang):
        lines = input_dokuwiki.split('\n')  # Splitting the DokuWiki text into lines
        in_code = False  # Flag to indicate whether we are currently processing a code block
        output_markdown = []  # List to store the converted Markdown lines
        code_lines = []

        for line in lines:
            # Check if the line is indented and not a list
            if match := re.match(r'(  +)[^*\- ]', line):
                if not in_code:  # Entering code
                    in_code = True
                indent = len(match.group(1))
                code_lines.append(line[indent:]) # remove indent
            else:
                if in_code:  # Exiting code
                    in_code = False
                    lang_type = '' if codeblk_lang is None else codeblk_lang
                    code_block = f'```{lang_type}\n' + '\n'.join(code_lines) + '\n```'
                    code_lines = []
                    unique_id = DokuWiki2MarkDown._store_codeblock(code_block)
                    output_markdown.append(f'{unique_id}')
                output_markdown.append(line)
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
    parser.add_argument('-o', '--outputpath', help='Destination directory for converted files.')
    parser.add_argument('-l', '--lang', help='Codeblocks will be labeled with this Language (eg. shell).')
    parser.add_argument('-T', '--timestamps', dest='timestamps', action='store_true',
                        help='Keep textual timestamps in documents. (Default is to remove timestamps)')
    parser.add_argument('-c', '--codefile', dest='codefile', action='store_true',
                        help='Add code-block file name in code block header. (Default is to remove code-block file name)')
    parser.add_argument('-O', '--outline', dest='outline', action='store_true',
                        help='Make compatible with Outline Wiki')

    args = parser.parse_args()
    dw2md = DokuWiki2MarkDown()
    if args.file:
        dw2md.convert_file(args.file, args.lang, args.timestamps, args.codefile, args.outputpath, args.outline)
    elif args.directory:
        dw2md.convert_directory(args.directory, args.lang, args.timestamps, args.codefile, args.outputpath, args.outline)


if __name__ == '__main__':
    main()
