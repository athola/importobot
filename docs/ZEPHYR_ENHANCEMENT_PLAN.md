# Zephyr Enhancement Plan

## Overview

This document outlines a comprehensive plan to enhance Importobot's test case analysis and parsing capabilities to support Zephyr Scale's sophisticated test case methodology. The integration will enable organizations using Zephyr to maintain their structured testing approach while leveraging Importobot's automated conversion to Robot Framework.

## Background

Zephyr Scale implements a highly structured approach to test case management with three core principles:

1. **Self-Contained Test Logic** - Tests must be executable manually from included information only
2. **Standalone Evaluation** - Tests should not depend on other product components working
3. **Target Agnosticism** - Tests should work across multiple platforms with minimal variations

The Zephyr Standard Operating Procedures (SOP) document a sophisticated test case structure with standardized fields, platform-agnostic command handling, and comprehensive requirement traceability.

## Current State Analysis

### Importobot Capabilities
- Generic JSON test case parsing with flexible field detection
- Bayesian confidence scoring for format detection
- Multi-platform API integration (Jira/Xray, Zephyr, TestRail, TestLink)
- Robot Framework conversion with keyword inference
- Bronze/Silver/Gold medallion architecture for data processing

### Zephyr Test Case Structure
Zephyr organizes test cases into three main tabs:

**Details Tab:**
- `Name` - Feature being tested with standardized naming
- `Objective` - Test evaluation description matching help menu text
- `Precondition` - Minimum setup requirements with standardized language
- `Details` - Status, Priority, Component, Owner, Estimated Time, Folder, Labels
- `More Information` - Test Level, Supported Platforms, Automation Status

**Test Script Tab:**
- `Step` - Description of commands and their purpose
- `Test Data` - Exact command values with platform-specific variations
- `Expected Result` - Expected verification outcomes

**Traceability Tab:**
- `Issues` - Linked Jira tickets for requirement tracking
- `Confluence` - Links to project documentation
- `Web Links` - External resources and specifications

## Enhancement Plan

### Phase 1: Enhanced Field Definitions and Structure Recognition

#### 1.1 Extended Field Groups

Add Zephyr-specific field groups to `src/importobot/core/field_definitions.py`:

```python
# Zephyr-specific field groups
ZEPHYR_DETAILS_FIELDS = FieldGroup(
    fields=("status", "priority", "component", "owner", "estimatedTime", "folder"),
    description="Zephyr test case details and metadata"
)

ZEPHYR_PRECONDITION_FIELDS = FieldGroup(
    fields=("precondition", "preconditions", "setup", "requirements"),
    description="Test setup requirements and preconditions"
)

ZEPHYR_TRACEABILITY_FIELDS = FieldGroup(
    fields=("issues", "confluence", "webLinks", "linkedCRS", "requirements"),
    description="Test case traceability and requirement links"
)

ZEPHYR_LEVEL_FIELDS = FieldGroup(
    fields=("testLevel", "level", "importance", "criticality"),
    description="Test level and importance classification"
)

ZEPHYR_PLATFORM_FIELDS = FieldGroup(
    fields=("supportedPlatforms", "platforms", "targets"),
    description="Supported target platforms and architectures"
)

# Enhanced step structure for Zephyr's three-segment approach
ZEPHYR_STEP_STRUCTURE_FIELDS = FieldGroup(
    fields=("step", "testData", "expectedResult", "description", "actual"),
    description="Zephyr step structure with action, data, and expected result"
)
```

#### 1.2 Enhanced Test Case Detection

Update the `is_test_case()` function to recognize Zephyr-specific indicators:

```python
# Add Zephyr-specific indicators to TEST_INDICATORS
ZEPHYR_TEST_INDICATORS = frozenset([
    "name", "description", "steps", "testscript", "objective",
    "summary", "title", "testname", "precondition", "testLevel",
    "supportedPlatforms", "status", "priority"
])

# Enhanced detection logic
def is_zephyr_test_case(data: Any) -> bool:
    """Check if data follows Zephyr test case structure."""
    if not isinstance(data, dict):
        return False

    zephyr_indicators = {
        "testscript", "precondition", "testlevel",
        "supportedplatforms", "objective"
    }

    data_keys = {key.lower() for key in data.keys()}
    return bool(zephyr_indicators & data_keys)
```

