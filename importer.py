#!/usr/bin/env python3

import argparse
import configparser
import logging
import logging.config

from lib import OutlineImporter

logger = logging.getLogger(__name__)

class Importer:

    def __init__(self):
        parser = argparse.ArgumentParser(description='Import Dokuwiki Outline.')
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-f', '--file', help='File to import.')
        group.add_argument('-d', '--dir', help='Directory of files to import.')
        parser.add_argument('-s', '--server',
                            help='Outline server url, like: http://localhost:3000')
        parser.add_argument('-t', '--token',
                            help='Outline api token')
        parser.add_argument('-r', '--revisions', dest='revisions', action='store_true',
                            help='Import all revisions')
        parser.add_argument('--dry-run', dest='dry_run', action='store_true',
                            help='Try scanning all documents without importing to Outline')
        parser.add_argument('--promote', dest='promote', action='store_true',
                            help='Promote headings: move H1 to document title and promote all other headings up one level')
        parser.add_argument('--debug', dest='debug', action='store_true',
                            help='Debugging')
        parser.add_argument('--debug-path', dest='debug_path',
                            help='Debugging: start import from a specific path in the site, useful for testing imports on a subset of documents')
        parser.add_argument('--pause', dest='pause', action='store_true',
                            help='Pause at each step for user confirmation, useful for testing')
        parser.add_argument('-m', '--mapping',
                            help='Mapping file.csv to translate internal links')

        self.parser = parser

    def run(self):
        args = self.parser.parse_args()
        config = configparser.ConfigParser()

        config.read('config.ini')
        logging.config.fileConfig("logger.ini", disable_existing_loggers=False)

        server = config["OUTLINE"]["SERVER"]
        token = config["OUTLINE"]["TOKEN"]

        server = args.server if args.server else server
        token = args.token if args.token else token

        if args.dry_run:
            dry_run=True
        elif not server or not token:
            input("Server and Token not provided, press enter to to a dry-run:")
            dry_run=True
        else:
            dry_run = args.dry_run
            if server.endswith("/"):
                server = server[:-1]

        dir_path = args.dir
        if not dir_path and args.revisions:
            self.parser.error("Revisions can only be used with a directory")

        if dir_path and dir_path.endswith("/"):
            dir_path = dir_path[:-1]

        importer = OutlineImporter(
            api_server=server,
            token=token,
            dir_path=dir_path,
            file_path=args.file,
            revisions=args.revisions,
            dry_run=dry_run,
            promote=args.promote,
            pause=args.pause,
            debug=args.debug,
            debug_path=args.debug_path,
            link_mapping_file=args.mapping,
        )
        importer.run()

if __name__ == '__main__':
    i = Importer()
    i.run()
