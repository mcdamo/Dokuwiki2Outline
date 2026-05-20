#!/usr/bin/env python3

import argparse
from lib import DokuwikiConverter


class Converter:

    def __init__(self):
        parser = argparse.ArgumentParser(description='Convert Dokuwiki to Markdown.')
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-f', '--file', help='File to convert.')
        group.add_argument('-d', '--dir', help='Directory of files to convert.')
        parser.add_argument('-o', '--output-path', dest='output_path', help='Destination directory for converted files.')
        parser.add_argument('-l', '--lang', help='Codeblocks will be labeled with this Language (eg. shell).')
        parser.add_argument('-T', '--timestamps', dest='timestamps', action='store_true',
                            help='Keep textual timestamps in documents. (Default is to remove timestamps)')
        parser.add_argument('-c', '--codefile', dest='codefile', action='store_true',
                            help='Add render the `filename` option from Dokuwiki code blocks. (Default is to remove)')
        parser.add_argument('--outline', dest='outline', action='store_true',
                            help='Additional tweaks for Outline Wiki (internal links, page titles, etc)')
        parser.add_argument('-r', '--revisions', dest='revisions', action='store_true',
                            help='Convert revisions from attic')
        parser.add_argument('--promote', dest='promote', action='store_true',
                            help='Promote headings, remove H1 and promote all others up one level')
        parser.add_argument('--dry-run', dest='dry_run', action='store_true',
                            help='Try converting all documents without saving')
        parser.add_argument('--debug', dest='debug', action='store_true',
                            help='Debugging: print converted text')
        self.parser = parser

    def run(self):
        args = self.parser.parse_args()

        if (not args.dry_run and not args.output_path):
            self.parser.error('The following arguments are required: -o, --output-path')

        dc = DokuwikiConverter(output_path=args.output_path, codeblock_lang=args.lang, timestamps=args.timestamps, codeblock_filename=args.codefile, outline=args.outline, promote=args.promote, revisions=args.revisions, dry_run=args.dry_run, debug=args.debug)

        if args.file:
            dc.convert_file(args.file)
        elif args.dir:
            dc.convert_directory(args.dir)


if __name__ == '__main__':
    c = Converter()
    c.run()