#### 1.3 Platform-Specific Command Parsing

Implement sophisticated parsing for Zephyr's platform-agnostic command structure:

```python
class PlatformCommandParser:
    """Parse Zephyr-style platform-specific commands."""

    PLATFORM_KEYWORDS = {
        "TARGET": ["target", "tgt", "default", "standard"],
        "ESXi": ["esxi", "vmware", "vsphere"],
        "EMBEDDED": ["embedded", "iot", "device"],
        "OTHER": ["other", "alternative", "fallback"]
    }

    def parse_platform_commands(self, test_data: str) -> dict[str, list[str]]:
        """Extract platform-specific command variations.

        Handles Zephyr format:
        TARGET: ip addr
        ESXi : esxcli network ip interface list
        EMBEDDED : /rw/pckg/{busyboxbinary} ip addr
        OTHER: ifconfig
        """
        commands = {platform: [] for platform in self.PLATFORM_KEYWORDS}

        # Implementation for parsing platform commands
        lines = test_data.strip().split('\n')
        current_platform = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for platform indicator
            for platform, keywords in self.PLATFORM_KEYWORDS.items():
                if any(line.upper().startswith(keyword + ':') or
                      line.upper().startswith(keyword + ' ')
                      for keyword in keywords):
                    current_platform = platform
                    command = line.split(':', 1)[1].strip() if ':' in line else line
                    commands[platform].append(command)
                    break
            elif current_platform and line:
                # Continuation of previous platform command
                commands[current_platform].append(line)

        return commands
```

### Phase 2: Test Level Classification and Analysis

#### 2.1 Zephyr Test Level Classifier

Implement Zephyr's test level hierarchy for better prioritization:

```python
class ZephyrTestLevelClassifier:
    """Classify tests according to Zephyr methodology."""

    TEST_LEVELS = {
        "Minimum Viable CRS": 1,  # Required for J9, CRS-linked
        "Smoke": 0,               # Preliminary critical tests
        "Edge Case": 2,           # Optional, edge cases
        "Regression": 3           # Bug fix validation, optional for J9
    }

    def classify_test(self, test_data: dict) -> tuple[str, int]:
        """Determine test level based on content and metadata."""
        # Check for CRS links
        if self._has_crs_links(test_data):
            return ("Minimum Viable CRS", 1)

        # Check for smoke test indicators
        if self._is_smoke_test(test_data):
            return ("Smoke", 0)

        # Check for edge case patterns
        if self._is_edge_case(test_data):
            return ("Edge Case", 2)

        # Default to regression
        return ("Regression", 3)

    def _has_crs_links(self, test_data: dict) -> bool:
        """Check if test case has CRS requirement links."""
        traceability_fields = ["issues", "linkedCRS", "requirements", "confluence"]
        return any(
            field in test_data and test_data[field]
            for field in traceability_fields
        )

    def _is_smoke_test(self, test_data: dict) -> bool:
        """Identify smoke test patterns."""
        smoke_indicators = ["smoke", "basic", "core", "critical", "startup"]
        test_text = " ".join([
            str(test_data.get("name", "")),
            str(test_data.get("objective", "")),
            str(test_data.get("description", ""))
        ]).lower()

        return any(indicator in test_text for indicator in smoke_indicators)

    def _is_edge_case(self, test_data: dict) -> bool:
        """Identify edge case patterns."""
        edge_indicators = ["edge", "boundary", "negative", "error", "exception", "invalid"]
        test_text = " ".join([
            str(test_data.get("name", "")),
            str(test_data.get("objective", "")),
            str(test_data.get("description", ""))
        ]).lower()

        return any(indicator in test_text for indicator in edge_indicators)
```

#### 2.2 Precondition Analysis

Enhance precondition parsing to support Zephyr's standardized approach:

