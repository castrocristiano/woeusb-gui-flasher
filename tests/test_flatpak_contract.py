"""Contract test for Flatpak manifest compliance."""

from pathlib import Path

import yaml


def test_flatpak_manifest_contract():
    base_dir = Path(__file__).resolve().parent.parent
    manifest_file = base_dir / "org.woeusb.WoeUsbGui.yml"

    assert manifest_file.is_file(), "Manifesto org.woeusb.WoeUsbGui.yml deve existir"

    with open(manifest_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["app-id"] == "org.woeusb.WoeUsbGui"
    assert data["command"] == "woeusb-gui"

    finish_args = data.get("finish-args", [])
    # Check essential permissions
    assert "--socket=wayland" in finish_args
    assert "--socket=fallback-x11" in finish_args
    assert "--share=ipc" in finish_args
    assert "--system-talk-name=org.freedesktop.UDisks2" in finish_args
    assert "--filesystem=host:ro" in finish_args
    assert "--filesystem=/run/media:rw" in finish_args

    # Check modules
    modules = data.get("modules", [])
    module_names = [m["name"] if isinstance(m, dict) else m for m in modules]
    assert "wimlib" in module_names
    assert "p7zip" in module_names
    assert "woeusb-gui" in module_names


def test_desktop_and_metainfo_localization_contract():
    base_dir = Path(__file__).resolve().parent.parent
    desktop_file = base_dir / "assets" / "org.woeusb.WoeUsbGui.desktop"
    metainfo_file = base_dir / "assets" / "org.woeusb.WoeUsbGui.metainfo.xml"
    locales_dir = base_dir / "locales"

    assert desktop_file.is_file()
    desktop_content = desktop_file.read_text(encoding="utf-8")
    assert "Comment=Universal Windows USB bootable flasher for Linux" in desktop_content
    assert "Comment[pt_BR]=" in desktop_content
    assert "Keywords[pt_BR]=" in desktop_content

    assert metainfo_file.is_file()
    metainfo_content = metainfo_file.read_text(encoding="utf-8")
    assert "<summary>Create bootable Windows USB drives on Linux</summary>" in metainfo_content
    assert 'xml:lang="pt_BR"' in metainfo_content

    assert (locales_dir / "en.lang").is_file()
    assert (locales_dir / "pt_BR.lang").is_file()
