"""Helper functions for creating Zephyr result logs.

Helper functions written in native Python rather than Robot Framework
that help with creating a log file (usually named `script.log`) file
(includes testcase, step number) which is used later on for J9 reporting.
"""

import re

from robot.api import logger

DEFAULT_LOG_FILENAME = "output/script.log"


def log_zephyr(test_id, step_num, result, result_str):
    """Format test information into a Zephyr result string before logging.

    Example Zephyr string:
    [Test JWT-T1036 (Step 1)]: PASSED - dir {Result: Actual matches expected}

    Args:
        test_id: Zephyr test case identifier (e.g., TST-7777).
        step_num: Current step number in the test case.
        result: Boolean indicating step success (True=PASSED, False=FAILED).
        result_str: Descriptive text for the step result.
    """
    # sanity check incase user passed True/False
    if isinstance(result, bool):
        result = "PASSED" if result else "FAILED"
    else:
        raise OSError("Pass in a boolean to indicate step result.")

    log_line = (
        f"[Test {test_id} (Step {step_num})]: {result} - {{Result: {result_str}}}"
    )
    with open(DEFAULT_LOG_FILENAME, "a+", encoding="utf-8") as zephyr_log:
        zephyr_log.write(f"{log_line}\n")


def get_test_id(test_name, project_id="ABC"):
    """Parse test name to extract Zephyr test ID.

    Parses out "test_name" to make sure it conforms to the Zephyr
    ID, e.g. agent1 would be CAN-T, but Robot does not allow "-"
    therefore the testcase name would omit "-" and recombine here.
    Adjust for Controller and use ABC.
    """
    logger.info(f"Test string: {test_name}")
    search = re.search(rf"{project_id} T(\d+)", test_name)
    if search:
        return f"{project_id}-T{search.group(1)}"
    raise OSError("Unable to parse for test ID.")