```python
class ZephyrPreconditionAnalyzer:
    """Analyze and structure test preconditions."""

    STANDARD_PRECONDITIONS = [
        "YJ Installed",
        "Communication Prepared",
        "Socket(s) Open",
        "Agent Stamped",
        "Agent Deployed",
        "CLI Connected to Active Agent"
    ]

    def analyze_preconditions(self, precondition_text: str) -> list[dict]:
        """Parse precondition text into structured steps."""
        if not precondition_text:
            return []

        steps = []

        # Parse numbered or bulleted preconditions
        lines = precondition_text.strip().split('\n')
        current_step = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for step numbering
            if line[0].isdigit() and ('.' in line or ')' in line):
                if current_step:
                    steps.append(current_step)
                current_step = {"description": line.split('.', 1)[-1].split(')', 1)[-1].strip()}
            elif line.startswith('-') or line.startswith('*'):
                if current_step:
                    steps.append(current_step)
                current_step = {"description": line[1:].strip()}
            else:
                # Continuation of current step
                if current_step:
                    current_step["description"] += " " + line
                else:
                    current_step = {"description": line}

        if current_step:
            steps.append(current_step)

        return steps

    def detect_hyperlinked_test_cases(self, precondition_text: str) -> list[str]:
        """Extract references to other test cases in preconditions."""
        # Look for patterns like "See test case X" or hyperlinked test names
        test_case_refs = []

        # Simple regex patterns for test case references
        import re

        # Pattern for test case keys (e.g., PROJ-123)
        test_key_pattern = r'\b[A-Z]+-\d+\b'
        test_case_refs.extend(re.findall(test_key_pattern, precondition_text))

        # Pattern for test names in quotes
        test_name_pattern = r'"([^"]+)"'
        test_case_refs.extend(re.findall(test_name_pattern, precondition_text))

        return test_case_refs
```

### Phase 3: Enhanced Zephyr API Integration

#### 3.1 Comprehensive Test Case Retrieval

Update the `ZephyrClient` to fetch complete test case structures:

```python
# Enhanced API_PATTERNS in ZephyrClient
API_PATTERNS = [
    # Existing patterns...

    # Comprehensive Zephyr pattern with full field mapping
    {
        "name": "comprehensive_zephyr",
        "testcase_search": "/rest/atm/1.0/testcase/search",
        "requires_keys_stage": False,
        "supports_field_selection": True,
        "field_mapping": {
            "details": ["status", "priority", "component", "owner", "estimatedTime"],
            "traceability": ["issues", "confluence", "webLinks"],
            "platforms": ["supportedPlatforms", "testLevel"],
            "script": ["testScript.step", "testScript.testData", "testScript.expectedResult"]
        }
    }
]
```

#### 3.2 Enhanced Bayesian Scoring

Update format detection to recognize Zephyr-specific patterns:

```python
# Add to evidence_collector.py or format detection
ZEPHYR_EVIDENCE_PATTERNS = {
    "testScript": 0.9,           # Strong Zephyr indicator
    "precondition": 0.8,         # Zephyr methodology
    "objective": 0.7,           # Zephyr naming convention
    "stepDescription": 0.6,      # Zephyr step structure
    "expectedResult": 0.6,       # Zephyr verification approach
    "supportedPlatforms": 0.8,   # Zephyr platform support
    "testLevel": 0.9,           # Zephyr classification
    "linkedCRS": 0.8            # Zephyr requirement tracking
}

# Enhanced detection for Zephyr field patterns
def detect_zephyr_evidence(data: dict) -> dict[str, float]:
    """Detect Zephyr-specific evidence patterns."""
    evidence = {}
    data_str = str(data).lower()

    for field, confidence in ZEPHYR_EVIDENCE_PATTERNS.items():
        if field.lower() in data_str:
            evidence[field] = confidence

    return evidence
```

### Phase 4: Platform-Agnostic Test Generation

#### 4.1 Robot Framework Conversion with Platform Support

Enhance test generation to handle Zephyr's platform variations:

