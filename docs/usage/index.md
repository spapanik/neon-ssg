# Usage

`ssg build` renders Markdown documentation into a static site. Run it from the
project directory:

```console
$ ssg build
```

By default, Markdown and assets are read from `docs/` and the site is written
to `site/`. The output directory must not overlap the source directory. A
non-empty output directory is only replaced if it contains a `.neon-ssg` marker
from an earlier build. A failed render leaves the earlier output available.

The defaults can be changed in `neon-ssg.yaml` using `content.docs_root`
and `content.site_root`. These paths are relative to the configuration
directory. Hidden files and directories in the documentation tree are skipped.

```yaml
content:
  docs_root: manual
  site_root: public
```

## Navigation

Create `neon-ssg.yaml` to set the site name and navigation. Entries point to
Markdown paths relative to the documentation directory; groups can be nested.
If navigation is omitted, all Markdown pages are listed in path order.

```yaml
site:
  name: My documentation
content:
  nav:
    - Home: README.md
    - Guides:
        - Getting started: guides/start.md
```

Markdown links to other Markdown pages are rewritten to their generated HTML
paths. Missing linked pages and navigation targets fail the build. Other files
are copied as assets. `index.md` and `README.md` produce `index.html` in their
containing directory; other Markdown files produce a directory with an
`index.html` inside it. Inputs that map to the same output cause an error.

Files outside the documentation directory can be included explicitly:

```yaml
content:
  include:
    - src: ../LICENSE.md
      as: LICENSE.md
```

The `src` path is relative to the documentation directory and `as` is a
relative path within the documentation tree. `ssg serve` and automatic reload
are not implemented yet.
