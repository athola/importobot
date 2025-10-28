"""Robot Framework variable file for dynamic path configuration."""


def get_variables(is_embedded):
    """
    A special function from Robot Framework that is
    evaluated in the ``Settings`` section of a robot
    test file.

    A relative path is required for SFTP operations when
    it comes to embedded devices. By creating a path at
    ``/flash/rw/pckg`` (or ``/`` when SFTP'd), operations
    such as ``SSHLibrary.File Should Exist`` can easily be
    checked once on the correct connection.
    """
    paths = {"TARGET_TEST_DIR": "/tmp/test_files"}
    if is_embedded:
        paths["TARGET_TEST_DIR"] = "tmp/test_files"

    return paths
