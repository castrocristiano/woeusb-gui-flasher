"""Test suite for WoeUSB GUI Flasher specification and foundational assets."""

from pathlib import Path


def test_spec_files_exist():
    """Verify that all core Spec Kit documentation files exist and are populated."""
    base_dir = Path(__file__).resolve().parent.parent

    spec_file = base_dir / "specs" / "001-woeusb-gui" / "spec.md"
    plan_file = base_dir / "specs" / "001-woeusb-gui" / "plan.md"
    tasks_file = base_dir / "specs" / "001-woeusb-gui" / "tasks.md"
    constitution_file = base_dir / ".specify" / "memory" / "constitution.md"
    license_file = base_dir / "LICENSE"

    assert spec_file.is_file(), "spec.md deve existir"
    assert plan_file.is_file(), "plan.md deve existir"
    assert tasks_file.is_file(), "tasks.md deve existir"
    assert constitution_file.is_file(), "constitution.md deve existir"
    assert license_file.is_file(), "LICENSE (GPLv3) deve existir"

    # Verify content size
    assert spec_file.stat().st_size > 500, "spec.md deve conter os requisitos definidos"
    assert plan_file.stat().st_size > 500, "plan.md deve conter a arquitetura técnica"
    assert tasks_file.stat().st_size > 500, "tasks.md deve conter as tarefas mapeadas"


def test_package_structure():
    """Verify basic python package structure."""
    import woeusb_gui_flasher

    assert woeusb_gui_flasher is not None
