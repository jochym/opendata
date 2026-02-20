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


def test_help_argument(capsys) -> None:
    """Test that --help argument displays help and exits."""
    from opendata.main import main
    import sys

    original_argv = sys.argv

    try:
        # Ensure that requesting help works and exits cleanly
        sys.argv = ["opendata", "--help"]

        try:
            main()
        except SystemExit:
            # --help exits after showing help
            pass
    finally:
        sys.argv = original_argv


def test_version_displays_correct_value(capsys) -> None:
    """Test that --version displays the actual version from VERSION file."""
    import sys
    from pathlib import Path
    from opendata.main import main

    # Read expected version from VERSION file
    version_file = Path(__file__).parent.parent / "src" / "opendata" / "VERSION"
    expected_version = version_file.read_text(encoding="utf-8").strip()

    original_argv = sys.argv

    try:
        # Test --version flag
        sys.argv = ["opendata", "--version"]

        # Capture output by redirecting stdout
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        try:
            with redirect_stdout(f):
                main()
        except SystemExit as e:
            # --version exits with code 0
            assert e.code == 0 or e.code is None

        output = f.getvalue().strip()

        # Verify version number is in output (not 0.0.0)
        assert expected_version.split(".")[0] != "0" or expected_version != "0.0.0", (
            "Version should not be default 0.0.0"
        )
        assert expected_version in output, (
            f"Expected version {expected_version} in output, got: {output}"
        )
    finally:
        sys.argv = original_argv
