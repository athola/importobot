*** Settings ***
Documentation    Tests converted from JSON
Library    SeleniumLibrary

*** Test Cases ***

Verify User Login Functionality
    [Documentation]    To ensure that users can successfully log in to the application with valid credentials.
    ${chrome_options}=    Evaluate    sys.modules['selenium.webdriver'].ChromeOptions()    sys,selenium.webdriver
    Call Method    ${chrome_options}    add_argument    argument=--headless
    Call Method    ${chrome_options}    add_argument    argument=--no-sandbox
    Call Method    ${chrome_options}    add_argument    argument=--disable-dev-shm-usage
    Call Method    ${chrome_options}    add_argument    argument=--disable-gpu
    Call Method    ${chrome_options}    add_argument    argument=--disable-extensions
    Call Method    ${chrome_options}    add_argument    argument=--user-data-dir=/tmp/chrome_user_data_43fc93a9
    Open Browser    http://localhost:8000/login.html    chrome    options=${chrome_options}
    # Description: Navigate to the application login page.
    # Action: URL: https://example.com/login
    # Expected: The login page is displayed with username and password fields.
    Go To    http://localhost:8000/login.html
    Page Should Contain    The login page is displayed with username and password fields.

    # Description: Enter valid username and password.
    # Action: Username: testuser, Password: password123
    # Expected: The username and password fields are populated.
    Input Text    id=username_field    testuser@example.com
    Textfield Value Should Be    id=username_field    testuser@example.com

    # Description: Click the 'Login' button.
    # Expected: User is successfully logged in and redirected to the dashboard page.
    Click Button    id=login_button
    Sleep    1s    # Wait for JavaScript to execute
    Page Should Contain    User is successfully logged in and redirected to the dashboard page.

    Close Browser
