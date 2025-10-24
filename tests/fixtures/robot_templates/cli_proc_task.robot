*** Settings ***
Documentation       ``$command`` task suite

# ``SSHLibrary`` keywords:
# ``Close All Connections``
# ``Switch Connection``
# ``Read Until Regexp``
# ``Write``
Library             SSHLibrary
# ``Setup.resource`` keywords:
# ``Connect Hosts SSH``
# ``CLI Entry``
# ``Logger``.
# ``Target Process List``
# ``Quit CLI``
Resource            resources/Setup.resource

Suite Setup         Run Keywords
...                     Connect Hosts SSH
...                     CLI Entry
Suite Teardown      Run Keywords
...                     Quit CLI
...                     Close All Connections


*** Test Cases ***
$test_name
    [Documentation]    $documentation
    VAR    $${proc_name}    $proc_name

    Switch Connection    Controller
    Write    $command --proc_name $${proc_name}
    ${cli_assignment}=    Read Until Regexp    $command task (\S+) completed successfully!
    Logger    step_num=1    result=$${TRUE}    result_str=Task completed successfully.
    Log    Expected: no task errors

    Switch Connection    Target
    ${ps}=    Execute Command    ps -ely | grep $proc_name
    Log    Expected: $proc_name found

    $${ps_output}=    Target Process List
    Log    $${ps_output}
    Should Contain    $${ps_output}    $${proc_name}
    Logger    step_num=2    result=$${TRUE}    result_str=Found $${proc_name} in ps output.
    Log    Expected: $proc_name found