```python
class ZephyrPlatformAgnosticGenerator:
    """Generate platform-agnostic Robot Framework tests."""

    def generate_platform_variations(self, step_data: dict) -> list[str]:
        """Generate Robot Framework steps for multiple platforms.

        Convert Zephyr format:
        TARGET: ip addr
        ESXi: esxcli network ip interface list
        OTHER: ifconfig

        To Robot Framework:
        Run Keyword If    '${PLATFORM}' == 'linux'    Run Process    ip addr
        Run Keyword If    '${PLATFORM}' == 'esxi'    Run Process    esxcli network ip interface list
        Run Keyword If    '${PLATFORM}' == 'other'    Run Process    ifconfig
        """
        robot_steps = []

        if "testData" in step_data:
            platform_commands = self._parse_platform_commands(step_data["testData"])

            # Generate conditional steps for each platform
            for platform, commands in platform_commands.items():
                if commands:
                    for command in commands:
                        robot_keyword = self._convert_command_to_keyword(command)
                        platform_condition = self._get_platform_condition(platform)

                        robot_step = f"Run Keyword If    '${{PLATFORM}}' {platform_condition}    {robot_keyword}"
                        robot_steps.append(robot_step)

        return robot_steps

    def _parse_platform_commands(self, test_data: str) -> dict[str, list[str]]:
        """Parse platform-specific commands from test data."""
        parser = PlatformCommandParser()
        return parser.parse_platform_commands(test_data)

    def _convert_command_to_keyword(self, command: str) -> str:
        """Convert shell command to Robot Framework keyword."""
        # Basic implementation - can be enhanced with keyword inference
        return f"Run Process    {command}"

    def _get_platform_condition(self, platform: str) -> str:
        """Get Robot Framework condition for platform."""
        platform_mapping = {
            "TARGET": "== 'linux'",
            "ESXi": "== 'esxi'",
            "EMBEDDED": "== 'embedded'",
            "OTHER": "== 'other'"
        }
        return platform_mapping.get(platform, "== 'default'")

    def generate_variables(self, test_data: dict) -> dict:
        """Extract and format variables from test data.

        Convert Zephyr {variable} format to Robot Framework ${variable} format.
        """
        variables = {}

        # Extract variables from test script
        if "testScript" in test_data:
            script_content = str(test_data["testScript"])

            # Find {variable} patterns
            import re
            var_pattern = r'\{([^}]+)\}'
            matches = re.findall(var_pattern, script_content)

            for var in matches:
                robot_var = f"${{{var}}}"
                variables[robot_var] = f"# TODO: Set value for {var}"

        return variables
```

#### 4.2 Enhanced Bronze Layer Processing

Update the bronze layer to handle Zephyr's structured approach:

