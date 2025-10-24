*** Test Cases ***
Sample
    Switch Connection    Controller
    Write    setconfig --proc_name ${proc_name}
    ${setconfig_cli}=    Read Until Regexp    setconfig task (\S+) completed successfully!
    Logger    step_num=1    result=${TRUE}    result_str=Task completed successfully.
    Log    Expected: no task errors

    Switch Connection    REMOTE_HOST
    ${setconfig_remote}=    Execute Command    ps -ely | grep ${proc_name}
    Log    Expected: process found

