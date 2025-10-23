*** Settings ***
Documentation       A resource file that has required functionality
...                 for zephyr logging, and signing into controller/target hosts.

Library             OperatingSystem
Library             Process
Library             String
Library             SSHLibrary
Library             libraries/zephyr_logger.py

# Import variables from config/example.resource such
# ```
# *** Variables ***
# ${CLI_DIR}              /path/to/cli/dir
# ${HOST_USERNAME}        username
# ${HOST_PASSWORD}        password
# ${TARGET_USERNAME}      username
# ${TARGET_PASSWORD}      password
# ${TARGET_IP}            10.0.2.50
# ${TARGET_CONNECTION}    20
# # accepts values: ${TRUE} and ${EMPTY}
# # because ${EMPTY} will replace with blank space,
# # quotes were needed around ${IS_EMBEDDED}. This is why
# # we are unable to use ${FALSE} because it would be interpreted
# # as a string.
# ${IS_EMBEDDED}          ${TRUE}
# ```
Resource            example.resource


*** Variables ***
${EMBEDDED_PRIVATE_KEY}    -----BEGIN TEST KEY-----
...                        # Example placeholder key (non-sensitive; generated for tests)
...                        placeholder-ssh-key-content-for-example-purposes-only
...                        -----END TEST KEY-----


*** Keywords ***
Connect Agent
    [Documentation]    Connect to an already established agent connection.
    ...                When connected, the return string can either be the IP address
    ...                or the hostname.
    Switch Connection    Controller

    Write    connect ${TARGET_CONNECTION}
    Read Until Regexp    (Connected to ${TARGET_IP}!)|(Connected to \\S+!)

Connect Hosts SSH
    [Documentation]    Connects to Host/Target and
    ...    sets default timeout to 30s and writes logs
    ...    debug logs to ${OUTPUT_DIR}/sshlibrary.log.

    Set Default Configuration    timeout=30 seconds
    Enable SSH Logging    ${OUTPUT_DIR}/sshlibrary.log
    Login Host
    Login Target

CLI Entry
    [Documentation]    Start the CLI, and connect an already established agent.
    ...    This a common entry point for agent tasks, but not all tasks are the same.
    ...    For example, a test that only configures will not need to connect to an agent.
    Start CLI
    Connect Agent

Create Directory
    [Documentation]    Create a directory, and check if that directory exists on
    ...                the given ``connection``.
    ...                ``dir_name`` - directory path. non-embedded systems must use
    ...                absolute paths, while embedded systems may use relative paths
    [Arguments]    ${dir_name}    ${connection}
    Switch Connection    ${connection}
    Execute Command    mkdir -p ${dir_name}

    # adjust connection for SFTP commands for target/embedded
    IF    '${connection}' == 'Target' and '${IS_EMBEDDED}'
        Switch Connection    CustomOSTarget
    END
    # ``OperatingSystem`` also has ``File Should Not Exist``; to remove lint warning
    # explicitly use ``SSHLibrary``
    SSHLibrary.Directory Should Exist    ${dir_name}

Logger
    [Documentation]    Zephyr logger that writes into ``script.log``.
    ...    Calls log_zephyr() from zephyr_logger.py library. This keyword is used
    ...    over the ``Log`` keyword because it logs to XML/HTML, which would require it's
    ...    own unique parser (feasible). Regardless, a custom keyword is needed to keep
    ...    the format of the zephyr logger to later be ingested.
    ...    Another option to use native keyword, but additional checks would have to be added.
    ...    ``Log    [Test ${TEST_ID} (Step ${step_num})]: ${result} - {Result: ${result_str}}    CONSOLE``
    ...    - ``step_num``: Step number.
    ...    - ``result``: Result, ``${TRUE}`` or ``${FALSE}``.
    ...    - ``result_str``: Message to display to the user.
    [Arguments]    ${step_num}    ${result}=${FALSE}    ${result_str}=''
    ${TEST_ID}=    Get Test ID    ${TEST NAME}
    Log Zephyr    ${TEST_ID}    ${step_num}    ${result}    ${result_str}

