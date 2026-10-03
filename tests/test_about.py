import pytest
from PyQt6.QtCore import QSettings

from sldgridy import __version__, project
from sldgridy.ui import about_dialog
from sldgridy.ui.about_dialog import AboutDialog, issue_url
from sldgridy.update import UpdateResult, evaluate, parse_version


def test_parse_and_compare_versions():
    assert parse_version("v1.2.10") == (1, 2, 10, 1)
    release = {
        "tag_name": "v99.0.0",
        "html_url": "https://example/r",
        "assets": [{"name": "sldgridy_99.0.0_all.deb", "browser_download_url": "https://x/d.deb"}],
    }
    r = evaluate("1.0.3", release)
    assert r.ok and r.available and r.version == "99.0.0" and r.download_url == "https://x/d.deb"
    assert not evaluate("1.0.3", {"tag_name": "v1.0.3"}).available
    assert not evaluate("1.0.3", {"tag_name": "nightly"}).ok


def test_issue_url_contains_version_and_label():
    url = issue_url("[Bug] ", "bug")
    assert url.startswith(project.ISSUES_NEW_URL + "?labels=bug")
    assert __version__ in url.replace("%2E", ".")


@pytest.fixture
def dialog(qapp, monkeypatch):
    QSettings().clear()
    monkeypatch.setattr(about_dialog, "open_url", lambda url: True)
    d = AboutDialog()
    yield d
    d.close()


def test_buttons_open_project_links(dialog):
    dialog.btn_star.click()
    dialog.btn_source.click()
    dialog.btn_support.click()
    dialog.btn_bug.click()
    assert dialog.opened[:3] == [project.URL, project.URL, project.SUPPORT_URL]
    assert dialog.opened[3].startswith(project.ISSUES_NEW_URL)


def test_update_result_display(dialog):
    dialog.show_update_result(UpdateResult(ok=True, available=False))
    assert "aktuell" in dialog.lbl_update.text()
    dialog.show_update_result(
        UpdateResult(ok=True, available=True, version="9.9.9", download_url="https://x/d.deb")
    )
    assert "9.9.9" in dialog.lbl_update.text()
    dialog.btn_download.click()
    assert dialog.opened[-1] == "https://x/d.deb"
    dialog.show_update_result(UpdateResult(ok=False))
    assert "fehlgeschlagen" in dialog.lbl_update.text()


def test_dev_versions_sort_before_their_release():
    assert parse_version("1.1.3.dev1") < parse_version("1.1.3") < parse_version("1.1.4.dev1")
    assert parse_version("v1.1.3-dev2") > parse_version("1.1.3.dev1")
    assert parse_version("1.1") == (1, 1, 0, 1)
    release = {"tag_name": "v1.1.3", "assets": []}
    assert evaluate("1.1.3.dev1", release).available
    assert not evaluate("1.1.3", release).available
