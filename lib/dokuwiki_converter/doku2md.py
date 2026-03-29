import re
import uuid
from functools import reduce

class Dokuwiki2Markdown:
    # Internal variables
    block_secret = 'a426289c1237fb3b963b0c0a4458b838'
    blockstore = {}
    lines = []
    line_idx = 0
    # Args
    filename = None
    dirpath = None
    codeblock_lang = None
    timestamps = False
    codeblock_filename = False
    outline = False
    promote = False
    page_moved = False
    link_mentions = False

    def convert(self, text, codeblock_lang=None, timestamps=False, codeblock_filename=False, outline=False, filename=None, dirpath=None, page_moved=False, promote=False, link_mentions=False):
        self.codeblock_lang = codeblock_lang
        self.timestamps = timestamps
        self.codeblock_filename = codeblock_filename
        self.outline = outline
        self.promote = promote
        self.filename = filename
        self.dirpath = dirpath
        self.page_moved = page_moved
        self.link_mentions = link_mentions

        self.blockstore = {
            'code': {},
            'mono': {},
            'indent': {},
            'link': {},
            'strike': {},
            'mention': {},
        }

        # the order of these matter:
        transforms = [
            self._extract_indentblocks,
            self._extract_codeblocks,
            self._extract_monospaced,
            self._extract_strikethrough,
            self._extract_links,
            self._extract_rawlinks,
            self._tr_headers,
            self._tr_italic,
            self._tr_underline,
            self._tr_images,
            self._tr_footnotes,
            self._tr_tables,
            self._tr_lists,
            self._tr_backslashes,
            self._tr_linebreaks,
            self._rm_single_space_at_line_end,
            self._rm_nowiki,
            self._rm_newlines,
        ]

        text = reduce(lambda txt, func: func(txt), transforms, text)

        if self.outline:
            text = self._tr_outline_pagetitle(text, filename)

        if not self.timestamps:
            text = self._rm_timestamp(text)

        text = self._restore_strikethrough(text)
        text = self._restore_indentblocks(text)
        text = self._restore_codeblocks(text)
        text = self._restore_monospaced(text)
        text = self._restore_links(text)

        return text
    
    def _generate_secret_prefix(self, prefix):
        return f'{self.block_secret}:{prefix}:'

    def _generate_secret_block(self, prefix):
        return '<' + self._generate_secret_prefix(prefix) + str(uuid.uuid4()) + '>'

    def _store_codeblock(self, block, key=None, params=None):
        if params is None:
            params = {}
        key = self._generate_secret_block('code') if key is None else key
        self.blockstore['code'][key] = (block, params)
        return key

    def _store_indentblock(self, block, key=None, params=None):
        if params is None:
            params = {}
        key = self._generate_secret_block('indent') if key is None else key
        self.blockstore['indent'][key] = (block, params)
        return key

    def _store_link(self, link, key=None):
        key = self._generate_secret_block('link') if key is None else key
        self.blockstore['link'][key] = link
        return key

    def _store_mention(self, link, key=None):
        key = self._generate_secret_block('mention') if key is None else key
        self.blockstore['mention'][key] = link
        return key

    def _store_monospaced(self, block, key=None):
        key = self._generate_secret_block('mono') if key is None else key
        self.blockstore['mono'][key] = block
        return key

    def _store_strikethrough(self, block, key=None):
        key = self._generate_secret_block('strike') if key is None else key
        self.blockstore['strike'][key] = block
        return key

    def _restore_codeblocks(self, text: str):
        # Insert code blocks back into doc
        for unique_id, (codeblock, params) in self.blockstore['code'].items():
            text = text.replace(unique_id, codeblock)
        return text

    def _restore_indentblocks(self, text: str):
        # Insert indented code back into doc
        for unique_id, (codeblock, params) in self.blockstore['indent'].items():
            text = text.replace(unique_id, codeblock)
        return text

    def _restore_monospaced(self, text: str):
        # Insert monospaced back into doc
        for unique_id, codeblock in self.blockstore['mono'].items():
            text = text.replace(unique_id, codeblock)
        return text

    def _restore_links(self, text: str):
        # Insert links back into doc
        for unique_id, link in self.blockstore['link'].items():
            text = text.replace(unique_id, link)
        return text

    def _restore_strikethrough(self, text: str):
        # Insert deleted blocks back into doc
        for unique_id, block in self.blockstore['strike'].items():
            text = text.replace(unique_id, block)
        return text

    def _tr_outline_pagetitle(self, text: str, file) -> str:
        # Outline requires the page heading to match the filename exactly
        if self.promote:
            # remove first H1
            return re.sub(rf"^# *([^\n]+)", rf"", text)
        return re.sub(rf"^# *([^\n]+)", rf"# {file}\n\n> Original Heading: \1\n", text)

    def _rm_timestamp(self, text: str) -> str:
        return re.sub(r' *Created \w+ \d{2} \w+ \d{4}\n', '', text)

    def _tr_italic(self, text: str) -> str:
        return re.sub(r'//(.*?)//', r'*\1*', text)

    def _tr_underline(self, text: str) -> str:
        # Underline (not supported in Markdown, converted to bold)
        return re.sub(r'__(.*?)__', r'**\1**', text)

    def _extract_monospaced(self, text: str) -> str:
        def replace_block(match):
            block = self._tr_monospaced(match.group(1))
            block = self._rm_nowiki(block)
            unique_id = self._store_monospaced(block)
            return unique_id

        return re.sub(r'(\'\'.*?\'\')', replace_block, text)

    def _tr_monospaced(self, text: str) -> str:
        return re.sub(r'\'\'(.*?)\'\'', r'`\1`', text)

    def _extract_strikethrough(self, text: str) -> str:
        def replace_block(match):
            block = match.group(1)
            block = self._tr_links(block)
            block = self._tr_strikethrough(block)
            unique_id = self._store_strikethrough(block)
            return unique_id

        return re.sub(r'(<del>.*?<\/del>)', replace_block, text, flags=re.DOTALL)

    def _tr_strikethrough(self, text: str) -> str:
        # DokuWiki allows strikethrough spanning newlines, Markdown does not.
        def handle_newlines(match):
            lines = match.group(1).split('\n')
            output = []
            for line in lines:
                if line.strip() != '':
                    output.append('~~' + line + '~~')
                else:
                    output.append('')
            return '\n'.join(output)

        return re.sub(r'<del>(.*?)</del>', handle_newlines, text, flags=re.DOTALL)

    def _extract_links(self, text: str) -> str:
        def replace_link(match):
            if self.link_mentions:
                unique_id = self._tr_links(match.group(1), extract=True)
                return unique_id
            link = self._tr_links(match.group(1))
            unique_id = self._store_link(link)
            return unique_id

        return re.sub(r'(\[\[[^|\]]+(\|([^]]+)?)?\]\])', replace_link, text, flags=re.DOTALL)

    def _tr_links(self, text: str, outline=None, dirpath=None, page_moved=None, extract=False) -> str:
        outline = self.outline if outline is None else outline
        dirpath = self.dirpath if dirpath is None else dirpath
        page_moved = self.page_moved if page_moved is None else page_moved

        def replace_link(match):
            url = match.group('url').strip()
            title = match.group('title')
            link = ''

            def clean_title(title):
                # strip newlines from title
                title = re.sub(r'[\s]+', ' ', title.strip())
                # escape special characters
                title = re.sub(r'\$', r'\$', title)
                return title

            def fix_internal_link(url):
                '''
                translate some special internal page links
                '''
                original_url = url

                def build_url_components(path):
                    dir_comps = dirpath.rstrip('/').split('/')
                    components = path.lower().split(':')
                    # special handling of 'index' pages:
                    if components[-1] == 'start':
                        components[-1] = ''
                    if components[0] == '.':
                        # relative link
                        special = False
                        if path.strip('.:') == '':
                            # special relative link
                            special = True
                        if components[-1] == '':
                            if special:
                                return dir_comps
                            return dir_comps+components[1:-1]

                        return dir_comps + components[1:]

                    if components[0] == '..':
                        if path.strip('.:') == '':
                            # special relative link
                            return dir_comps[:-1]
                        del components[0]
                        if components[-1] == '':
                            # ends with dir
                            del components[-1]
                        #if page_moved:
                        return dir_comps[:-1] + components

                    if path[0] == '.':
                        # special relative page link
                        components[0] = components[0][1:] # remove dot prefix from path
                        return dir_comps + components

                    if ':' in path:
                        # absolute link
                        if components[0] != '':
                            components[:0] = [''] # unshift
                        if components[-1] == '':
                            # ends with dir
                            del components[-1]
                        return components
                    else:
                        # link to page
                        return dir_comps + components

                #print(f'url: {url}  dirpath: {dirpath}')
                if match := re.match(r'([^#]*)(#.*)?$', url):
                    path = match.group(1)
                    title = ''
                    if path:
                        components = build_url_components(path)
                        title = components[-1]
                        if '.' not in components[-1] and not self.link_mentions:
                            # don't need the extensions for mentions
                            components[-1] += '.md'
                        url = '/'.join(components)
                    else:
                        raise Exception(f'No path created for url: {original_url}')
                    return (url, title)
                raise Exception(f'No path matched in url: {original_url}')

            if outline and re.match(r"([\.:].*)|([\w]+(:([^/].*)?)?)$", url):
                # always include a title for internal links
                (url, _title) = fix_internal_link(url)
                title = title if title else _title

                title = clean_title(title) if title else title

                if (self.link_mentions):
                    # this saves the internal link for later
                    # so that we can convert to Outline DocIDs
                    unique_id = self._store_mention((url, title, text))
                    return unique_id

            if title:
                title = clean_title(title)
                link = f'[{title}]({url})'
            else:
                link = f'<{url}>'
            if extract:
                unique_id = self._store_link(link)
                return unique_id
            return link

        return re.sub(r'\[\[(?P<url>[^|\]]*?)(\|(?P<title>[^\]]+)?)?\]\]', replace_link, text, flags=re.DOTALL)

    def _extract_rawlinks(self, text: str) -> str:
        def replace_link(match):
            link = self._tr_rawlinks(match.group(1))
            unique_id = self._store_link(link)
            return unique_id

        return re.sub(r'(?<!{{rss>)(https?://[^\s]+)', replace_link, text, flags=re.DOTALL)

    def _tr_rawlinks(self, text: str) -> str:
        def replace_link(match):
            url = match.group(1)
            link = f'<{url}>'
            return link

        return re.sub(r'(https?://[^\s]+)', replace_link, text, flags=re.DOTALL)

    def _tr_headers(self, text: str, promote=None) -> str:
        promote = self.promote if promote is None else promote
        for i in range(6, 1, -1):
            j = i
            if promote and i < 6:
                j = i + 1
            text = re.sub(rf" *{'=' * i} *(.*?) *=+ *\s*\n", rf"{'#' * (7 - j)} \1\n\n", text)
        return text

    def _extract_indentblocks(self, text):

        lines = text.split('\n')  # Splitting the DokuWiki text into lines
        in_indent = False  # Flag to indicate whether we are currently processing a indent block
        in_code = False
        output_markdown = []  # List to store the converted Markdown lines
        code_lines = []

        in_del = False
        for line in lines:
            if in_code:
                if f'</{in_code}>' in line:
                    in_code = False
                output_markdown.append(line)
            # Check if the line is indented and not a list
            elif match := re.match(r'^(  +)[^*\- ]', line):
                if not in_indent:  # Entering code
                    in_indent = True
                code_lines.append(line[2:]) # remove indent
            else:
                if in_indent:  # Exiting indent
                    in_indent = False
                    code_block = '```\n' + '\n'.join(code_lines) + '\n```\n' if not in_del else '~~\n~~'.join(code_lines)
                    code_lines = []
                    unique_id = self._store_indentblock(code_block, params={ 'delete_wrapper': in_del})
                    output_markdown.append(f'{unique_id}')
                elif match := re.match(r'<(code|file)[^>]*>', line):
                    in_code = match.group(1)
                output_markdown.append(line)

            a = line.find('<del>')
            b = line.find('</del>')
            if (a > b):
                in_del = True
            elif (a < b):
                in_del = False
        text = '\n'.join(output_markdown)
        return text

    def _extract_codeblocks(self, text: str, lang=None, filename=None, indent=None) -> str:
        def replace_block(match):
            listitem = '' if 'listitem' not in match.groupdict() else match.group('listitem')
            listitem = '' if listitem is None else listitem
            indent = ' ' * (len(listitem) - 2) # adjust for markdown indentation
            del1 = bool('del' in match.groupdict() and match.group('del'))
            del2 = bool('del2' in match.groupdict() and match.group('del2'))
            pre = '' if 'pre' not in match.groupdict() else match.group('pre').strip()
            post = '' if 'post' not in match.groupdict() else match.group('post').strip()
            postdel = '' if 'postdel' not in match.groupdict() else match.group('postdel')
            postdel = '' if postdel is None else postdel.strip()
            # if listitem or pre: newline
            prefix_newline = pre != ''
            tr_codeblock = self._tr_codeblocks(match.group('block'), lang=lang, filename=filename, indent=indent, delete_wrapper=del1, prefix_newline=(prefix_newline))
            unique_id = self._store_codeblock(tr_codeblock, params={'delete_wrapper': del1, 'indent': indent})
            if pre and del1:
                pre = f'<del>{pre}</del>'

            if postdel and del2:
                postdel = f'<del>{postdel}</del>'
            post_indent = ''
            if post != '':
                post_indent = '\n' + indent

            return f'{listitem}{pre}{unique_id}{postdel}{post_indent}{post}'

        ## these regex substitutions are segmented this way for performance reasons

        # match listitems
        text = re.sub(r'(?P<listitem>  +[*-] +)(?P<del><del>)?(?P<pre>[^\n<]*)(?P<block><(?:code|file)[^>]*>.*?<\/(?:code|file)>)(?P<del2>(?P<postdel>[^<]*)<\/del>)?(?P<post>[^\n]*)', replace_block, text, flags=re.DOTALL)

        # match deleted blocks
        text = re.sub(r'(?P<del><del>)(?P<pre>.*?)(?P<block><(?:code|file)[^>]*>.*?<\/(?:code|file)>)\s*(?P<del2>(?P<postdel>.*?)<\/del>)', replace_block, text, flags=re.DOTALL)

        # match all other blocks, unless wrapped in nowiki %% tags
        text = re.sub(r'(?<!......%%|<nowiki>)(?P<block><(?:code|file)[^>]*>.*?<\/(?:code|file)>)(?!%%|<\/nowiki>)', replace_block, text, flags=re.DOTALL)

        return text

    def _tr_codeblocks(self, text: str, lang=None, filename=None, indent='', delete_wrapper=False, prefix_newline=False) -> str:
        lang = self.codeblock_lang if lang is None else lang
        filename = self.codeblock_filename if filename is None else filename

        def replace_block(match):
            content = match.group('content')
            if delete_wrapper:
                # inside strikethrough, so don't wrap in code block or newlines
                # strip empty lines
                # wrap in additional spaces to avoid concatenating with adjacent delete blocks
                return ' ~~`' + '`~~\n~~`'.join(filter(lambda x: x.strip(), content.splitlines())) + '`~~ '
            lang_type = '' if match.group('lang') is None else match.group('lang')
            lang_type = lang_type if lang is None else lang
            content = re.sub(r'^', indent, content, flags=re.MULTILINE)
            content = content.removeprefix('\n').rstrip()
            file_block = f'`{indent}{match.group('filename')}`\n\n' if filename and match.group('filename') else ''
            prefix = '\n' if prefix_newline else ''
            prefix_indent = indent if prefix_newline else ''
            ret = f'{prefix}{file_block}{prefix_indent}```{lang_type}\n{content}\n{indent}```'

            return ret

        return re.sub(r'<(?:code|file)(\s+(?P<lang>[^> ]+))?(\s+(?P<filename>[^> ]+))?[^>]*>(?P<content>.+?)<\/(?:code|file)>', replace_block, text, flags=re.DOTALL)

    def _tr_images(self, text: str) -> str:
        def replace_url(match):
            url = match.group(1).strip()
            if re.match(r"([\.:])|([\w]+(:[^/]){0,1})", url):
                # quick fix for internal links
                url = re.sub(r':', r'/', url)
            return f'![{match.group(3)}]({url})'
        return re.sub(r'\{\{(.*?)(\|(.*?))?\}\}', replace_url, text)

    def _tr_footnotes(self, text: str) -> str:
        return re.sub(r'\(\((.*?)\)\)', r'[^1]\n\n[^1]: \1', text)

    def _tr_linebreaks(self, text: str) -> str:
        return re.sub(r' *\\{2} *\n', r'  \n', text)

    def _tr_backslashes(self, text: str) -> str:
        return re.sub(r'\\', r'\\\\', text)

    def _tr_list_items(self, indentation, i, line):
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
            self.lines[i] = '    '*indentation + bullet + rest
            return (ordered_list_counter, bullet)

        ordered_list_counter = 0
        in_list = False

        while True:
            match = self._tr_lists_match(line)
            if match:
                in_list = True
                spaces, bullet, rest = match.groups()
                next_indentation = len(spaces) // 2 - 1
                if next_indentation > indentation:
                    (i, line) = self._tr_list_items(next_indentation, i, line)
                    if i is not None:
                        continue
                elif next_indentation < indentation:
                    return (i, line)
                else:
                    (ordered_list_counter, bullet) = process_line(i, match, ordered_list_counter)
            else:
                if in_list == True:
                    # add an extra newline after the end of a list
                    self.lines[i] += '\n'
                return (None, None)

            (i, line) = self._tr_lists_line()
            if i is None:
                return (None, None)

    def _tr_lists_line(self):
        idx = self.line_idx
        if idx > len(self.lines) - 1:
            return (None, None)
        line = self.lines[idx]
        self.line_idx = idx + 1
        return (idx, line)

    def _tr_lists_match(self, line):
        return re.match(r'(  \s*)([\-\*])(.*)', line)

    def _tr_lists(self, text: str) -> str:
        self.lines = text.split('\n')
        self.line_idx = 0

        while True:
            (i, line) = self._tr_lists_line()
            if i is None:
                break
            self._tr_list_items(0, i, line)

        return '\n'.join(self.lines)

    def _tr_tables(self, input_dokuwiki):
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
                    output_markdown.append('') # newline after a table
                    in_table = False
                output_markdown.append(line)

        # no empty line found after the table, so add one:
        if (in_table):
            output_markdown.append('')
        # Join the Markdown lines into a single string and return
        text = '\n'.join(output_markdown)
        return text

    def _rm_newlines(self, text: str) -> str:
        """Remove any excessive (2+) newlines and replace with 2 \n"""
        return re.sub(r'(\n\s*){2,}', r'\n\n', text, flags=re.MULTILINE)

    def _rm_nowiki(self, text: str) -> str:
        text = re.sub(r'<nowiki>(.*?)</nowiki>', r'\1', text)
        return re.sub(r'%%(.*?)%%', r'\1', text)

    def _rm_single_space_at_line_end(self, text: str) -> str:
        return re.sub(r'(?<! ) (?! )$', '', text, flags=re.MULTILINE)
