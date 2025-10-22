# Blueprint Tutorial: Template Learning System

This tutorial shows how to use Importobot's blueprint system to learn patterns from your existing Robot Framework files and apply them consistently during conversions.

## Overview

Importobot identifies conversion patterns from existing Robot Framework files. When you provide template files, the system extracts step patterns, variable naming conventions, and test structure to apply them to new conversions.

For example, if your team uses `${TEST_USER}` and `${TEST_PASSWORD}` consistently across web tests, Importobot will apply those patterns instead of generating generic variable names.

### Template Learning

When you run Importobot with `--robot-template`, it scans your existing Robot files to find step patterns. For example, if your templates consistently use `Input Text    id=username    ${TEST_USER}`, Importobot will apply that variable pattern instead of generic `${variable}` syntax.

In practice, this means:
- Web UI tests use your team's naming conventions (`${TEST_USER}`, `${TEST_PASSWORD}`)
- API calls follow your session management patterns
- Database queries use your preferred connection cleanup approach

## Step 1: Prepare Your Template Files

Gather your existing Robot Framework files that demonstrate good testing patterns in your organization.

### What Makes a Good Template?

**Good template characteristics**:
- Well-structured test cases with clear steps
- Consistent naming conventions
- Proper use of Robot Framework keywords
- Domain-specific commands relevant to your applications
- Error handling and validation patterns

**Avoid templates with**:
- Syntax errors or invalid Robot Framework code
- Outdated or deprecated keywords
- Overly complex or unclear test logic
- Hardcoded values that should be variables

### Example Template Structure

```
templates/
├── web_ui_tests.robot          # Web application tests
├── api_tests.robot             # API integration tests
├── database_tests.robot        # Database validation tests
├── ssh_commands.robot          # Server management tests
└── file_operations.robot       # File system operations
```

## Step 2: Organize Template Directories

Create a template directory structure that reflects your testing domains:

```bash
# Create template directories
mkdir -p templates/{web,api,database,infrastructure}

# Organize existing Robot files
cp tests/ui/*.robot templates/web/
cp tests/integration/*.robot templates/api/
cp tests/db/*.robot templates/database/
cp tests/ops/*.robot templates/infrastructure/
```

### Template Naming Conations

Use descriptive names that indicate the domain:

```bash
Good names:
├── user_authentication.robot
├── payment_processing.robot
├── database_migrations.robot
├── server_deployment.robot

Poor names:
├── test1.robot
├── temp.robot
├── old_tests.robot
├── backup.robot
```

## Step 3: Run Conversion with Templates

Use the `--robot-template` flag to tell Importobot to learn from your template files.

### Basic Template Usage

```bash
# Single template directory
uv run importobot \
    --robot-template templates/ \
    input.json output.robot

# Multiple template directories
uv run importobot \
    --robot-template templates/web/ \
    --robot-template templates/api/ \
    input.json output.robot

# Specific template files
uv run importobot \
    --robot-template templates/user_authentication.robot \
    --robot-template templates/payment_processing.robot \
    input.json output.robot
```

### Template + Schema Documentation

For even better results, combine template learning with schema documentation:

```bash
uv run importobot \
    --robot-template templates/ \
    --input-schema docs/field_guide.md \
    input.json output.robot
```

## Step 4: Monitor Template Ingestion

Use the `--verbose` flag to see what patterns Importobot learns from your templates:

```bash
uv run importobot \
    --robot-template templates/ \
    --verbose \
    input.json output.robot
```

### What to Look For

You should see output like:

```
INFO: Ingesting template: templates/user_authentication.robot
INFO: Found 12 step patterns in user_authentication.robot
INFO: Learned pattern: 'Switch Connection    ${SSH_SESSION}' for SSH operations
INFO: Learned pattern: 'Input Text    id=username    ${USER}' for web forms
INFO: Learned pattern: 'Execute Command    docker restart ${CONTAINER}' for container operations
INFO: Template ingestion complete: 4 files, 45 patterns learned
```

## Step 5: Verify Template Application

Check that the generated Robot Framework file uses patterns from your templates.

### Before Template Learning

```robot
*** Test Cases ***
Login Test
    [Documentation]    Verify user can login
    Input Text    id=username    testuser
    Input Text    id=password    pass123
    Click Button    id=login-button
```

### After Template Learning

```robot
*** Test Cases ***
Login Test
    [Documentation]    Verify user can login
    Input Text    id=username    ${TEST_USER}
    Input Text    id=password    ${TEST_PASSWORD}
    Click Button    id=login-button
    Page Should Contain    Welcome, ${TEST_USER}
    Sleep    2s
    [Teardown]    Logout User
```

Notice how the learned template added:
- Variable usage (`${TEST_USER}`, `${TEST_PASSWORD}`)
- Additional validation step
- Proper teardown
- Team-specific timing patterns

## Advanced Template Usage

### Conditional Template Loading

Use environment variables to conditionally load different template sets:

```bash
#!/bin/bash
# Environment-specific template selection

if [ "$ENVIRONMENT" = "production" ]; then
    TEMPLATE_DIRS="templates/prod/"
elif [ "$ENVIRONMENT" = "staging" ]; then
    TEMPLATE_DIRS="templates/staging/ templates/common/"
else
    TEMPLATE_DIRS="templates/dev/ templates/common/"
fi

uv run importobot \
    --robot-template $TEMPLATE_DIRS \
    input.json output.robot
```

### Template Validation

Before using templates in production, validate them:

```bash
# Check template syntax
robot --dry-run templates/*.robot

# Test template-based conversion
uv run importobot \
    --robot-template templates/ \
    --verbose \
    sample_input.json sample_output.robot

# Review generated output
robot --dry-run sample_output.robot
```

