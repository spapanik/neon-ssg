# neon-ssg: Static site generator

[![build][build_badge]][build_url]
[![lint][lint_badge]][lint_url]
[![tests][tests_badge]][tests_url]
[![license][licence_badge]][licence_url]
[![codecov][codecov_badge]][codecov_url]
[![readthedocs][readthedocs_badge]][readthedocs_url]
[![pypi][pypi_badge]][pypi_url]
[![downloads][pepy_badge]][pepy_url]
[![build automation: yam][yam_badge]][yam_url]
[![Lint: ruff][ruff_badge]][ruff_url]

neon-ssg is an early-stage Python static site generator for documentation.
It turns Markdown and assets into a static site with configurable navigation.
The project is intended to grow into a richer documentation experience; today,
`ssg build` is the implemented command. Development serving, live reload,
translations and plugins are planned but are not yet available.

Install the package with Python 3.11 or newer, then run `ssg build` from a
project containing a `docs/` directory. The generated site is written to
`site/`. See the [installation guide](installation.md) and
[usage guide](usage/index.md) for details.

## Links

- [Documentation]
- [Changelog]

[build_badge]: https://github.com/spapanik/neon-ssg/actions/workflows/build.yml/badge.svg
[build_url]: https://github.com/spapanik/neon-ssg/actions/workflows/build.yml
[lint_badge]: https://github.com/spapanik/neon-ssg/actions/workflows/lint.yml/badge.svg
[lint_url]: https://github.com/spapanik/neon-ssg/actions/workflows/lint.yml
[tests_badge]: https://github.com/spapanik/neon-ssg/actions/workflows/tests.yml/badge.svg
[tests_url]: https://github.com/spapanik/neon-ssg/actions/workflows/tests.yml
[licence_badge]: https://img.shields.io/pypi/l/neon-ssg
[licence_url]: https://neon-ssg.readthedocs.io/en/stable/LICENSE/
[codecov_badge]: https://codecov.io/github/spapanik/neon-ssg/graph/badge.svg?token=Q20F84BW72
[codecov_url]: https://codecov.io/github/spapanik/neon-ssg
[readthedocs_badge]: https://readthedocs.org/projects/neon-ssg/badge/?version=latest
[readthedocs_url]: https://neon-ssg.readthedocs.io/en/latest/
[pypi_badge]: https://img.shields.io/pypi/v/neon-ssg
[pypi_url]: https://pypi.org/project/neon-ssg
[pepy_badge]: https://pepy.tech/badge/neon-ssg
[pepy_url]: https://pepy.tech/project/neon-ssg
[yam_badge]: https://img.shields.io/badge/build%20automation-yamk-success
[yam_url]: https://github.com/spapanik/yamk
[ruff_badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v1.json
[ruff_url]: https://github.com/charliermarsh/ruff
[Documentation]: https://neon-ssg.readthedocs.io/en/stable/
[Changelog]: https://neon-ssg.readthedocs.io/en/stable/CHANGELOG/
