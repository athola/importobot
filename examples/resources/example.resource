*** Settings ***
Documentation       An example resource file that is required to be populated
...                 before running the example ``setconfig.robot`` test suite.


*** Variables ***
${CLI_DIR}              /path/to/cli/dir
${HOST_USERNAME}        username
${HOST_PASSWORD}        password
${TARGET_USERNAME}      username
${TARGET_PASSWORD}      password
${TARGET_IP}            10.0.2.50
${TARGET_CONNECTION}    20
# accepts values: ${TRUE} and ${EMPTY}
# because ${EMPTY} will replace with blank space,
# quotes were needed around ${IS_EMBEDDED}. This is why
# we are unable to use ${FALSE} because it would be interpreted
# as a string.
${IS_EMBEDDED}          ${TRUE}
# used in ``ssh.robot`` test suite. this machine currently
# requires ``netstat`` from the ``net-tools`` library, and
# ``ncat`` to be installed.
${THIRD_MACHINE_IP}            10.0.2.51
${THIRD_MACHINE_USERNAME}      username
${THIRD_MACHINE_PASSWORD}      password

