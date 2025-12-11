# Dependency Management Guide

This document explains how dependencies are managed in the Mira project to ensure reproducible builds.

## Overview

Mira uses a two-tier dependency management system:
- **requirements.txt**: Primary dependencies with pinned versions
- **requirements-lock.txt**: Complete lockfile with all transitive dependencies
- **requirements-dev.txt**: Development dependencies with pinned versions
- **requirements-dev-lock.txt**: Complete lockfile for development environment

## Installation

### For Production Use (Recommended)

Install from the lockfile for reproducible builds:

```bash
pip install -r requirements-lock.txt
```

This ensures you get the exact same versions of all dependencies (including transitive ones) that the project was tested with.

### For Development

Install with development dependencies:

```bash
pip install -r requirements-dev-lock.txt
```

This includes testing tools (pytest, pytest-cov, pytest-benchmark) along with all production dependencies.

### For Flexible Installations

If you need more flexibility (e.g., for compatibility with other packages):

```bash
pip install -r requirements.txt
```

Note: This may install newer versions of transitive dependencies than what was tested.

## Updating Dependencies

When you need to update a dependency:

1. Update the version in `requirements.txt` or `requirements-dev.txt`
2. Regenerate the lockfiles:
   ```bash
   pip-compile --output-file=requirements-lock.txt requirements.txt
   pip-compile --output-file=requirements-dev-lock.txt requirements-dev.txt
   ```
3. Test thoroughly with the new versions
4. Run security checks:
   ```bash
   # Check for vulnerabilities
   pip install safety
   safety check --file requirements-lock.txt
   ```
5. Commit all changes

## Primary Dependencies

- **Flask 3.0.0**: Web framework
- **pydantic 2.12.5**: Data validation and settings management
- **pydantic-settings 2.12.0**: Settings management with environment variable support
- **requests 2.31.0**: HTTP library for API integrations

## Development Dependencies

- **pytest 9.0.2**: Testing framework
- **pytest-cov 7.0.0**: Code coverage reporting
- **pytest-benchmark 5.2.3**: Performance benchmarking

## Transitive Dependencies

All transitive dependencies are locked in the lockfiles with exact versions. See:
- `requirements-lock.txt` for the complete production dependency tree
- `requirements-dev-lock.txt` for the complete development dependency tree

## Security

All dependencies have been checked for known vulnerabilities using the GitHub Advisory Database. No vulnerabilities were found at the time of lockfile creation.

To check for new vulnerabilities:
```bash
pip install safety
safety check --file requirements-lock.txt
```

## Continuous Integration

CI/CD pipelines should use the lockfiles to ensure consistent test environments:
```bash
pip install -r requirements-dev-lock.txt
pytest
```