Login Target
    [Documentation]    embedded devices will use 2 connections, one that
    ...    will use the alias ``Target`` for ``Execute Command``
    ...    and ``CustomOSTarget`` for SFTP commands.
    ...    embedded devices are assumed to have used ``dropbear -BR``
    ...    to run in the background, and not require passwords.
    IF     "${IS_EMBEDDED}"
        # Special case where embedded3/embedded4 requires public key authentication.
        # Password authentication will have priority, and public key authentication
        # used as a backup method. Key material is generated on demand to avoid
        # storing private keys in source control.
        TRY
            Open Connection    ${target_ip}    alias=Target    port=2222    prompt=#
            Login    username=root    password=${EMPTY}
        EXCEPT
            Open Connection    ${target_ip}    alias=Target    port=2222    prompt=#
            ${embedded_key_path}=    Join Path    ${OUTPUT_DIR}    embedded_private_key.pem
            Create File    ${embedded_key_path}    ${EMBEDDED_PRIVATE_KEY}
            Login With Public Key    username=root    keyfile=${embedded_key_path}
        END
        Open Connection    ${target_ip}    alias=CustomOSTarget
        # quotations around ``${EMPTY}`` otherwise syntax error
        # appears; doesn't regard as an empty string.
        IF    "${TARGET_PASSWORD}" == "${EMPTY}"
            Login    username=admin
        ELSE
            Login    username=admin    password=${TARGET_PASSWORD}
        END
    ELSE
        Open Connection    ${target_ip}    alias=Target
        Login    username=${TARGET_USERNAME}    password=${TARGET_PASSWORD}
    END

Login Host
    [Documentation]    Login to the controller host, use
    ...                hard coded localhost; Avoiding one extra
    ...                variable inside of our resource config file.
    Open Connection    localhost    alias=Controller
    Login    ${HOST_USERNAME}    ${HOST_PASSWORD}

Remove Directory
    [Documentation]    Remove a directory ``dir`` on the given ``connection``.
    ...                ``dir`` - directory path. non-embedded systems must use
    ...                absolute paths, while embedded systems may use relative paths
    ...                ``connection`` - which connection to use
    [Arguments]    ${dir}    ${connection}
    Switch Connection    ${connection}
    IF    '${connection}' == 'Target' and '${IS_EMBEDDED}'
        Execute Command    rm -rf ${dir}
    ELSE
        Execute Command    rm -rf ${dir}    sudo=True    sudo_password=${TARGET_PASSWORD}
    END

    # adjust connection for SFTP commands for target/embedded
    IF    '${connection}' == 'Target' and '${IS_EMBEDDED}'
        Switch Connection    CustomOSTarget
    END
    # ``OperatingSystem`` also has ``Directory Should Not Exist``; to remove lint warning
    # explicitly use ``SSHLibrary``
    SSHLibrary.Directory Should Not Exist    ${dir}

Start CLI
    [Documentation]    Start the CLI, enter credentials, and await for prompt.
    ...                use -D option when starting CLI to return tables. This makes
    ...                parsing values such as ID, GUIDS, etc without requiring a regex
    Switch Connection    Controller

    Write    cd ${CLI_DIR}
    Read Until Regexp    \$|#
    Write    ./cli.sh -D
    Read Until Regexp    [Uu]sername:
    Write    admin
    Read Until Regexp    [Pp]assword:
    Write    admin
    Read Until Regexp    Websocket Connected![\\s\\S]+admin>

Target Process List
    [Documentation]    Return the process list of a command.
    ...                different devices use different syntax.
    Switch Connection    Target

    VAR    ${ps_command}    ps -ely
    IF    "${IS_EMBEDDED}"
        VAR    ${ps_command}    ps
    END
    ${ps_output}=    Execute Command   ${ps_command}
    RETURN    ${ps_output}

Quit CLI
    [Documentation]    Quit the CLI so we don't have cli_entry dangling
    ...    after every test run.
    Switch Connection    Controller
    Write    quit
    Read Until Regexp    Logged out|\$|#
