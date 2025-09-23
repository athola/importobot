"""
Demo utilities module.

Contains file operations, command execution, and user interface utilities.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any


class FileOperations:
    """Handles file operations with proper error handling and security."""

    def __init__(self, loader: Any) -> None:
        """Initialize the FileHandler with a loader."""
        self.loader = loader

    def read_json_file(self, file_path: str) -> dict[str, Any] | None:
        """Read and parse a JSON file."""
        try:
            if self.loader.security_manager:
                self.loader.security_manager.log_file_access(file_path, "read")

            self.loader.validate_file_path(
                file_path, must_exist=True, allowed_extensions=[".json"]
            )

            with self.loader.demo_logger.operation_timer(
                f"read_json_{Path(file_path).name}"
            ):
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.loader.demo_logger.info(
                        f"Successfully read JSON file: {file_path}"
                    )
                    # Ensure we return the expected type
                    if isinstance(data, dict):
                        return data
                    return None

        except (self.loader.validation_error, self.loader.security_error) as e:
            self.loader.demo_logger.error(
                f"Validation error reading {file_path}", exc_info=e
            )
            return None
        except (OSError, json.JSONDecodeError) as e:
            if self.loader.error_handler and self.loader.error_handler.handle_error(
                e, f"reading {file_path}"
            ):
                self.loader.demo_logger.warning(f"Using fallback data for {file_path}")
                return None
            self.loader.demo_logger.error(f"Failed to read {file_path}", exc_info=e)
            return None

    def read_and_display_file(self, file_path: str, title: str = "OUTPUT") -> None:
        """Read and display a file's contents."""
        if not os.path.exists(file_path):
            self.loader.demo_logger.warning(f"File not found: {file_path}")
            return

        print(f"\n{title}:")

        try:
            with self.loader.demo_logger.operation_timer(
                f"display_{Path(file_path).name}"
            ):
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    print(content)
            self.loader.demo_logger.info(f"Successfully displayed file: {file_path}")
        except (OSError, UnicodeDecodeError) as e:
            if self.loader.error_handler and self.loader.error_handler.handle_error(
                e, f"displaying {file_path}"
            ):
                print(f"\n{title}: [File could not be read - using simulated output]")
            else:
                self.loader.demo_logger.error(f"Failed to display {file_path}: {e}")
        finally:
            if file_path.startswith("/tmp/"):
                self._safe_remove_file(file_path)

    def _safe_remove_file(self, file_path: str) -> None:
        """Safely remove a file with logging and proper error handling."""
        if not file_path or not os.path.exists(file_path):
            return

        try:
            os.remove(file_path)
            self.loader.demo_logger.debug(f"Cleaned up temporary file: {file_path}")

            if self.loader.security_manager:
                self.loader.security_manager.log_file_access(file_path, "delete")
        except (OSError, PermissionError) as e:
            self.loader.demo_logger.warning(
                f"Could not remove temporary file {file_path}: {e}"
            )
        except Exception:
            pass


class CommandRunner:
    """Handles command execution with proper error handling."""

    def __init__(self, loader: Any) -> None:
        """Initialize the CommandRunner with a loader."""
        self.loader = loader

    def run_conversion(self, input_file: str, output_file: str) -> str:
        """Run importobot conversion."""
        try:
            self.loader.validate_file_path(
                input_file, must_exist=True, allowed_extensions=[".json"]
            )

            command = f"uv run importobot {input_file} {output_file}"

            with self.loader.demo_logger.operation_timer(
                f"conversion_{Path(input_file).stem}"
            ):
                success, stdout, stderr = self.loader.safe_execute_command(command)

                if self.loader.security_manager:
                    self.loader.security_manager.log_command(command, success)

                if success:
                    self.loader.demo_logger.info(
                        f"Conversion successful: {input_file} -> {output_file}"
                    )
                    return str(stdout)

                error_msg = f"Conversion failed: {stderr}"
                self.loader.demo_logger.error(error_msg)
                return error_msg

        except (self.loader.validation_error, self.loader.security_error) as e:
            error_msg = f"Validation error: {e}"
            self.loader.demo_logger.error("Validation error in conversion", exc_info=e)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error during conversion: {e}"
            self.loader.demo_logger.error(error_msg, exc_info=e)
            return error_msg

    def run_command(self, command: str, cwd: str | None = None) -> str:
        """Run a shell command and return the result with proper error handling."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.loader.demo_logger.error(f"Command failed: {command}")
            self.loader.demo_logger.error(
                f"Exit code: {e.returncode}, stderr: {e.stderr}"
            )
            return ""
        except subprocess.TimeoutExpired:
            self.loader.demo_logger.error(f"Command timed out: {command}")
            return ""
        except Exception as e:
            self.loader.demo_logger.error(
                f"Unexpected error running command '{command}': {e}"
            )
            return ""


class UserInterface:
    """Handles user interaction and display."""

    def __init__(self, config: Any) -> None:
        """Initialize the UserInterface with a config."""
        self.config = config

    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        if not self.config.non_interactive:
            os.system("cls" if os.name == "nt" else "clear")

    def press_to_continue(self) -> None:
        """Prompt user to press Enter to continue."""
        if self.config.non_interactive:
            print("\n[Non-interactive mode - continuing automatically...]")
            time.sleep(1)
            return
        input("\nPress Enter to continue...")

    def prompt_continue(self) -> bool:
        """Prompt user with y/n to continue."""
        if self.config.non_interactive:
            print("\n[Non-interactive mode - continuing to next demo...]")
            time.sleep(1)
            return True

        while True:
            response = input("\nContinue to next demo? (y/n): ").strip().lower()
            if response in ["y", "yes"]:
                return True
            if response in ["n", "no"]:
                return False

            print("Please enter 'y' or 'n'")

    def show_title(self, title: str) -> None:
        """Display a section title."""
        self.clear_screen()
        print("=" * 80)
        print(f"{title:^80}")
        print("=" * 80)