```python
class ZephyrBronzeProcessor:
    """Enhanced bronze layer processing for Zephyr test cases."""

    def process_zephyr_test(self, raw_data: dict) -> dict:
        """Process Zephyr test case with full structure preservation."""
        return {
            "test_case_core": {
                "name": self._extract_name(raw_data),
                "objective": self._extract_objective(raw_data),
                "precondition": self._extract_precondition(raw_data),
                "details": self._extract_details(raw_data)
            },
            "test_script": {
                "steps": self._extract_platform_agnostic_steps(raw_data)
            },
            "metadata": {
                "level": self._extract_test_level(raw_data),
                "platforms": self._extract_supported_platforms(raw_data),
                "traceability": self._extract_traceability(raw_data),
                "classification": self._classify_test(raw_data)
            }
        }

    def _extract_name(self, data: dict) -> str:
        """Extract test case name."""
        name_fields = ["name", "title", "summary"]
        for field in name_fields:
            if field in data and data[field]:
                return str(data[field])
        return "Untitled Test"

    def _extract_objective(self, data: dict) -> str:
        """Extract test objective."""
        objective_fields = ["objective", "description", "documentation"]
        for field in objective_fields:
            if field in data and data[field]:
                return str(data[field])
        return ""

    def _extract_precondition(self, data: dict) -> dict:
        """Extract and analyze preconditions."""
        precondition_fields = ["precondition", "preconditions", "setup"]
        for field in precondition_fields:
            if field in data and data[field]:
                analyzer = ZephyrPreconditionAnalyzer()
                return {
                    "raw": str(data[field]),
                    "structured": analyzer.analyze_preconditions(str(data[field])),
                    "linked_tests": analyzer.detect_hyperlinked_test_cases(str(data[field]))
                }
        return {}

    def _extract_details(self, data: dict) -> dict:
        """Extract test case details."""
        details = {}
        detail_fields = ["status", "priority", "component", "owner", "estimatedTime", "folder"]

        for field in detail_fields:
            if field in data:
                details[field] = data[field]

        return details

    def _extract_platform_agnostic_steps(self, data: dict) -> list[dict]:
        """Extract steps with platform variations."""
        steps = []

        # Look for testScript structure
        if "testScript" in data and isinstance(data["testScript"], dict):
            script_data = data["testScript"]

            # Handle Zephyr step structure
            if "step" in script_data or "testData" in script_data:
                # Process as structured Zephyr steps
                steps = self._process_zephyr_steps(script_data)
            else:
                # Process as generic step list
                steps = self._process_generic_steps(script_data)

        # Look for direct steps array
        elif "steps" in data and isinstance(data["steps"], list):
            steps = data["steps"]

        return steps

    def _process_zephyr_steps(self, script_data: dict) -> list[dict]:
        """Process Zephyr-structured test script."""
        steps = []

        # Handle arrays of step data
        step_fields = ["step", "testData", "expectedResult"]

        # Find the longest array to determine number of steps
        max_steps = 0
        for field in step_fields:
            if field in script_data and isinstance(script_data[field], list):
                max_steps = max(max_steps, len(script_data[field]))

        # Build step objects
        for i in range(max_steps):
            step = {}
            for field in step_fields:
                if (field in script_data and
                    isinstance(script_data[field], list) and
                    i < len(script_data[field])):
                    step[field] = script_data[field][i]

            if step:  # Only add non-empty steps
                steps.append(step)

        return steps

    def _extract_test_level(self, data: dict) -> dict:
        """Extract test level classification."""
        classifier = ZephyrTestLevelClassifier()
        level_name, level_value = classifier.classify_test(data)

        return {
            "name": level_name,
            "value": level_value,
            "raw": data.get("testLevel", "")
        }

    def _extract_supported_platforms(self, data: dict) -> list[str]:
        """Extract supported platforms."""
        platform_fields = ["supportedPlatforms", "platforms", "targets"]

        for field in platform_fields:
            if field in data:
                platforms = data[field]
                if isinstance(platforms, list):
                    return platforms
                elif isinstance(platforms, str):
                    return [platforms]

        return ["All Platforms"]  # Default assumption

    def _extract_traceability(self, data: dict) -> dict:
        """Extract traceability information."""
        traceability = {}

        traceability_fields = ["issues", "confluence", "webLinks", "linkedCRS", "requirements"]
        for field in traceability_fields:
            if field in data:
                traceability[field] = data[field]

        return traceability

    def _classify_test(self, data: dict) -> dict:
        """Classify test with multiple dimensions."""
        return {
            "is_zephyr": is_zephyr_test_case(data),
            "has_preconditions": bool(self._extract_precondition(data)),
            "has_traceability": bool(self._extract_traceability(data)),
            "platform_specific": len(self._extract_supported_platforms(data)) > 0,
            "complexity_score": self._calculate_complexity_score(data)
        }

    def _calculate_complexity_score(self, data: dict) -> int:
        """Calculate test complexity score."""
        score = 0

        # Base score for having structured elements
        if "testScript" in data:
            score += 2
        if "precondition" in data:
            score += 1
        if self._extract_traceability(data):
            score += 1

        # Score for number of steps
        steps = self._extract_platform_agnostic_steps(data)
        score += min(len(steps), 5)  # Cap at 5 for steps

        # Score for platform variations
        platforms = self._extract_supported_platforms(data)
        if len(platforms) > 1:
            score += 2

        return score
```

## Implementation Strategy

