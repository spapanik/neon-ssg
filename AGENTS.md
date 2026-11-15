# neon-ssg

## Purpose

Build a Python static site generator named **neon-ssg**, exposed through the
command **`ssg`**. Use `neon_ssg` as the Python import package.

Prioritise a pleasant local development loop, repository-specific plugins and
reproducible CI builds. A system-wide installation must coexist with isolated
site environments. Hot reloading is a core requirement.

The product direction is a documentation site generator with the authoring and
navigation experience associated with MkDocs and Material, plus room for
additional capabilities. Treat these as inspiration, not a claim of feature,
configuration or plugin compatibility. Build a distinctive `neon` theme and
keep the generated result usable as a static site.

This file describes the intended architecture, not features already implemented.
Inspect the repository before making changes and update documentation to reflect
actual behaviour. Do not implement the entire roadmap for an unrelated task.

## Technology and scope

- Implement the generator in Python. Do not introduce Rust, Wasm or native plugin
  interfaces without a demonstrated need and an explicit architectural decision.
- Use `uv` for dependency management, a committed `uv.lock`, a `src/` layout,
  Ruff for linting and formatting, `ty` for type checking, and pytest for tests.
- Retain the existing mypy check in CI alongside `ty`. Respect the configured
  Ruff, pytest and coverage settings when changing code.
- Declare the supported Python versions in `pyproject.toml`; do not invent a
  minimum version in documentation that differs from the package metadata.
- Support development and execution on Linux, macOS and Windows. Use portable
  paths and process management; avoid shell-dependent execution.
- Keep generated sites deployable as static files without a Python server.
- Prefer simple implementations. Optimise measured local rebuild bottlenecks;
  production builds will commonly run in CI.

## Command-line contract

The intended public commands are:

```sh
ssg init
ssg build
ssg serve
ssg plugin add <package>
```

Use these names consistently. `neon-ssg` is the distribution name, not the CLI
command. Keep bootstrap and environment-management behaviour separate from the
build engine. Provide useful help, actionable errors and non-zero exit codes
for failed commands. Production builds must not prompt interactively.

## Installation and project environments

Support both of these workflows:

1. A globally available `ssg` launcher delegates to the site's environment.
2. A project installation runs directly, including through `uv run ssg ...`.

The site environment contains the selected version of `neon-ssg` and all plugin
dependencies. Different sites may pin different generator and plugin versions.
Global packages must not leak into project plugin resolution.

- Discover the site root deterministically from the working directory and a
  documented project marker; support an explicit project-directory override.
- Use the project's `.venv` by default. If supporting another environment path,
  make its selection explicit and document precedence. Never silently select an
  unrelated activated environment over the site's configured environment.
- An activated venv does not automatically change a global command's interpreter.
  Explicitly delegate into the selected project environment.
- Prefer delegating through `uv run` with an explicit project root rather than
  manually modifying `sys.path` or activating an environment in a shell.
- Prevent delegation loops. A worker must use the selected project interpreter,
  including after restarts, and execute a dedicated internal entry point.
- Do not change the global installation to satisfy a site's dependencies.
- Keep dependency installation and lockfile changes in explicit setup or plugin
  management operations. Locked CI builds must fail clearly on missing or
  inconsistent dependencies rather than silently update the lockfile.
- Do not synchronise dependencies on every file-watcher event.

Use `pyproject.toml` and `uv.lock` for Python dependencies. Do not introduce a
second dependency resolver or a redundant plugin lockfile. Keep site
configuration distinct from dependency metadata.

## Site configuration and authoring

- Preserve the existing `neon-ssg.yaml` configuration convention and the
  `NEON_SSG` environment namespace. Configuration currently uses `dj_settings`
  to merge system, user and project file tiers, with later override files;
  scalar resolution also accepts environment and CLI values. Preserve and test
  precedence when extending it. Make the effective inputs clear so CI builds
  can be reproduced despite machine-specific configuration or environment.
- Resolve configured filesystem paths relative to the configuration's
  resolution root, rather than the process's incidental working directory.
  Include source paths are relative to the configured documentation directory;
  include targets are relative to that directory's content tree. Distinguish
  source paths from output-relative paths and validate the latter.
- Continue the existing typed configuration and structured diagnostics
  approach: report actionable locations and hints where available, collect
  independent configuration errors, and retain Python warning integration and
  strict-mode promotion of warnings where applicable.
- Support Markdown documentation, Jinja templates and syntax highlighting,
  building on the existing Python Markdown, PyMdown Extensions and Pygments
  dependencies. The current configuration models site metadata, content and
  navigation, repository links, theme and overrides, Markdown extensions,
  locales, versions, assets and explicitly enabled plugins. Extend these
  deliberately rather than assuming every modelled option is implemented.
- Aim for a polished documentation experience, including navigation, search,
  rich Markdown and configurable theme features. The checked-in example
  configuration illustrates the intended feature vocabulary; it is not proof
  those features work. Document only behaviour that has been implemented.

## Translations and localisation

Translations are a first-class part of the site model, not an afterthought or
an optional plugin. Design content discovery, navigation, URLs, templates,
search, diagnostics and rebuild invalidation with multiple locales in mind.

