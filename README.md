# Dokuwiki2Outline

## About

I wrote this to migrate from [DokuWiki](https://www.dokuwiki.org/dokuwiki) to [Outline Wiki](https://github.com/outline/outline/).

My goal was to retain all internal links between pages as well as importing all previous revisions.

There are two components to this library that can be run independently:

- **DokuwikiConverter** converts from DokuWiki syntax to Markdown.
- **OutlineImporter** pushes an entire DokuWiki site to an Outline collection.

## Prerequisites

Python3 and dependencies listed in [requirements.txt](requirements.txt). These may be installed and run from a venv.

Outline >= v1.7.0 for importing internal links as mentions

Custom Outline dev build to import revisions (read _Import revisions_ section below)

## DokuwikiConverter

This can be used to transform a DokuWiki site to Markdown.

### General syntax

Have a look at [syntax.md](syntax.md), which is the official [DokuWiki Syntax](https://www.dokuwiki.org/wiki:syntax) file converted to Markdown using this utility.

The following syntax is well supported:

- Headers (all levels) `====== H1 ======`
- Italic `//italic//`
- Bold `**bold**`
- Monospaced `` `mono` ``
- Strikethrough `<del>strikethrough</del>`
- Code blocks and indented blocks `<code>`
- Lists - including nested lists
- External Links `[[https://example.com|Example]]`
- Tables (does not support colspan/rowspan)

Additionally images and footnotes are not fully supported.

### Special replacements

- Underline is converted to bold (Markdown does not have underline syntax)
- Blocks wrapped in strikethrough: DokuWiki treats this like `<nowiki>`, the converter splits the lines and applies strikethrough to each line.
- Code blocks preserve the `syntax` field and can optionally insert the `filename` field above the block.

  ```
  <code xml filename.xml><xml /></code>
  ```

  Becomes

  ````
  `filename.xml`
  ```xml
  <xml />
  ```
  ````

- Indented monospace is converted to code blocks.
- Raw links `https://example.com` are converted to Markdown raw links `<https://example.com>`.
- `<nowiki>` tags are removed.

### Outline only replacements

- H1 heading is renamed to match the filename, existing H1 heading is inserted as a blockquote. This is to support seamless Outline import.

### Usage

DokuwikiConverter can run on individual \*.txt files or a complete site dump from a Dokuwiki installation (use the `/data/pages` folder)

```bash
# Single file
./converter.py -f syntax.txt -o ./

# All files in pages/ to pages_md/, preserving the folder structure
./converter.py -d dokuwiki/pages -o pages_md/
```

### More options

```text
$ python3 converter.py --help

usage: converter.py [-h] (-f FILE | -d DIR) [-o OUTPUT_PATH] [-l LANG] [-T] [-c] [--outline] [-r] [--promote] [--dry-run] [--debug]

Convert Dokuwiki to Markdown.

options:
  -h, --help            show this help message and exit
  -f, --file FILE       File to convert.
  -d, --dir DIR         Directory of files to convert.
  -o, --output-path OUTPUT_PATH
                        Destination directory for converted files.
  -l, --lang LANG       Codeblocks will be labeled with this Language (eg. shell).
  -T, --timestamps      Keep textual timestamps in documents. (Default is to remove timestamps)
  -c, --codefile        Add render the `filename` option from Dokuwiki code blocks. (Default is to remove)
  --outline             Skip additional tweaks for Outline Wiki (internal links, page titles, etc)
  -r, --revisions       Convert revisions from attic
  --promote             Promote headings, remove H1 and promote all others up one level
  --dry-run             Try converting all documents without saving
  --debug               Debugging: print converted text
```

## OutlineImporter

This can import pages to Outline, either from converted Markdown files or directly from the original DokuWiki files by doing inline conversion.

By using the data from DokuWiki it can also import all revisions into Outline (_see notes below_)

### Prerequisites

You should have an Outline instance and obtain an [API key](https://docs.getoutline.com/s/guide/doc/api-1rEIXDfLF6). Read the [Outline docs](https://docs.getoutline.com/s/hosting/doc/docker-7pfeLP5a8t) for information about setting up your own instance.

The API Key and URL for your Outline instance can be entered on the command line in `--host` and `--token` or by editing [config.ini](config.ini.sample).

### Usage

```bash
# Single file
./importer.py -f <syntax.txt|syntax.md>

# All files in pages
./importer.py -d dokuwiki/pages
```

### More options

```text
$ python3 importer.py --help

usage: importer.py [-h] (-f FILE | -d DIR) [-s SERVER] [-t TOKEN] [-r] [--dry-run] [--promote] [--debug] [--debug-path DEBUG_PATH] [--pause] [-m MAPPING]

Import Dokuwiki Outline.

options:
  -h, --help            show this help message and exit
  -f, --file FILE       File to import.
  -d, --dir DIR         Directory of files to import.
  -s, --server SERVER   Outline server url, like: http://localhost:3000
  -t, --token TOKEN     Outline api token
  -r, --revisions       Import all revisions
  --dry-run             Try scanning all documents without importing to Outline
  --promote             Promote headings: move H1 to document title and promote all other headings up one level
  --debug               Debugging
  --debug-path DEBUG_PATH
                        Debugging: start import from a specific path in the site, useful for testing imports on a subset of documents
  --pause               Pause at each step for user confirmation, useful for testing
  -m, --mapping MAPPING
                        Mapping file.csv to translate internal links
```

### Import revisions

Importing revisions is not natively supported in Outline, bulk document updates are debounced and will be stored as a single revision.

To support importing revisions you must run custom code branch for the import. Once it is imported you can switch back to production branch.

- [Feature request](https://github.com/outline/outline/discussions/11892)
- [Pull request](https://github.com/outline/outline/pull/11893)

You will need both the `pages` and `attic` folders from the DokuWiki data.

### Internal page links

#### Broken links

Do a dry-run to print the list of broken links to CSV:

```
python3 importer.py -d dokuwiki/pages [--revisions] --dry-run > broken_links.csv
```

To fix links due to moved pages or mistakes you can provide a new mapping CSV from old to new URL:

```csv
bork/page,working/page
```

Run with mapping to confirm the links are fixed:

```
python3 importer.py ... --mapping mymap.csv
```

## Acknowledgements

https://github.com/mm503/Dokuwiki2Markdown for the original DokuWiki2MarkDown converter that this was built on.

https://github.com/hyponet/outline-importer for the starting point of the Outline Importer.
