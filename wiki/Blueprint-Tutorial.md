# Blueprint Tutorial: Template Learning System

This tutorial explains how to use Importobot's blueprint system to extract patterns from your existing Robot Framework files and apply them consistently during new conversions.

For detailed examples and guidelines on creating effective templates, see the [Blueprint Templates Examples and Guidelines](../examples/robot/templates/README.md).

## Overview

When you provide template files using the `--robot-template` flag, Importobot analyzes them to identify common step patterns, variable naming conventions, and overall test structure. It then uses these identified patterns to guide the generation of new Robot Framework files. For example, if your templates consistently use `${TEST_USER}` for login credentials, Importobot will prioritize using that variable in new conversions rather than generating a generic one.

## Step 1: Prepare Your Template Files

Gather existing Robot Framework files that represent your desired testing style and conventions. These template files should be clean, use consistent naming, and ideally include common setup and teardown steps.

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

Observe how the blueprint system applied patterns from your templates, such as variable usage, a validation step, and a teardown.

## Troubleshooting

- **If you encounter warnings during template loading**: Use `robot --dryrun` to validate the syntax of your template files.
- **If no patterns are learned**: Ensure your templates have `*** Test Cases ***` sections and recognizable test steps. Use `--verbose` to see detailed ingestion logs.

## Related Documentation

- [User Guide](User-Guide.md)
- [Blueprint Learning Architecture](architecture/Blueprint-Learning.md)
- [API Examples](API-Examples.md)