- Support a default locale and explicitly configured additional locales, with
  locale-specific content and navigation, translated theme UI and a way for
  readers to switch languages. Single-language sites should remain simple.
- Define deterministic locale URL and fallback rules before implementing them;
  missing translations must be visible through useful diagnostics rather than
  silently producing ambiguous output. The existing configuration defaults to
  English and enables fallback, but rendering and fallback are not yet built.
- Preserve Unicode throughout and consider language metadata, text direction,
  accessible language selection and locale-appropriate search when designing
  the interface. Do not assume a flag uniquely represents a language.
- Test translated and untranslated content, fallback on and off, navigation,
  links, search and rebuilds as those capabilities are implemented.

## Plugins

Use ordinary Python modules and packages loaded inside the build worker.
Support published packages and repository-local plugin code, including editable
local packages whose own dependencies are resolved in the site environment.

- Define a small, typed public plugin interface and an explicit API compatibility
  policy. Prefer Python protocols and data classes to inheritance-heavy APIs.
- Allow configuration to explicitly enable plugins and determine their order.
  Installing a package alone must not automatically execute it.
- Define contracts for content loading, transformation, page generation and
  output handling as those extension points are introduced. Specify input and
  output types, ordering, dependency reporting and error behaviour.
- Keep plugin discovery, dependency installation and execution separate.
- Report plugin identity, build phase and relevant source path on failures.
- Treat plugin code as trusted project code. A venv or worker process is not a
  security sandbox; do not claim otherwise.
- Avoid a subprocess protocol for each plugin initially. The replaceable worker
  provides process isolation for the build as a whole.

## Development server and hot reloading

Separate a persistent development supervisor from a replaceable build worker.

The supervisor owns file watching, the development HTTP server and the browser
notification connection. The worker owns configuration, imported plugins and
build state. Keep the supervisor independent of project plugin imports so a
plugin failure cannot prevent it from observing the next edit.

| Changed input | Required behaviour |
| --- | --- |
| Content or templates | Rebuild affected output; refresh after success |
| CSS or static assets | Update output; refresh or replace CSS after success |
| Plugin Python code or site configuration | Replace worker, rebuild and refresh |
| Dependency metadata or lockfile | Report that environment synchronisation is needed; require an explicit restart after synchronisation |

- Browser live reload is mandatory. Replacing CSS without a full page refresh
  is an enhancement, not a prerequisite for the first working version.
- Reload Python code by replacing the worker. Do not rely on `importlib.reload`
  to reconstruct plugin instances, module references or global state.
- Watch configured local plugin source roots, including declared editable
  sources outside the site root. Exclude `.venv`, output, caches and VCS data.
- Debounce changes and serialise builds. Coalesce edits received during a build
  into a subsequent build; never lose an edit or let stale output replace newer
  output. Use worker/build generation identifiers where necessary.
- Publish successful output coherently. Keep the last successful site available
  when a build fails and show diagnostics in the terminal and browser.
- Recover automatically when a later edit fixes a configuration or plugin error.
- Ensure deleted or renamed inputs remove obsolete generated output after the
  next successful build.
- Stop and reap workers on restart and shutdown, including on Windows. Keep the
  HTTP server and browser notification connection alive during worker restarts.
- Bind the development server to loopback by default; make other interfaces an
  explicit option.

`watchfiles` is the initial watcher candidate. Hide watcher details behind a
small boundary so build logic is independent of a particular watcher library.

## Build engine

- Share one build engine between `ssg build` and `ssg serve`.
- Keep build state scoped to a site and worker rather than module-level globals.
- Make output deterministic for the same inputs, configuration and dependencies.
- Track dependencies between source inputs and outputs. Templates, shared data
  and plugins may invalidate more than the file that changed.
- Start with correct full rebuilds where dependency tracking is incomplete.
  Incremental rebuilds must produce the same result as a clean build.
- Do not let generated paths escape the configured output directory. Never
  delete source files while cleaning stale output.
- Keep browser reload scripts and error UI out of production output.

## Implementation conventions

Use cohesive modules organised around features such as CLI/environment
delegation, building, plugins and development serving. Keep boundaries explicit
without adding speculative abstraction layers or a service framework.

Use type annotations for public interfaces, `pathlib` for filesystem work and
argument lists for subprocess calls. Avoid shell command construction. Keep
diagnostics useful for site authors rather than exposing implementation details
as the primary error message. Use British English in prose and documentation.

Do not add pre-commit hooks. Keep checks runnable directly and in CI.

## Validation

Use the repository's configured checks; the intended baseline is:

```sh
uv sync --locked --group dev
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest
```

Add meaningful tests for changed behaviour. Prioritise integration coverage of:

- Global launcher delegation and direct project execution without recursion.
- Two sites using different plugin versions without dependency leakage.
- Local plugins with their own dependencies.
- Browser refresh after a successful edit and worker replacement after a plugin
  edit, using the same project interpreter.
- Error recovery, rapid edits, deleted inputs and graceful process shutdown.
- Clean versus incremental output equivalence and reproducible locked CI builds.

Use temporary site fixtures, observable events and bounded timeouts for watcher
tests; avoid arbitrary sleeps. Report which checks actually ran, and do not
present planned behaviour as tested functionality.
