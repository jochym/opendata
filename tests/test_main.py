def test_ui_import() -> None:
    """Ensure the UI components are importable."""
    from opendata.ui.app import start_ui

    assert callable(start_ui)


def test_main_launch() -> None:
    """Ensure the main entry point exists."""
    from opendata.main import main

    assert callable(main)
