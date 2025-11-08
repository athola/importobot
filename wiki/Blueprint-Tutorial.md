# Blueprint Tutorial: Template Learning System

This tutorial shows how to use Importobot's blueprint system to learn patterns from your existing Robot Framework files and apply them consistently during conversions.

For detailed examples and guidelines on creating effective templates, see the [Blueprint Templates Examples and Guidelines](../examples/robot/templates/README.md).

## Overview

When you provide template files using the `--robot-template` flag, Importobot scans them for step patterns, variable naming conventions, and test structure. It then applies these learned patterns to new conversions. For example, if your templates consistently use `${TEST_USER}` for logins, Importobot will use that variable instead of generating a generic one.

## Step 1: Prepare Your Template Files

Gather existing Robot Framework files that demonstrate good testing patterns. Templates should be clean, use consistent naming, and include setup and teardown steps.

## Step 2: Run Conversion with Templates

Use the `--robot-template` flag to specify a directory or a list of files to learn from.

```bash
# Learn from a directory of templates
uv run importobot \
    --robot-template templates/ \
    input.json output.robot

# Combine with schema-driven parsing
uv run importobot \
    --robot-template templates/ \
    --input-schema docs/field_guide.md \
    input.json output.robot
```

## Step 3: Verify Template Application

Check the generated Robot Framework file to ensure it uses patterns from your templates.

### Before Template Learning

```robotframework
*** Test Cases ***
Login Test
    Input Text    id=username    testuser
    Input Text    id=password    pass123
    Click Button    id=login-button
```

### After Template Learning

```robotframework
*** Test Cases ***
Login Test
    [Documentation]    Verify user can login
    Input Text    id=username    ${TEST_USER}
    Input Text    id=password    ${TEST_PASSWORD}
    Click Button    id=login-button
    Page Should Contain    Welcome, ${TEST_USER}
    [Teardown]    Logout User
```

Notice how the learned template added variable usage, a validation step, and a teardown.

## Troubleshooting

- **Template loading warnings**: Use `robot --dry-run` to validate your template files.
- **No patterns learned**: Ensure your templates have `*** Test Cases ***` sections and recognizable test steps. Use `--verbose` to see detailed ingestion logs.

## Related Documentation

- [User Guide](User-Guide.md)
- [Blueprint Learning Architecture](architecture/Blueprint-Learning.md)
- [API Examples](API-Examples.md)
