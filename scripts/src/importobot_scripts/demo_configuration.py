"""
Demo configuration management module.

Handles command-line arguments, environment setup, and matplotlib configuration.
"""

import argparse
import os


class DemoConfiguration:
    """Centralized configuration management for the demo."""

    def __init__(self) -> None:
        """Initialize the DemoConfig."""
        self.args = self._parse_args()
        self.non_interactive = self.args.non_interactive
        self.user_tmp_dir = self._setup_temp_dir()
        self._configure_environment()
        self._configure_matplotlib()

    def _parse_args(self) -> argparse.Namespace:
        """Parse command line arguments for demo configuration."""
        parser = argparse.ArgumentParser(description="Importobot Interactive Demo")
        parser.add_argument(
            "--non-interactive", action="store_true", help="Run in non-interactive mode"
        )
        parser.add_argument(
            "--test-cases",
            type=int,
            default=800,
            help="Number of test cases for scenario (default: 800)",
        )
        parser.add_argument(
            "--team-size",
            type=int,
            default=10,
            help="Team size for scenario (default: 10)",
        )
        parser.add_argument(
            "--scenario-name",
            type=str,
            default="Standard Enterprise Migration",
            help="Name for the demo scenario",
        )
        parser.add_argument(
            "--figure-width",
            type=int,
            default=16,
            help="Figure width for charts (default: 16)",
        )
        parser.add_argument(
            "--figure-height",
            type=int,
            default=10,
            help="Figure height for charts (default: 10)",
        )
        parser.add_argument(
            "--complexity-factor",
            type=float,
            default=1.0,
            help="Complexity factor for scenario (0.5=simple, 1.0=standard, "
            "2.0=complex, default: 1.0)",
        )

        # Check if we're in a test environment (imported by pytest)
        # pylint: disable=import-outside-toplevel
        import sys

        if len(sys.argv) == 0 or any("pytest" in arg for arg in sys.argv):
            # Use default arguments when imported in test environment
            return parser.parse_args([])

        return parser.parse_args()

    def _setup_temp_dir(self) -> str:
        """Create a user-owned temporary directory."""
        temp_dir = f"/tmp/importobot_{os.getuid()}"
        os.makedirs(temp_dir, mode=0o700, exist_ok=True)
        return temp_dir

    def _configure_environment(self) -> None:
        """Configure environment variables for Qt and matplotlib."""
        qt_config = {
            "QT_RUNTIME_ROOT": self.user_tmp_dir,
            "XDG_RUNTIME_DIR": self.user_tmp_dir,
            "QT_LOGGING_RULES": "qt.qpa.plugin.warning=false;qt.qpa.plugin.debug=false",
            "QT_DEBUG_PLUGINS": "0",
            "QT_FATAL_WARNINGS": "0",
            "QT_NO_DEBUG": "1",
        }

        if self.non_interactive:
            qt_config.update(
                {
                    "MPLBACKEND": "Agg",
                    "QT_QPA_PLATFORM": "offscreen",
                    "QT_PLUGIN_PATH": "",
                    "QT_QPA_PLATFORM_PLUGIN_PATH": "",
                }
            )

        for key, value in qt_config.items():
            os.environ[key] = value

    def _configure_matplotlib(self) -> None:
        """Configure matplotlib backend based on environment."""
        try:
            # pylint: disable=import-outside-toplevel
            import matplotlib

            if self.non_interactive:
                matplotlib.use("Agg")
            else:
                # Try to use interactive backends in order of preference
                backends_to_try = ["Qt5Agg", "QtAgg", "TkAgg", "GTK3Agg", "MacOSX"]
                current_backend = matplotlib.get_backend().lower()

                # Only try to change backend if we're currently on a non-interactive one
                if current_backend in ["agg", "svg", "pdf", "ps"]:
                    for backend in backends_to_try:
                        try:
                            # Test if backend can be imported
                            matplotlib.use(backend)
                            # If we get here, the backend works
                            break
                        except Exception:
                            # Try next backend
                            continue
        except ImportError:
            pass

    def ensure_visualization_directory(self) -> str:
        """Ensure visualization directory exists in non-interactive mode."""
        if self.non_interactive:
            viz_dir = "visualizations"
            os.makedirs(viz_dir, exist_ok=True)
            return viz_dir
        return "visualizations"
