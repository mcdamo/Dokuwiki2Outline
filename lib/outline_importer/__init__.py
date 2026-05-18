import logging
import os
import gzip
import uuid
import tabulate
from datetime import datetime, timezone

from .client import ApiClient
from .finder import Finder, Document, Collection
from ..dokuwiki_converter import DokuwikiConverter

log = logging.getLogger(__name__)

class OutlineImporter:

    def __init__(self, api_server=None, token=None, dir_path=None, file_path=None, revisions=False, dry_run=False, promote=False, pause=False, debug=False, debug_path=None, link_mapping_file=None):
        self.api_server = api_server
        self.token = token
        self.dir_path = dir_path
        self.dir_prefix = dir_path if not revisions else os.path.join(dir_path, 'pages')
        self.file_path = file_path
        self.revisions = revisions
        self.dry_run = dry_run
        self.promote = promote
        self.pause = pause
        self.debug = debug
        self.debug_path = debug_path.strip('/').split('/') if debug_path else None
        self.link_mapping_file = link_mapping_file
        self.links_map = {}

        self.api_server = ApiClient(api_server, token)
        self.finder = Finder()
        self.doku2md = DokuwikiConverter(promote=self.promote, link_mentions=True, outline=True, codeblock_filename=True)
        self.broken_links = []
        self.document_links_all = []
        self.document_links_map = {} # cached document links: internal_url -> docId

    def run(self):
        if not self.dry_run:
            self.api_server.auth()

        if self.link_mapping_file:
            self.links_map = self._import_link_mapping(self.link_mapping_file)

        if self.file_path:
            self.dir_prefix = os.path.dirname(self.file_path)
            self.collection = Collection('', 'Single file')
            filename = os.path.basename(self.file_path)
            d = Document(self.file_path, title=filename, dirpath='')
            self.collection.documents[filename] = d

        else:
            self.collection = self.finder.scan(self.dir_path, revisions=self.revisions, debug_path=self.debug_path)

            if self.pause:
                input("Press Enter to view site tree...")

            log.info("[document] <#revisions>")
            self._print_collection(self.collection, '')
       
        if self.pause:
            input("Press Enter to import...")

        self._import_collection(self.collection)

        if self.debug:
            if self.pause:
                input("Press Enter to list all internal links...")
            print(','.join(("URL", "Original URL", "Document")))
            for (_doc, _orig_url, _url) in self.document_links_all:
                print(','.join((_url, _orig_url, _doc)))

        if self.broken_links:
            print("### Broken internal links:")
            print(','.join(("URL", "Original URL", "Document")))
            for (_doc, _orig_url, _url) in self.broken_links:
                print(','.join((_url, _orig_url, _doc)))


    def _import_collection(self, collection):
        cname = 'Dokuwiki Import -%s' % datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        collection.name = cname

        if not self.dry_run:
            cid = self.api_server.create_collection(collection)
        else:
            cid = uuid.uuid4()

        # first create site structure with empty pages
        # this will obtain the document ids and allow us to import revisions
        # with working internal links

        if self.dir_path:
            self._process_nested_collection(collection, cid=cid, empty_page=True)

        self._process_nested_collection(collection, cid=cid)

    def _process_nested_collection(self, collection, cid, pid=None, empty_page=False):

        # use reversed order so that documents are inserted in reverse alphabetical order (Z->A)
        # then Outline will display in the correct order because the newer documents will be on top.
        # reorder list to process pages before folders, this ensures the pages will
        # be listed after the folders in the sitemap
        docs = reversed(sorted(collection.documents.values(), key=lambda x: (not(x.collection), x.title)))
        #ordered = list(filter(lambda doc: not doc.collection, docs)) + list(filter(lambda doc: doc.collection, docs))
        for doc in docs:
            self._process_document(doc, cid=cid, pid=pid, empty_page=empty_page)

    def _read_file(self, path):
        if path.endswith('.gz'):
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                text = f.read()
        else:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        return text

    def _import_link_mapping(self, path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        mapping = {}
        for line in text.splitlines():
            if line:
                csv = line.split(',')
                mapping[csv[0].strip('/')] = csv[1].strip('/')
        return mapping

    def _import_document(self, document, is_publish=True, empty_page=False):
        """
        Import document.
        empty_page: creates empty page during structural import
        """

        text_md = ''

        if not empty_page:
            if os.path.isfile(document.path):
                text = self._read_file(document.path)
            else:
                log.info("CREATE EMPTY DOCUMENT ### %s", document.path)
                text = "(Page left intentionally blank)"
                document.timestamp = int(datetime.now().timestamp())

            md_ext = os.path.splitext(document.path)[1] == '.md'
            title = self.doku2md.get_pagetitle(text, md_ext)
            if title:
                document.title = title
            text_md = text
            if not md_ext:
                text_md = self.doku2md.convert_text(text, filename=document.filename, dirpath=document.dirpath, page_moved=document.unnested)
                text_md = self._transform_mentions(document, text_md)

        if self.dry_run:
            return str(uuid.uuid4())

        if document.doc_id:
            return self.api_server.update_document(document.doc_id, document, text_md)
        return self.api_server.create_document(document, text_md)

    def _recursive_lookup(self, collection, dcs):
        for name, doc in collection.documents.items():
            #log.debug(f'# {dcs[0]}\t=>\t{doc.filename} ?')
            if dcs[0] == doc.filename:
                # this section of the part matches.
                if len(dcs) > 1:
                    if not doc.collection:
                        # this likely means the link in Dokuwiki is broken or pages have been moved (and this is an old revision)
                        return None
                    return self._recursive_lookup(doc.collection, dcs[1:])
                return doc.doc_id

        # if we got here it means that we did not find a match
        return None

    def _transform_mentions(self, document, text_md):

        mm = self.doku2md.get_stored_mentions()
        mm2 = {}
        for (k, v) in mm.items():

            (url, _title, _orig_url) = v
            _url = url.removeprefix(self.dir_prefix).strip('/')
            if _url in self.links_map:
                log.debug("LINK MAP: %s => %s", _url, self.links_map[_url])
                _url = self.links_map[_url]
            _dcs = _url.split('/')

            # use cached lookups
            if _url in self.document_links_map:
                _doc_id = self.document_links_map[_url]
            else:
                _doc_id = self._recursive_lookup(self.collection, _dcs)
                if _doc_id:
                    self.document_links_map[_url] = _doc_id
            
            if not _doc_id:
                # log for later
                if self.debug:
                    log.warning("BROKEN LINK: %s => %s", _orig_url, _url)
                    input("Press enter to continue")
                self.broken_links.append((document.path, _orig_url, _url))
                mm2[k] = (f'`LINK:{_url}`', _title)
            else:
                self.document_links_all.append((document.path, _orig_url, _url))
                mm2[k] = ('@<mention://document/'+_doc_id+'>', _title)
        text_md = self.doku2md.restore_mentions(text_md, mm2)

        return text_md

    def _import_revision(self, document, doc_id):

        text_md = ''

        if os.path.isfile(document.path):
            text = self._read_file(document.path)
        else:
            raise Exception("Failed opening revision file:" + document.path)

        md_ext = os.path.splitext(document.path)[1] == '.md'
        title = self.doku2md.get_pagetitle(text, md_ext)
        if title:
            document.title = title
        text_md = text
        if not md_ext:
            text_md = self.doku2md.convert_text(text, filename=document.filename, dirpath=document.dirpath, page_moved=document.unnested)
            text_md = self._transform_mentions(document, text_md)

        if self.dry_run:
            return str(uuid.uuid4())

        self.api_server.create_revision(doc_id, document, text_md)

    def _create_empty_page(self, document):

        timestamp = document.timestamp - 60; # shift page creation revision earlier so that it appears as the first revision.
        ts = str(datetime.fromtimestamp(timestamp, timezone.utc))
        log.info("%s > Creating initial document (%s @ %s)", document.title, timestamp, ts)
        if self.dry_run:
            return str(uuid.uuid4())
        doc_id = self.api_server.create_document(document, '', timestamp=timestamp)
        return doc_id

    def _process_document(self, document, cid, pid=None, empty_page=False):

        if empty_page:
            document.cid = cid
            document.pid = pid
            document.doc_id = self._create_empty_page(document)

        if not empty_page:
            if not self.revisions or len(document.revisions) == 0:
                document.cid = cid
                document.pid = pid
                log.info("%s > Creating document", document.title)
                document.doc_id = self._import_document(document)

            if self.revisions:
                for i, rev in enumerate(document.revisions):
                    rev.cid = cid
                    rev.pid = pid
                    ts = str(datetime.fromtimestamp(rev.timestamp, timezone.utc))
                    log.info("%s >> Creating revision (%s @ %s) <%s>", rev.title, rev.timestamp, ts, document.doc_id)
                    self._import_revision(rev, document.doc_id)

        if document.collection:
            self._process_nested_collection(document.collection, cid, document.doc_id, empty_page=empty_page)

    def _print_collection(self, collection, prefix=''):
        idx = 0
        itemcount = len(collection.documents)
        for name, doc in collection.documents.items():
            idx += 1

            rev = f" <{len(doc.revisions)}>" if doc.revisions else ""

            if idx == itemcount and not doc.collection:
                idc = "┗━"
            else:
                idc = "┣━"
            if not doc.collection:
                log.info("%s%s%s%s", prefix, idc, doc.filename, rev)

            if doc.collection:
                if idx == itemcount:
                    tmp_prefix = prefix + "    "
                    idc = "┗━"
                else:
                    tmp_prefix = prefix + "┃  "
                log.info("%s%s%s%s", prefix, idc, doc.filename, rev)

                self._print_collection(doc.collection, tmp_prefix)
