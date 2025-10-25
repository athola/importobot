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
- Database queries use your team's connection cleanup approach

## Step 1: Prepare Your Template Files

Gather your existing Robot Framework files that demonstrate good testing patterns in your organization.

## Template Guidelines

-   **Focus on patterns:** Each template should demonstrate a specific testing pattern (e.g., web authentication, API validation).
-   **Use consistent naming:** Variables, test cases, and keywords should follow a consistent naming convention.
-   **Include proper structure:** Templates should include setup, test steps, validation, and teardown.
-   **Avoid hardcoded values:** Use variables for values that may change between environments.
-   **Keep it clean:** Avoid syntax errors, deprecated keywords, and overly complex logic.

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

### Template Naming Conventions

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

## Advanced Usage

### Conditional Template Loading

You can use environment variables to conditionally load different template sets for different environments.

```bash
#!/bin/bash

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

### Troubleshooting

-   **Template loading warnings:** If you see warnings about syntax errors, use `robot --dry-run` to validate your template files.
-   **No patterns learned:** Ensure your templates have `*** Test Cases ***` sections and contain recognizable test steps. Use the `--verbose` flag to see detailed ingestion logs.
-   **Generated tests don't use template patterns:** Check that your template patterns match your JSON step descriptions and use similar terminology. The `--verbose` flag can help you debug pattern matching issues.

## Related Documentation

- [User Guide](User-Guide.md) - General usage instructions
- [Blueprint Learning Architecture](architecture/Blueprint-Learning.md) - Technical details
- [API Examples](API-Examples.md) - Advanced usage patterns
- [Migration Guide](Migration-Guide.md) - Upgrade instructions
