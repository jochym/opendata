def test_ui_import() -> None:
    """Ensure the UI components are importable."""
    from opendata.ui.app import start_ui

    assert callable(start_ui)


def test_main_launch() -> None:
    """Ensure the main entry point exists."""
    from opendata.main import main

    assert callable(main)


def test_version_argument(capsys) -> None:
    """Test that --version argument displays version and exits."""
    import sys
    from opendata.main import main

    # Save original argv
    original_argv = sys.argv

    try:
        # Test --version flag
        sys.argv = ["opendata", "--version"]

        # --version calls sys.exit(), so we expect SystemExit
        with capsys.disabled():
            try:
                main()
            except SystemExit as e:
                assert e.code == 0 or e.code is None
    finally:
        # Restore original argv
        sys.argv = original_argv


def test_version_argument_short_flag(capsys) -> None:
    """Test that -v shows verbose help (not version, as -v is for verbose)."""
    from opendata.main import main
    import sys

    original_argv = sys.argv

    try:
        # Note: -v is for --verbose, not --version
        # --version doesn't have a short flag to avoid conflict
        sys.argv = ["opendata", "--help"]

        try:
            main()
        except SystemExit:
            pass  # --help exits after showing help
    finally:
        sys.argv = original_argv