## Template Pattern Examples

### Web UI Patterns

Templates can teach Importobot your team's web testing patterns:

```robot
# Template: web_authentication.robot
*** Test Cases ***
User Login Flow
    [Documentation]    Standard user login procedure
    [Tags]    authentication    smoke
    Open Browser    ${BASE_URL}    chrome
    Maximize Browser Window
    Input Text    id=username    ${USER_NAME}
    Input Text    id=password    ${USER_PASSWORD}
    Click Button    id=login-button
    Wait Until Page Contains    Dashboard
    [Teardown]    Close Browser
```

**Learned patterns:**
- Standard browser setup sequence
- Variable naming conventions (`${USER_NAME}`, `${USER_PASSWORD}`)
- Page validation patterns
- Proper teardown procedures

### API Testing Patterns

```robot
# Template: api_validation.robot
*** Test Cases ***
API Endpoint Validation
    [Documentation]    Validate API response structure
    Create Session    api    ${API_BASE_URL}
    ${response}=    GET On Session    api    /users/1
    Should Be Equal As Strings    ${response.status_code}    200
    ${json}=    To Json    ${response.content}
    Should Contain    ${json['username']}    testuser
    [Teardown]    Delete All Sessions
```

**Learned patterns:**
- API session management
- Response validation approach
- JSON parsing patterns
- Session cleanup procedures

### Database Testing Patterns

```robot
# Template: database_operations.robot
*** Test Cases ***
Database Record Validation
    [Documentation]    Verify database record integrity
    Connect To Database    ${DB_CONNECTION_STRING}
    ${count}=    Row Count    SELECT COUNT(*) FROM users WHERE active = 1
    Should Be True    ${count} > 0
    Disconnect From Database
```

**Learned patterns:**
- Database connection handling
- Query execution patterns
- Validation approach
- Connection cleanup

## Troubleshooting Template Issues

### Common Problems

**Problem**: Template loading warnings
```bash
WARNING: Skipping template file: syntax_error.robot - Parse error
```

**Solution**: Fix Robot Framework syntax errors in template files:
```bash
# Validate template syntax
robot --dry-run templates/syntax_error.robot
```

**Problem**: No patterns learned from templates
```bash
INFO: Template ingestion complete: 4 files, 0 patterns learned
```

**Solution**: Ensure templates contain recognizable patterns:
- Check that templates have `*** Test Cases ***` sections
- Verify templates contain actual test steps
- Use `--verbose` to see detailed ingestion logs

**Problem**: Generated tests don't use template patterns

**Solution**:
- Verify template patterns match your JSON step descriptions
- Check that template and JSON use similar terminology
- Use `--verbose` to see pattern matching attempts

### Debugging Template Learning

Enable detailed logging to understand pattern learning:

```bash
# Enable debug logging
export IMPORTOBOT_LOG_LEVEL=DEBUG

uv run importobot \
    --robot-template templates/ \
    --verbose \
    input.json output.robot
```

Look for debug messages like:
```
DEBUG: Analyzing step: "Enter username 'testuser'"
DEBUG: Searching for pattern with command: "Enter"
DEBUG: Found match: "Input Text    id=username    ${USER}"
DEBUG: Applied template pattern with variable substitution
```

## Best Practices

### Template Quality Guidelines

1. **Keep templates focused**: Each template should demonstrate specific testing patterns
2. **Use consistent naming**: Variable names, test case names, and keywords should follow conventions
3. **Include proper structure**: Setup, test steps, validation, and teardown
4. **Regular maintenance**: Update templates as testing practices evolve
5. **Version control**: Track template changes in git like other test assets

### Template Organization

```
templates/
├── core/                    # Essential patterns used by all teams
│   ├── setup_teardown.robot
│   └── validation.robot
├── web/                     # Web application testing patterns
│   ├── authentication.robot
│   ├── navigation.robot
│   └── forms.robot
├── api/                     # API testing patterns
│   ├── rest_calls.robot
│   └── response_validation.robot
└── infrastructure/          # Infrastructure testing patterns
    ├── database.robot
    └── ssh_commands.robot
```

### Performance Considerations

- **Template ingestion time**: 50-200ms per typical Robot file
- **Memory usage**: ~1KB per learned pattern
- **Recommended limits**: Keep template directory under 50 files total
- **Caching**: Patterns are cached after first conversion

### Integration with CI/CD

Add template validation to your CI pipeline:

```yaml
# .github/workflows/template-validation.yml
name: Template Validation
on:
  push:
    paths: ['templates/**']

jobs:
  validate-templates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Importobot
        run: pip install importobot

      - name: Validate Template Syntax
        run: |
          for template in templates/**/*.robot; do
            robot --dry-run "$template" || exit 1
          done

      - name: Test Template Conversion
        run: |
          uv run importobot \
            --robot-template templates/ \
            --verbose \
            tests/fixtures/sample_input.json \
            /tmp/test_output.robot

          robot --dry-run /tmp/test_output.robot
```

## Next Steps

1. **Start small**: Begin with 2-3 high-quality template files
2. **Measure improvement**: Compare conversions with and without templates
3. **Iterate**: Add more templates based on conversion quality needs
4. **Share**: Distribute template collections across teams for consistency
5. **Maintain**: Regularly review and update templates as practices evolve

## Related Documentation

- [User Guide](User-Guide.md) - General usage instructions
- [Blueprint Learning Architecture](architecture/Blueprint-Learning.md) - Technical details
- [API Examples](API-Examples.md) - Advanced usage patterns
- [Migration Guide](Migration-Guide.md) - Upgrade instructions
