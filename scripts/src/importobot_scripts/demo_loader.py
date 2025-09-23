"""
Demo module loader.

Provides direct access to all demo modules.
"""

# Import all demo modules directly
from .demo_config import DemoConfig, EnterpriseScenario
from .demo_logging import (
    ProgressReporter,
    demo_logger,
    error_handler,
    metrics_reporter,
)
from .demo_scenarios import (
    ScenarioModeler,
    create_business_case,
)
from .demo_validation import (
    SECURITY_MANAGER,
    SecurityError,
    ValidationError,
    read_and_display_file,
    safe_execute_command,
    safe_remove_file,
    validate_demo_environment,
    validate_file_path,
)


class ModuleLoader:
    """Provides direct access to all demo modules."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self) -> None:
        """Initialize all demo modules."""
        # Configuration and scenarios
        self.demo_config = DemoConfig()
        self.scenario_modeler = ScenarioModeler()
        self.enterprise_scenario = EnterpriseScenario

        # Logging and error handling
        self.demo_logger = demo_logger
        self.error_handler = error_handler
        self.security_manager = SECURITY_MANAGER
        self.metrics_reporter = metrics_reporter
        self.progress_reporter = ProgressReporter

        # Validation and security
        self.validation_error = ValidationError
        self.security_error = SecurityError
        self.validate_file_path = validate_file_path
        self.safe_execute_command = safe_execute_command
        self.validate_demo_environment = validate_demo_environment
        self.safe_remove_file = safe_remove_file
        self.read_and_display_file = read_and_display_file

        # Business case functions
        self.create_business_case = create_business_case