### Phase 1: Foundation (Week 1-2)
- Implement enhanced field definitions
- Add Zephyr test case detection
- Create platform command parser
- Update format detection with Zephyr patterns

### Phase 2: Analysis and Classification (Week 3-4)
- Implement test level classifier
- Create precondition analyzer
- Enhance Bayesian scoring for Zephyr
- Add comprehensive test structure processing

### Phase 3: API Integration (Week 5-6)
- Enhance Zephyr client for complete data retrieval
- Update API patterns for field mapping
- Implement traceability data extraction
- Add platform support detection

### Phase 4: Test Generation (Week 7-8)
- Implement platform-agnostic Robot Framework generation
- Create variable extraction and conversion
- Add conditional step generation for platforms
- Enhance bronze layer processing

### Phase 5: Testing and Documentation (Week 9-10)
- Comprehensive testing with real Zephyr data
- Update documentation with Zephyr examples
- Performance optimization
- User acceptance testing

## Success Metrics

### Functional Metrics
- **Accuracy**: 95%+ correct parsing of Zephyr test case structures
- **Completeness**: Preserve all test case metadata and traceability
- **Platform Support**: Handle 90%+ of platform variation patterns
- **API Coverage**: Support all major Zephyr API endpoint patterns

### Quality Metrics
- **Test Level Classification**: 90%+ accuracy in test level detection
- **Precondition Analysis**: Extract and structure 85%+ of precondition data
- **Traceability Preservation**: Maintain 100% of requirement links
- **Robot Framework Output**: Generate executable tests for 95%+ of cases

### Performance Metrics
- **Processing Time**: Maintain sub-second processing per test case
- **Memory Usage**: No significant increase in memory footprint
- **API Efficiency**: Optimized data retrieval with minimal requests
- **Scalability**: Handle large test suites (1000+ test cases) efficiently

## Testing Strategy

### Unit Tests
- Field definition parsing and detection
- Platform command parsing accuracy
- Test level classification correctness
- Precondition analysis completeness

### Integration Tests
- End-to-end Zephyr API integration
- Complete test case processing pipeline
- Robot Framework generation validation
- Platform variation handling

### Performance Tests
- Large dataset processing benchmarks
- Memory usage profiling
- API request optimization validation
- Concurrent processing capabilities

### Acceptance Tests
- Real-world Zephyr instance validation
- Customer test suite conversion
- Generated test execution verification
- User experience feedback collection

## Risks and Mitigations

### Technical Risks
- **Zephyr API Variability**: Different Zephyr instances may have different API structures
  - *Mitigation*: Flexible API pattern discovery with fallback strategies

- **Complex Platform Variations**: Some test cases may have intricate platform-specific logic
  - *Mitigation*: Extensible platform parser with configurable patterns

- **Test Case Structure Evolution**: Zephyr may update its test case structure
  - *Mitigation*: Flexible parsing with backward compatibility

### Business Risks
- **Customer Adoption**: Users may require training on enhanced features
  - *Mitigation*: Comprehensive documentation and examples

- **Performance Impact**: Enhanced processing may slow down conversion
  - *Mitigation*: Performance testing and optimization

- **Maintenance Overhead**: Additional complexity may increase maintenance
  - *Mitigation*: Modular design with clear separation of concerns

## Conclusion

This enhancement plan positions Importobot as the premier tool for organizations using Zephyr Scale, enabling them to maintain their sophisticated testing methodology while leveraging automated Robot Framework conversion. The phased approach ensures manageable development with clear deliverables and success metrics.

The implementation will significantly enhance Importobot's value proposition by:

1. **Preserving Testing Methodology**: Maintain Zephyr's structured approach to test case design
2. **Platform Flexibility**: Handle sophisticated platform-agnostic test designs
3. **Requirement Traceability**: Preserve complete audit trails from requirements to tests
4. **Automated Conversion**: Generate high-quality Robot Framework tests automatically
5. **Enterprise Integration**: Support large-scale testing operations with comprehensive API coverage

This enhancement will make Importobot particularly valuable for organizations with mature testing processes using Zephyr Scale or similar structured test management systems.