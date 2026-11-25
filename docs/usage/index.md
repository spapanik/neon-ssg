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
`index.html` inside it. Inputs that map to the same output cause an error, except for competing
directory indexes as described below.
Generated navigation and Markdown links use relative directory URLs such as
`installation/` rather than links ending in `index.html`. Static hosts must
serve directory indexes for these links; the preview server redirects directory
requests without a trailing slash to the corresponding URL with one.

Files outside the documentation directory can be included explicitly:

```yaml
content:
    include:
        - src: ../LICENSE.md
          as: LICENSE.md
```

The `src` path is relative to the documentation directory and `as` is a
relative path within the documentation tree.

## Local preview

Run `ssg serve` to build into a temporary directory and serve a live preview at
`http://127.0.0.1:8000/`. Use `--host` and `--port` to change the address.
The preview uses the same build as `ssg build` and leaves the configured output
directory untouched. The browser refreshes after a successful rebuild. When a
build fails, the last successful preview remains available and an error appears
in the terminal and browser.

The server watches the project directory and external documentation and include
directories configured when it starts. Restart it after changing those paths.
Changes to `pyproject.toml` or `uv.lock` require environment synchronisation and
an explicit server restart. Press Ctrl+C to stop the server.

## Clean page URLs

By default, source names are preserved in page URLs. To remove ordering markers,
set `content.remove_prefix` and/or `content.remove_suffix` to Python regular
expressions. Each pattern is matched once at the respective end of every
Markdown filename stem and directory component; the prefix is removed first.
For example:

```yaml
content:
    remove_prefix: '\d\d[-_]'
    nav:
        - Home: 00-index.md
        - Phonology: 01-phonology/00-index.md
```

This maps those pages to `/` and `/phonology/`, while their navigation labels
remain Home and Phonology. Use single-quoted YAML strings for regular
expressions containing backslashes. A suffix such as `'-\d\d'` can be set with
`remove_suffix`. If neither setting is present, numbered names are retained.
The build fails if cleaned page paths collide (other than directory indexes)
or a component becomes empty.

Assets retain their source paths, including numbered directories. Relative
Markdown links and images pointing to known assets are adjusted to reach those
paths from the generated page. Links to Markdown pages and navigation entries
continue to use the original source paths.

## Section indexes

In a navigation group, an unlabelled entry pointing to a directory index makes
the group title a link to that page and is removed from the group's children.
For example, `Phonology: [01-phonology/00-index.md, ...]` links the Phonology
heading when the configured path cleanup identifies that file as an index. An
explicitly labelled entry such as `Overview: 01-phonology/00-index.md` remains
as a separate link and takes precedence over the automatic section link.

When a source directory has several index candidates, `index.md` takes
precedence over `README.md` after path cleanup. Among candidates of the same
kind, the lexicographically first source path wins. Other candidates are not
rendered; links to them lead to the selected index. This selection is confined
to each source directory, and other output collisions remain errors.

## Custom assets

Place site assets under `docs/assets/`, or choose a different directory name
relative to the documentation directory:

```yaml
content:
    assets: site-assets
```

The name must be a single, non-hidden directory name. It is used unchanged in
the generated site, even when page URL prefix or suffix removal is enabled.
Only files within the `img/`, `css/`, `js/` and `fonts/` subdirectories are
copied. They are copied as-is, and Markdown files in those directories are
not treated as documentation pages. Other files and subdirectories in the
assets directory are excluded. For example, an image at
`docs/site-assets/img/logo.png` can be referenced from a Markdown page as
`![Logo](site-assets/img/logo.png)` (adjust the relative path for nested
pages).

Every `.css` file under `assets/css/` is linked on each page after the built-in
styles, and every `.js` file under `assets/js/` is loaded with `defer` on each
page. Files are included in lexicographical path order within each type, and
nested directories are supported. Replace `assets` in these paths with the
configured name when using a custom directory. Paths are relative to each page,
so the generated site can be hosted beneath a URL prefix. Only add CSS and
JavaScript that should run on every page.

The generator does not compile TypeScript. An `assets/ts/` directory is
ignored and is not published. Compile TypeScript to `assets/js/` separately
before `ssg build`, for example as a CI step. During `ssg serve`, run your
TypeScript compiler in watch mode separately and configure it to write to
`assets/js/`; the preview rebuilds when the generated JavaScript changes.
TypeScript sources can instead live outside the documentation directory.

The theme can display a logo beside the site name and set a browser favicon.
Specify their paths relative to the configured asset directory's `img/`
subdirectory:

```yaml
theme:
    logo: brand/logo.svg
    favicon: favicon.ico
```

For the default asset directory, these files are `docs/assets/img/brand/logo.svg`
and `docs/assets/img/favicon.ico`. With `content.assets: site-assets`, use
`docs/site-assets/img/` instead. Both settings are optional. A configured image
that cannot be found fails the build with the setting and expected path.
