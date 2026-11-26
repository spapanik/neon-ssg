# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], and this project adheres to [Semantic Versioning].

## [Unreleased]

## [0.2.0]

### Added

- Preview a site with `ssg serve`, rebuilding on edits and refreshing the browser
  after a successful build. Failed builds leave the last successful preview
  available.

### Changed

- Use relative directory URLs in generated links, and redirect directory
  requests without a trailing slash in the preview server.

## [0.1.0]

### Added

- Build a static documentation site from Markdown and assets with `ssg build`.
- Configure site metadata, source and output directories, nested navigation
  and included files through `neon-ssg.yaml`.
- Rewrite links to Markdown pages, and report missing pages and conflicting
  output paths.
- Stage builds before replacing marked output, preserving the previous site if
  rendering fails.
- Resolve scalar configuration from layered files, environment variables and
  defaults, with typed validation and diagnostics.

The development server, live reload, translations and plugins are not yet
implemented in this release.

[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html
[Unreleased]: https://github.com/spapanik/neon-ssg/compare/v0.2.0...main
[0.2.0]: https://github.com/spapanik/neon-ssg/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/spapanik/neon-ssg/releases/tag/v0.1.0
