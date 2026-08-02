# Usage

`ssg` builds a static documentation site from a directory of Markdown files.

## Building a site

From your project root, run:

```console
$ ssg build
```

This reads Markdown files from `docs/` and writes static HTML into `site/`.
Pass `-v` to list every page as it is built. The command exits non-zero if
the build produces any errors, such as broken internal links.

## Previewing a site

Build and serve the site locally with:

```console
$ ssg serve
```

The preview is available at `http://localhost:8000/`. Use `--host` and
`--port` to change the listening address, for example:

```console
$ ssg serve --host 0.0.0.0 --port 3000
```

Stop the server with <kbd>Ctrl</kbd>+<kbd>C</kbd>. Run `ssg serve` again after
editing source files; automatic rebuilds are not yet enabled.

The preview is built into a temporary directory and removed when the server
stops, so serving never touches the configured output directory.

## Configuration

Configuration is optional. To override the defaults, create a `neon-ssg.yaml`
file in the project root:

```yaml
site:
    name: "My Docs"
    url: "https://docs.example.com"

content:
    docs_root: "docs"
    site_root: "site"
```

- `site.name` is used in page titles and the site header. It defaults to the
  name of the project directory.
- `site.url` enables canonical URLs. It has no default.
- `content.docs_root` is the source directory. It defaults to `docs`.
- `content.site_root` is the build target. It defaults to `site`.

Both roots are resolved relative to the directory containing `neon-ssg.yaml`,
and may point outside it with `../`. This allows the config to live inside
the docs tree itself:

```yaml
# proj/docs/neon-ssg.yaml
content:
    docs_root: "."
    site_root: "../site"
```

When the config lives inside the docs tree, it is not copied into the built
site, and hidden files (names starting with a dot) are always skipped.

The output directory is removed and rebuilt on every build. As a safety net,
`ssg` marks its output with a `.neon-ssg` file and refuses to delete a
non-empty directory that lacks the marker, so a mistyped `site_root` cannot
wipe an unrelated directory.

## Writing pages

Every `*.md` file under the docs directory becomes a page with a
directory-style URL: `docs/guide.md` and `docs/guide/index.md` both map to
`/guide/`. All other files are copied verbatim and keep their paths.

Page titles come from the `title` metadata key when present, then the first
level-one heading, then the file name.

The following Markdown features work out of the box:

- Fenced code blocks with build-time syntax highlighting.
- Admonitions (`!!! note "Title"`) and collapsible details (`??? tip`).
- Snippets (`--8<-- "file.md"`), resolved from the docs directory.
- Mermaid diagrams in `mermaid` fenced blocks.
- Tables, and a table of contents with anchor permalinks.

Internal links between Markdown files (`[guide](../guide/index.md)`) are
rewritten to the final URLs. Links to missing files fail the build with a
`broken-link` diagnostic that suggests the closest existing file.
