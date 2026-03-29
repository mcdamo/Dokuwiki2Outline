import os
import re
import logging

log = logging.getLogger(__name__)

class Collection:

    def __init__(self, name, description=None):
        self.name = name
        self.description = description or ""
        self.documents = {}


class Document:
    def __init__(self, path, title=None, filename=None, dirpath=None, timestamp=None, unnested=False):
        self.title      = title
        self.path       = path       # full path to file on disk
        self.filename   = filename   # filename without extension, needed for doku2md link replacement
        self.dirpath    = dirpath    # unnested dirpath in tree, needed for doku2md link replacement
        self.unnested   = unnested   # boolean: if index (start.txt) was nested in same dir as pages
        self.timestamp  = timestamp
        self.collection = None
        self.revisions  = []
        self.pid = None
        self.cid = None
        self.doc_id = None
        if not timestamp:
            self.timestamp = int(os.path.getmtime(path))


class Finder:
    INDEX = "start.txt"

    @staticmethod
    def filename_from_revision(path):
        ret = re.sub(r'^(.*)\.[0-9]+\.txt\.gz$', r'\1', path)
        return ret

    @staticmethod
    def timestamp_from_revision(path):
        return re.sub(r'.*\.([0-9]+)\.txt\.gz$', r'\1', path)
 
    def _scan_revisions(self, collection, parent_path, in_files, unnested=False):

        if parent_path != os.path.join(self.root, "pages"):
            attic_subdirs = parent_path.removeprefix(os.path.join(self.root, "pages")+'/')
            attic_path = os.path.join(self.root, "attic", attic_subdirs)
        else:
            attic_path = os.path.join(self.root, "attic")
        log.debug(f"Scan revisions: %s", attic_path)

        file_list = os.listdir(attic_path)

        # only import revisions matching names in 'files'
        file_list = list(filter(lambda f: f != '_dummy' and self.filename_from_revision(f) in in_files and os.path.isfile(os.path.join(attic_path, f)), file_list))
        file_list.sort()

        for sub_path in file_list:
            self.count_revisions += 1
            orig_filename = self.filename_from_revision(sub_path) if not unnested else unnested
            timestamp = int(self.timestamp_from_revision(sub_path))

            if orig_filename not in collection.documents:
                d = Document(os.path.join(attic_path, sub_path), title=orig_filename, filename=orig_filename, dirpath=parent_path, unnested=unnested)
                log.debug("  Adding document: %s", orig_filename)
                collection.documents[orig_filename] = d

            # create revision
            d = Document(os.path.join(attic_path, sub_path), title=orig_filename, filename=orig_filename, dirpath=parent_path, timestamp=timestamp, unnested=unnested)
            collection.documents[orig_filename].revisions.append(d)

        return collection

    # https://stackoverflow.com/a/32656429
    def _recurse(self, parent_path, file_list, level, debug_path=None):

        log.debug("Scan documents: %s", parent_path)
        if len(file_list) == 0 \
            or (self.max_level != -1 and self.max_level <= level):
            return
        else:
            base_dir_name = os.path.basename(parent_path)
            collection = Collection(parent_path, base_dir_name)
            file_list.sort(key=lambda f: os.path.isfile(os.path.join(parent_path, f)))
            directories = []
            files = []
            for idx, sub_path in enumerate(file_list):
                self.count_pages += 1

                # ignore 'start.txt' index files here, unless we are in the root folder
                # other index files will be scanned from directories section below
                if sub_path == self.INDEX and level > 0:
                    continue

                if debug_path and level < len(debug_path) and sub_path != debug_path[level]:
                    continue

                full_path = os.path.join(parent_path, sub_path)
                if os.path.isdir(full_path): # and sub_path not in self.exf:
                    directories.append((full_path, sub_path))
                elif os.path.isfile(full_path):
                    orig_filename = os.path.splitext(sub_path)[0]
                    if self.revisions:
                        files.append(os.path.splitext(sub_path)[0]) # sanity check
                        continue
                    d = Document(full_path, title=orig_filename, filename=orig_filename, dirpath=parent_path)
                    collection.documents[orig_filename] = d

            if self.revisions and len(files) > 0:
                collection = self._scan_revisions(collection, parent_path=parent_path, in_files=files)

            for idx, (full_path, sub_path) in enumerate(directories):
                if sub_path not in collection.documents:
                    # lookup index 'start' files in subdirectories
                    start_path = os.path.join(full_path, self.INDEX)
                    start_parent = os.path.join(parent_path, sub_path)

                    if os.path.exists(start_path):
                        log.debug("Collecting nested %s from %s", self.INDEX, full_path)
                        if self.revisions:
                            collection = self._scan_revisions(collection, parent_path=start_parent, in_files=['start'], unnested=sub_path)
                        else:
                            collection.documents[sub_path] = Document(start_path, title=sub_path, filename=sub_path, dirpath=start_parent, unnested=sub_path)
                    else:
                        log.debug("Creating empty document %s in %s collection", full_path, sub_path)
                        # create empty document if non exists for this path
                        collection.documents[sub_path] = Document(full_path, title=sub_path, filename=sub_path, dirpath=parent_path)

                next_debug_path = debug_path[1:] if debug_path else None
                ret = self._recurse(parent_path=full_path, file_list=os.listdir(full_path), level=level + 1, debug_path=next_debug_path)
                if ret:
                    collection.documents[sub_path].collection = ret

            return collection

    def scan(self, path, revisions=False, debug_path=None):
        # attic may contain old revisions of documents in their old locations if they were deleted (not if they were moved)
        # scan the 'pages' to build the site structure, then scan attic to add the revisions.
        if revisions:
            if not os.path.exists(os.path.join(path, "pages")):
                raise Exception("'pages' folder not found in %s" % path)
            if not os.path.exists(os.path.join(path, "attic")):
                raise Exception("'attic' folder not found %s" % path)
        elif os.path.exists(os.path.join(path, "pages")) and os.path.exists(os.path.join(path, "attic")):
            input("Found 'pages/' and 'attic/' in %s, did you mean to use --revisions? Press Enter to continue..." % path)

        self.revisions = revisions
        self.root = path
        self.max_level = -1
        self.count_pages = 0
        self.count_revisions = 0
        self.debug_path = debug_path

        pages_path = self.root if not revisions else os.path.join(path, "pages")
        collection = self._recurse(parent_path=pages_path, file_list=os.listdir(pages_path), level=0, debug_path=self.debug_path)

        log.info("Total Pages:     %s", self.count_pages)
        log.info("Total Revisions: %s", self.count_revisions)
        log.info("Root:            %s", self.root)

        path_parts = self.root.rsplit(os.path.sep, 1)
        log.info("Home:            %s", path_parts[-1])

        return collection
