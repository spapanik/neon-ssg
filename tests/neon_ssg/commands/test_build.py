from __future__ import annotations

from contextlib import chdir
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from neon_ssg.__main__ import main
from neon_ssg.commands.build import BuildCommand
from neon_ssg.lib.exceptions import BuildFailedError

if TYPE_CHECKING:
    from pathlib import Path


def test_build_renders_navigation_and_rewrites_links(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("# Home\n\n[Guide](guide.md)\n", encoding="utf-8")
    (docs / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (tmp_path / "neon-ssg.yaml").write_text(
        "site:\n  name: Example\ncontent:\n  nav:\n"
        "    - Home: README.md\n    - Guides:\n        - Guide: guide.md\n",
        encoding="utf-8",
    )
    with chdir(tmp_path):
        BuildCommand(verbosity=0).run()
    home = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    guide = (tmp_path / "site" / "guide" / "index.html").read_text(encoding="utf-8")
    assert '<a href="guide/">Guide</a>' in home
    assert '<a href="../">Home</a>' in guide
    assert '<h1 id="guide">Guide</h1>' in guide


def test_nested_links_keep_queries_and_fragments(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "guide").mkdir(parents=True)
    (docs / "README.md").write_text("# Home", encoding="utf-8")
    (docs / "guide" / "index.md").write_text(
        "# Guide\n\n[Home](../README.md?view=full#top)\n"
        "[Next](next%20steps.md#section)\n",
        encoding="utf-8",
    )
    (docs / "guide" / "next steps.md").write_text("# Next", encoding="utf-8")
    with chdir(tmp_path):
        BuildCommand(verbosity=0).run()
    guide = (tmp_path / "site" / "guide" / "index.html").read_text(encoding="utf-8")
    assert 'href="../?view=full#top"' in guide
    assert 'href="next%20steps/#section"' in guide
    assert (tmp_path / "site" / "guide" / "next steps" / "index.html").is_file()


def test_failed_build_preserves_previous_output(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    page = docs / "index.md"
    page.write_text("# Working\n", encoding="utf-8")
    with chdir(tmp_path):
        BuildCommand(verbosity=0).run()
        output = tmp_path / "site" / "index.html"
        previous = output.read_text(encoding="utf-8")
        page.write_text("[Broken](missing.md)\n", encoding="utf-8")
        with pytest.raises(BuildFailedError, match="linked page not found"):
            BuildCommand(verbosity=0).run()
        assert output.read_text(encoding="utf-8") == previous


def test_include_source_is_relative_to_docs_directory(tmp_path: Path) -> None:
    (tmp_path / "manual").mkdir()
    (tmp_path / "LICENSE.md").write_text("# Licence\n", encoding="utf-8")
    (tmp_path / "neon-ssg.yaml").write_text(
        "content:\n  docs_root: manual\n  include:\n"
        "    - src: ../LICENSE.md\n      as: LICENSE.md\n"
        "  nav:\n    - Licence: LICENSE.md\n",
        encoding="utf-8",
    )
    with chdir(tmp_path):
        BuildCommand(verbosity=0).run()
    assert '<h1 id="licence">Licence</h1>' in (
        tmp_path / "site" / "LICENSE" / "index.html"
    ).read_text(encoding="utf-8")


def test_unmarked_directory_is_not_removed(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    output = tmp_path / "site"
    output.mkdir()
    (output / "important.txt").write_text("keep", encoding="utf-8")
    with chdir(tmp_path), pytest.raises(BuildFailedError, match="unmarked"):
        BuildCommand(verbosity=0).run()
    assert (output / "important.txt").read_text(encoding="utf-8") == "keep"


def test_configuration_error_and_output_override(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    config = tmp_path / "neon-ssg.yaml"
    config.write_text("site:\n  name: ''\n", encoding="utf-8")
    with chdir(tmp_path), pytest.raises(BuildFailedError):
        BuildCommand(0).run()
    config.write_text("{}", encoding="utf-8")
    with chdir(tmp_path):
        BuildCommand(0, site_root=tmp_path / "custom").run()
    assert (tmp_path / "custom" / ".neon-ssg").exists()


def test_main_reports_build_failure(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch("sys.argv", ["ssg", "build"]),
        patch("neon_ssg.__main__.BuildCommand", side_effect=BuildFailedError("bad")),
        pytest.raises(SystemExit, match="1"),
    ):
        main()
    assert capsys.readouterr().err == "bad\n"


def test_configurable_path_cleanup_and_asset_links(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    section = docs / "01-phonology"
    section.mkdir(parents=True)
    (docs / "00-index.md").write_text(
        "# Arcadia\n\n[Guide](01-phonology/00-index.md)", encoding="utf-8"
    )
    (section / "00-index.md").write_text(
        "# Guide\n\n![Diagram](diagram.png)\n\n[Home](../00-index.md)", encoding="utf-8"
    )
    (section / "diagram.png").write_bytes(b"image")
    (tmp_path / "neon-ssg.yaml").write_text(
        "content:\n  remove_prefix: '\\d\\d-'\n  nav:\n"
        "    - Home: 00-index.md\n    - Guide: 01-phonology/00-index.md\n",
        encoding="utf-8",
    )
    with chdir(tmp_path):
        BuildCommand(0).run()
    home = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    guide = (tmp_path / "site/phonology/index.html").read_text(encoding="utf-8")
    assert 'href="phonology/"' in home
    assert 'href="../">Home</a>' in guide
    assert 'src="../01-phonology/diagram.png"' in guide
    assert (tmp_path / "site/01-phonology/diagram.png").is_file()


def test_suffix_cleanup_and_collisions(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index-00.md").write_text("# Home", encoding="utf-8")
    config = tmp_path / "neon-ssg.yaml"
    config.write_text("content:\n  remove_suffix: '-\\d\\d'\n", encoding="utf-8")
    with chdir(tmp_path):
        BuildCommand(0).run()
        assert (tmp_path / "site/index.html").exists()
        (docs / "index.md").write_text("# Duplicate", encoding="utf-8")
        BuildCommand(0).run()
        assert "Home" in (tmp_path / "site/index.html").read_text(encoding="utf-8")
        (docs / "guide-01.md").write_text("# One", encoding="utf-8")
        (docs / "guide-02.md").write_text("# Two", encoding="utf-8")
        with pytest.raises(BuildFailedError, match="same output"):
            BuildCommand(0).run()


def test_invalid_cleanup_pattern_is_configuration_error(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "neon-ssg.yaml").write_text(
        "content:\n  remove_prefix: '['\n", encoding="utf-8"
    )
    with chdir(tmp_path), pytest.raises(BuildFailedError):
        BuildCommand(0).run()


def test_section_index_links_and_explicit_labels(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    section = docs / "01-phonology"
    section.mkdir(parents=True)
    (docs / "index.md").write_text("# Home", encoding="utf-8")
    (section / "00-index.md").write_text("# Introduction", encoding="utf-8")
    (section / "01-letters.md").write_text("# Letters", encoding="utf-8")
    config = tmp_path / "neon-ssg.yaml"
    config.write_text(
        "content:\n  remove_prefix: '\\d\\d-'\n  nav:\n"
        "    - Home: index.md\n    - Phonology:\n"
        "        - 01-phonology/00-index.md\n"
        "        - Letters: 01-phonology/01-letters.md\n",
        encoding="utf-8",
    )
    with chdir(tmp_path):
        BuildCommand(0).run()
        html = (tmp_path / "site/index.html").read_text(encoding="utf-8")
        assert '<a href="phonology/">Phonology</a>' in html
        assert ">00-index</a>" not in html
        assert '<a href="phonology/letters/">Letters</a>' in html
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                "- 01-phonology/00-index.md", "- Overview: 01-phonology/00-index.md"
            ),
            encoding="utf-8",
        )
        BuildCommand(0).run()
    html = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    assert "<summary><span>Phonology</span></summary>" in html
    assert '<a href="phonology/">Overview</a>' in html


def test_index_selection_and_alias_links(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    for name in ("02-index.md", "01-index.md", "00-README.md", "03-README.md"):
        (docs / name).write_text(f"# {name}", encoding="utf-8")
    (docs / "other.md").write_text("[Readme](00-README.md)", encoding="utf-8")
    (tmp_path / "neon-ssg.yaml").write_text(
        "content:\n  remove_prefix: '\\d\\d-'\n", encoding="utf-8"
    )
    with chdir(tmp_path):
        BuildCommand(0).run()
        assert "01-index.md" in (tmp_path / "site/index.html").read_text(
            encoding="utf-8"
        )
        assert 'href="../"' in (tmp_path / "site/other/index.html").read_text(
            encoding="utf-8"
        )
        (docs / "01-index.md").unlink()
        (docs / "02-index.md").unlink()
        BuildCommand(0).run()
        assert "00-README.md" in (tmp_path / "site/index.html").read_text(
            encoding="utf-8"
        )


def test_custom_assets_are_included_on_all_pages(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    for folder in (
        "01-files/css/nested",
        "01-files/js",
        "01-files/img",
        "01-files/ts",
        "01-files/lua",
        "01-files/fonts",
        "01-guide",
    ):
        (docs / folder).mkdir(parents=True, exist_ok=True)
    (docs / "00-index.md").write_text(
        "# Home\n\n![Logo](01-files/img/logo.png)", encoding="utf-8"
    )
    (docs / "01-guide/00-index.md").write_text("# Guide", encoding="utf-8")
    (docs / "01-files/css/a.css").write_text("body {color: red}", encoding="utf-8")
    (docs / "01-files/css/nested/b.css").write_text(
        "body {color: blue}", encoding="utf-8"
    )
    (docs / "01-files/js/site.js").write_text("console.log('ready')", encoding="utf-8")
    (docs / "01-files/img/logo.png").write_bytes(b"logo")
    (docs / "01-files/ts/source.ts").write_text("const x: number = 1", encoding="utf-8")
    (docs / "01-files/README.md").write_text("asset documentation", encoding="utf-8")
    (docs / "01-files/lua/example.lua").write_text("source", encoding="utf-8")
    (docs / "01-files/fonts/site.woff2").write_bytes(b"font")
    (tmp_path / "neon-ssg.yaml").write_text(
        "content:\n  assets: 01-files\n  remove_prefix: '\\d\\d-'\n", encoding="utf-8"
    )
    with chdir(tmp_path):
        BuildCommand(0).run()
    home = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    guide = (tmp_path / "site/guide/index.html").read_text(encoding="utf-8")
    assert 'href="01-files/css/a.css"' in home
    assert home.index('href="01-files/css/a.css"') < home.index(
        'href="01-files/css/nested/b.css"'
    )
    assert '<script defer src="../01-files/js/site.js"></script>' in guide
    assert 'href="../01-files/css/a.css"' in guide
    assert 'src="01-files/img/logo.png"' in home
    assert not (tmp_path / "site/01-files/README.md").exists()
    assert not (tmp_path / "site/01-files/lua").exists()
    assert (tmp_path / "site/01-files/fonts/site.woff2").read_bytes() == b"font"
    assert not (tmp_path / "site/01-files/ts").exists()
    assert "01-files/README" not in home


def test_default_assets_and_updated_files(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "assets/css").mkdir(parents=True)
    (docs / "index.md").write_text("# Home", encoding="utf-8")
    stylesheet = docs / "assets/css/custom.css"
    stylesheet.write_text("first", encoding="utf-8")
    with chdir(tmp_path):
        BuildCommand(0).run()
        assert (
            'href="assets/css/custom.css"' in (tmp_path / "site/index.html").read_text()
        )
        stylesheet.write_text("second", encoding="utf-8")
        BuildCommand(0).run()
    assert (tmp_path / "site/assets/css/custom.css").read_text() == "second"


def test_theme_images_use_configured_assets_on_nested_pages(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "01-brand/img/icons").mkdir(parents=True)
    (docs / "01-guide").mkdir()
    (docs / "00-index.md").write_text("# Home", encoding="utf-8")
    (docs / "01-guide/00-index.md").write_text("# Guide", encoding="utf-8")
    (docs / "01-brand/img/my logo.svg").write_text("logo", encoding="utf-8")
    (docs / "01-brand/img/icons/favicon.svg").write_text("icon", encoding="utf-8")
    (tmp_path / "neon-ssg.yaml").write_text(
        "site:\n  name: Example\ncontent:\n  assets: 01-brand\n"
        "  remove_prefix: '\\d\\d-'\ntheme:\n"
        "  logo: my logo.svg\n  favicon: icons/favicon.svg\n",
        encoding="utf-8",
    )
    with chdir(tmp_path):
        BuildCommand(0).run()
    home = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    guide = (tmp_path / "site/guide/index.html").read_text(encoding="utf-8")
    assert '<img src="01-brand/img/my%20logo.svg" alt="">Example' in home
    assert '<link rel="icon" href="01-brand/img/icons/favicon.svg">' in home
    assert '<img src="../01-brand/img/my%20logo.svg" alt="">' in guide
    assert '<link rel="icon" href="../01-brand/img/icons/favicon.svg">' in guide
    assert (tmp_path / "site/01-brand/img/my logo.svg").is_file()


@pytest.mark.parametrize("setting", ["logo", "favicon"])
def test_missing_theme_image_reports_setting(tmp_path: Path, setting: str) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "neon-ssg.yaml").write_text(
        f"theme:\n  {setting}: missing.png\n", encoding="utf-8"
    )
    with (
        chdir(tmp_path),
        pytest.raises(BuildFailedError, match=f"theme.{setting}.*missing.png"),
    ):
        BuildCommand(0).run()


def test_default_translation_builds_prefixed_urls(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "en-gb/guide").mkdir(parents=True)
    (docs / "assets/img").mkdir(parents=True)
    (docs / "assets/css").mkdir()
    (docs / "assets/img/logo.svg").write_text("logo", encoding="utf-8")
    (docs / "assets/css/custom.css").write_text("body {}", encoding="utf-8")
    (docs / "en-gb/index.md").write_text(
        "# Home\n\n[Guide](guide/index.md)\n\n![Logo](../assets/img/logo.svg)",
        encoding="utf-8",
    )
    (docs / "en-gb/guide/index.md").write_text(
        "# Guide\n\n[Home](../index.md)", encoding="utf-8"
    )
    (tmp_path / "neon-ssg.yaml").write_text(
        "translations:\n  default:\n    - name: 🇬🇧 English\n"
        "      link: en/\n      path: en-gb/\n      lang: en\n"
        "  alternate:\n    - name: Français\n      link: fr/\n      lang: fr\n"
        "theme:\n  logo: logo.svg\ncontent:\n  nav:\n"
        "  - Home: index.md\n  - Guide: guide/index.md\n",
        encoding="utf-8",
    )
    with chdir(tmp_path):
        BuildCommand(0).run()
    home = (tmp_path / "site/en/index.html").read_text(encoding="utf-8")
    guide = (tmp_path / "site/en/guide/index.html").read_text(encoding="utf-8")
    redirect = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    assert '<html lang="en">' in home
    assert 'href="guide/"' in home
    assert 'href="../">Home</a>' in guide
    assert 'src="../assets/img/logo.svg"' in home
    assert 'href="../assets/css/custom.css"' in home
    assert 'src="../../assets/img/logo.svg"' in guide
    assert "url=en/" in redirect
    assert not (tmp_path / "site/fr").exists()


def test_default_translation_path_defaults_to_link(tmp_path: Path) -> None:
    (tmp_path / "docs/en").mkdir(parents=True)
    (tmp_path / "docs/en/index.md").write_text("# Home", encoding="utf-8")
    (tmp_path / "neon-ssg.yaml").write_text(
        "translations:\n  default:\n    - name: English\n"
        "      link: en/\n      lang: en\n",
        encoding="utf-8",
    )
    with chdir(tmp_path):
        BuildCommand(0).run()
    assert (tmp_path / "site/en/index.html").is_file()


@pytest.mark.parametrize(
    "link", ["../escape", "/absolute", "", "a\\b", "https://example.com"]
)
def test_invalid_translation_url_fails(tmp_path: Path, link: str) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "neon-ssg.yaml").write_text(
        "translations:\n  default:\n    - name: English\n      lang: en\n"
        f"      link: '{link}'\n      path: en\n",
        encoding="utf-8",
    )
    with (
        chdir(tmp_path),
        pytest.raises(BuildFailedError, match=r"translations\.default\.link"),
    ):
        BuildCommand(0).run()


def test_configurable_fonts_load_local_files_and_system_names(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "assets/fonts").mkdir(parents=True)
    (docs / "guide").mkdir()
    (docs / "index.md").write_text("# Home", encoding="utf-8")
    (docs / "guide/index.md").write_text("# Guide", encoding="utf-8")
    (docs / "assets/fonts/ComicSans-Regular.woff2").write_bytes(b"font")
    (docs / "assets/fonts/ComicSans-Bold.woff2").write_bytes(b"font")
    (docs / "assets/fonts/Other-Regular.woff2").write_bytes(b"font")
    (tmp_path / "neon-ssg.yaml").write_text(
        "theme:\n  text: Times New Roman\n  code: Comic Sans\n", encoding="utf-8"
    )
    with chdir(tmp_path):
        BuildCommand(0).run()
    home = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    guide = (tmp_path / "site/guide/index.html").read_text(encoding="utf-8")
    assert 'font-family:"Times New Roman",sans-serif' in home
    assert 'font-family:"Comic Sans",monospace' in home
    assert 'url("assets/fonts/ComicSans-Regular.woff2")' in home
    assert 'url("../assets/fonts/ComicSans-Bold.woff2")' in guide
    assert "font-weight:700;font-style:normal" in guide
    assert "Other-Regular" not in home


def test_default_fonts_and_safe_css_escaping(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("# Home", encoding="utf-8")
    with chdir(tmp_path):
        BuildCommand(0).run()
        home = (tmp_path / "site/index.html").read_text(encoding="utf-8")
        assert 'font-family:"Roboto",sans-serif' in home
        assert 'font-family:"Roboto Mono",monospace' in home
        (tmp_path / "neon-ssg.yaml").write_text(
            "theme:\n  text: 'evil</style><script>'\n", encoding="utf-8"
        )
        BuildCommand(0).run()
    home = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    assert "evil</style><script>" not in home
    assert "evil\\3c /style\\3e " in home


def test_navigation_collapses_sections_and_expands_current_path(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "guide/advanced").mkdir(parents=True)
    (docs / "other").mkdir()
    for page in (
        "index.md",
        "guide/index.md",
        "guide/advanced/topic.md",
        "other/index.md",
    ):
        (docs / page).write_text("# Page", encoding="utf-8")
    (tmp_path / "neon-ssg.yaml").write_text(
        "content:\n  nav:\n  - Home: index.md\n  - Guide:\n"
        "      - guide/index.md\n      - Advanced:\n"
        "          - Topic: guide/advanced/topic.md\n"
        "  - Other:\n      - other/index.md\n",
        encoding="utf-8",
    )
    with chdir(tmp_path):
        BuildCommand(0).run()
    home = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    guide = (tmp_path / "site/guide/index.html").read_text(encoding="utf-8")
    topic = (tmp_path / "site/guide/advanced/topic/index.html").read_text(
        encoding="utf-8"
    )
    assert '<a href="./" aria-current="page">Home</a>' in home
    assert '<details><summary><a href="guide/">Guide</a></summary>' in home
    assert (
        '<details open><summary><a href="./" aria-current="page">Guide</a></summary>'
        in guide
    )
    assert '<details open><summary><a href="../../">Guide</a></summary>' in topic
    assert "<details open><summary><span>Advanced</span></summary>" in topic
    assert '<a href="./" aria-current="page">Topic</a>' in topic
    assert '<details><summary><a href="../../../other/">Other</a></summary>' in topic


def test_mermaid_is_opt_in_and_leaves_other_code_blocks_alone(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text(
        '# Diagrams\n\n```mermaid\nflowchart LR\n A["<hello>"] --> B\n```\n\n'
        '```python\nprint("hello")\n```\n',
        encoding="utf-8",
    )
    (docs / "plain.md").write_text("# No diagram", encoding="utf-8")
    config = tmp_path / "neon-ssg.yaml"
    with chdir(tmp_path):
        BuildCommand(0).run()
        home = (tmp_path / "site/index.html").read_text(encoding="utf-8")
        assert '<div class="mermaid">' not in home
        assert "mermaid.esm.min.mjs" not in home
        config.write_text("markdown:\n  mermaid: true\n", encoding="utf-8")
        BuildCommand(0).run()
    home = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    plain = (tmp_path / "site/plain/index.html").read_text(encoding="utf-8")
    assert '<div class="mermaid">flowchart LR' in home
    assert "&lt;hello&gt;" in home
    assert "mermaid@11.4.1/dist/mermaid.esm.min.mjs" in home
    assert 'securityLevel:"strict"' in home
    assert "<pre" in home
    assert "hello" in home
    assert "mermaid.esm.min.mjs" not in plain
