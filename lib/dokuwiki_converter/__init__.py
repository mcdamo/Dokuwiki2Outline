import re
import gzip
import os
from pathlib import Path

from .doku2md import Dokuwiki2Markdown

class DokuwikiConverter:

    def __init__(self, codeblock_lang=None, timestamps=False, codeblock_filename=False, outline=False, promote=False, revisions=False, link_mentions=False, dry_run=False, output_path=None, debug=False):
       
        self.codeblock_lang = codeblock_lang
        self.timestamps = timestamps
        self.codeblock_filename = codeblock_filename
        self.outline = outline
        self.promote = promote
        self.revisions = revisions
        self.link_mentions = link_mentions
        self.dry_run = dry_run
        self.output_path = output_path if output_path else ''
        self.debug = debug

        self.doku2md = Dokuwiki2Markdown()

    def get_pagetitle(self, text, md=False):
        if md:
            if match := re.match(rf"^# *(.*?) *\n", text):
                return match.group(1)
        if match := re.match(rf"^====== *(.*?) *=+ *\s*\n", text):
            return match.group(1)
        return None

    def get_stored_mentions(self):
        # this is populated after document is converted
        return self.doku2md.blockstore['mention']

    @staticmethod
    def restore_mentions(text: str, mentions):
        # Insert links back into doc
        for unique_id, (url, title) in mentions.items():
            text = text.replace(unique_id, f'**{title}** {url}')
        return text

    def convert_text(self, text, filename=None, dirpath=None, page_moved=False):

        text_md = self.doku2md.convert(text, filename=filename, dirpath=dirpath, page_moved=page_moved, codeblock_lang=self.codeblock_lang, timestamps=self.timestamps, codeblock_filename=self.codeblock_filename, outline=self.outline, promote=self.promote, link_mentions=self.link_mentions)
        if self.debug:
            print(text_md)
        return text_md

    def convert_file(self, filepath):
        dokuwiki_text = self._read_file(filepath)

        filepath = filepath.removesuffix('.gz') if self.revisions else filepath

        new_filepath = os.path.splitext(os.path.join(self.output_path, filepath))[0] + '.md'
        timestamp_suffix = re.sub(r'.*(\.[0-9]+)$', r'\1', new_filepath) if self.revisions else ''
        orig_filename = orig_filename.removesuffix(timestamp_suffix) if self.revisions else os.path.splitext(os.path.basename(new_filepath))[0]

        orig_dirpath = os.path.dirname(new_filepath)
        orig_dirname = os.path.basename(orig_dirpath)
        page_moved = False

        if self.outline and orig_filename == 'start':
            parent = Path(orig_dirpath).parent
            new_filepath = os.path.join(parent, f'{orig_dirname}{timestamp_suffix}.md')
            if os.path.exists(new_filepath):
                print(f"WARNING overwriting: {new_filepath}")
            filename = os.path.splitext(os.path.basename(new_filepath))[0]
            page_moved = True
        else:
            filename = orig_filename + timestamp_suffix

        if not self.dry_run:
            os.makedirs(os.path.dirname(new_filepath), exist_ok=True)

        text_md = self.doku2md.convert(
                dokuwiki_text,
                filename=filename,
                dirpath=orig_dirpath,
                page_moved=page_moved,
                codeblock_lang=self.codeblock_lang,
                timestamps=self.timestamps,
                codeblock_filename=self.codeblock_filename,
                outline=self.outline,
                promote=self.promote,
            )
        if self.debug:
            print(text_md)

        if not self.dry_run:
            with open(new_filepath, 'w', encoding='utf-8') as f:
                print(f"Saving: {new_filepath}")
                f.write(text_md)

    def convert_directory(self, directory):
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.txt') or file.endswith('.txt.gz'):
                        self.convert_file(filepath=os.path.join(root, file))

        except NotADirectoryError:
            print(f"Error: Directory {directory} not found.")

    def _read_file(self, filepath):
        if filepath.endswith('.gz'):
            with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                dokuwiki_text = f.read()
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                dokuwiki_text = f.read()
        # except FileNotFoundError:
        return dokuwiki_text
