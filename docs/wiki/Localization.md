# Localization Guide

This guide covers the localization (i18n) setup for Mira, including how the system works, contribution guidelines, and instructions for adding new languages via pull requests.

## Table of Contents

- [Overview](#overview)
- [Localization Setup](#localization-setup)
  - [Directory Structure](#directory-structure)
  - [Message Format](#message-format)
  - [Using Translations in Code](#using-translations-in-code)
- [Contribution Guidelines](#contribution-guidelines)
  - [Before You Start](#before-you-start)
  - [Translation Best Practices](#translation-best-practices)
  - [Quality Standards](#quality-standards)
- [Adding New Languages via PRs](#adding-new-languages-via-prs)
  - [Step 1: Fork and Clone](#step-1-fork-and-clone)
  - [Step 2: Create Language Files](#step-2-create-language-files)
  - [Step 3: Add Translations](#step-3-add-translations)
  - [Step 4: Test Your Translations](#step-4-test-your-translations)
  - [Step 5: Submit Pull Request](#step-5-submit-pull-request)
- [Supported Languages](#supported-languages)
  - [Maintaining Translation Completeness](#maintaining-translation-completeness)
- [FAQ](#faq)

---

## Overview

Mira uses a JSON-based localization system to support multiple languages. All user-facing strings are externalized into language files, making it easy for contributors to add translations without modifying the core codebase.

### Key Features

- **JSON-based**: Simple, human-readable format
- **Namespaced keys**: Organized by feature/component
- **Fallback support**: Falls back to English if a translation is missing
- **Variable interpolation**: Supports dynamic values in strings

---

## Localization Setup

### Directory Structure

Localization files are organized in the following structure:

```
mira/
├── locales/
│   ├── en/
│   │   ├── common.json       # Common UI strings
│   │   ├── agents.json       # Agent-related messages
│   │   ├── integrations.json # Integration messages
│   │   └── errors.json       # Error messages
│   ├── es/
│   │   ├── common.json
│   │   ├── agents.json
│   │   ├── integrations.json
│   │   └── errors.json
│   └── [locale_code]/
│       └── ...
└── utils/
    └── i18n.py               # Internationalization utilities
```

### Message Format

Translation files use JSON format with nested keys:

```json
{
  "project_plan": {
    "title": "Project Plan",
    "description": "Generate a comprehensive project plan",
    "milestone": "Milestone {{number}}: {{name}}",
    "task_created": "Task '{{name}}' created successfully"
  },
  "risk_assessment": {
    "title": "Risk Assessment",
    "high_risk": "High Risk",
    "medium_risk": "Medium Risk",
    "low_risk": "Low Risk"
  }
}
```

#### Variable Interpolation

Use double curly braces for variables:
- `{{variable}}` - Simple variable substitution
- `{{count}} items` - Variables can appear anywhere in the string

### Using Translations in Code

```python
from mira.utils.i18n import t, set_locale

# Set the current locale
set_locale('es')

# Get a translated string
message = t('project_plan.title')  # Returns "Plan de Proyecto" in Spanish

# With variables
message = t('project_plan.milestone', number=1, name='Design Phase')
# Returns "Hito 1: Fase de Diseño"
```

---

## Contribution Guidelines

### Before You Start

1. **Check existing translations**: Review the current state of translations for your target language
2. **Coordinate with others**: Check open PRs and issues to avoid duplicate work
3. **Familiarize yourself**: Understand the product terminology and context

### Translation Best Practices

1. **Maintain context**: Understand where each string appears in the application
2. **Keep formatting**: Preserve variables like `{{name}}` exactly as they appear
3. **Be consistent**: Use the same terms throughout for consistency
4. **Cultural adaptation**: Adapt content appropriately for the target culture
5. **Length awareness**: Consider that translations may be longer or shorter than English

### Quality Standards

- ✅ Accurate translation of meaning
- ✅ Correct grammar and spelling
- ✅ Appropriate tone (professional but accessible)
- ✅ Preserved variable placeholders
- ✅ Valid JSON syntax
- ✅ No machine translation without review

---

## Adding New Languages via PRs

### Step 1: Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/Capstone-Mira.git
cd Capstone-Mira

# Add upstream remote
git remote add upstream https://github.com/YellowscorpionDPIII/Capstone-Mira.git

# Create a new branch for your translation
git checkout -b add-language-[locale_code]
# Example: git checkout -b add-language-fr
```

### Step 2: Create Language Files

Create a new directory for your language using the [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) language code:

```bash
# Create the locale directory
mkdir -p mira/locales/[locale_code]

# Copy English files as templates
cp mira/locales/en/*.json mira/locales/[locale_code]/
```

**Language Code Examples:**
- `fr` - French
- `de` - German
- `ja` - Japanese
- `zh` - Chinese (Simplified)
- `zh-TW` - Chinese (Traditional)
- `pt-BR` - Portuguese (Brazil)

### Step 3: Add Translations

Edit each JSON file in your new locale directory:

```json
// mira/locales/fr/common.json
{
  "welcome": "Bienvenue",
  "loading": "Chargement...",
  "error": "Erreur",
  "success": "Succès",
  "cancel": "Annuler",
  "confirm": "Confirmer"
}
```

**Important:**
- Keep all keys from the English version
- Only translate the values, not the keys
- Preserve all `{{variable}}` placeholders
- Maintain valid JSON syntax

### Step 4: Test Your Translations

```bash
# Install dependencies
pip install -r requirements.txt

# Run the test suite to verify JSON validity
python -m unittest discover mira/tests

# Verify your JSON files are valid
python -c "import json; json.load(open('mira/locales/[locale_code]/common.json'))"
```

### Step 5: Submit Pull Request

```bash
# Stage your changes
git add mira/locales/[locale_code]/

# Commit with a descriptive message
git commit -m "Add [Language Name] translations"

# Push to your fork
git push origin add-language-[locale_code]
```

Then create a Pull Request on GitHub with:

**PR Title:** `Add [Language Name] ([locale_code]) translations`

**PR Description Template:**
```markdown
## Summary
This PR adds [Language Name] translations for Mira.

## Checklist
- [ ] All JSON files are valid
- [ ] All keys from English version are present
- [ ] All variable placeholders are preserved
- [ ] Translations have been reviewed for accuracy
- [ ] No machine translation without human review

## Translation Coverage
- [x] common.json (100%)
- [x] agents.json (100%)
- [x] integrations.json (100%)
- [x] errors.json (100%)

## Native Speaker Review
- [ ] Reviewed by a native speaker (if applicable)
```

---

## Supported Languages

| Language | Code | Status | % Complete | Maintainer |
|----------|------|--------|------------|------------|
| English | `en` | ✅ Complete | 100% | Core Team |
| Spanish | `es` | 🚧 In Progress | 45% | - |
| French | `fr` | 📋 Planned | 0% | - |
| German | `de` | 📋 Planned | 0% | - |
| Japanese | `ja` | 📋 Planned | 0% | - |
| Chinese (Simplified) | `zh` | 📋 Planned | 0% | - |

**Legend:**
- ✅ Complete - All strings translated
- 🚧 In Progress - Partial translation
- 📋 Planned - Looking for contributors

Want to help? Pick a language and [open an issue](https://github.com/YellowscorpionDPIII/Capstone-Mira/issues/new) to let us know you're working on it!

### Maintaining Translation Completeness

The "% Complete" column in the table above indicates the translation coverage for each language. This can be maintained manually or automated using translation status tracking.

#### Manual Updates

To manually update the completion percentage:
1. Count the total number of translation keys in the English locale files
2. Count the number of translated (non-empty, non-placeholder) keys in the target language
3. Calculate percentage: `(translated_keys / total_keys) * 100`
4. Update the table above with the new percentage

#### Automation with JSON Summary File

For automated tracking, you can maintain a `translation-status.json` file in the project root or `docs/` directory with the following structure:

```json
{
  "last_updated": "2024-12-08",
  "languages": {
    "en": {
      "total_keys": 150,
      "translated_keys": 150,
      "percentage": 100,
      "last_updated": "2024-12-08"
    },
    "es": {
      "total_keys": 150,
      "translated_keys": 68,
      "percentage": 45,
      "last_updated": "2024-11-15"
    },
    "fr": {
      "total_keys": 150,
      "translated_keys": 0,
      "percentage": 0,
      "last_updated": "2024-10-01"
    }
  }
}
```

**Future Automation Script:**

A Python script can be created (e.g., in `mira/scripts/update_translation_status.py` or a dedicated `scripts/` directory) to automatically generate this file by:
1. Scanning all locale directories in `mira/locales/` (once the localization system is implemented)
2. Counting keys in each JSON file
3. Comparing against the English baseline
4. Generating the `translation-status.json` file

Example command:
```bash
python mira/scripts/update_translation_status.py
# or
python scripts/update_translation_status.py
```

This automation would enable:
- Automatic updates on each commit via CI/CD
- Real-time translation progress tracking
- Identification of missing or outdated translations
- Generation of translation coverage reports

---

## FAQ

### How do I report a translation issue?

Open an issue on GitHub with the label `translation` and include:
- Language affected
- The incorrect string
- The suggested correction
- Context (where the string appears)

### Can I use machine translation?

Machine translation can be used as a starting point, but all translations must be reviewed and refined by a human speaker. Low-quality machine translations will not be accepted.

### What if my language uses different pluralization rules?

For languages with complex pluralization (like Russian, Arabic, etc.), we support ICU message format. Contact the maintainers for guidance on implementing plural forms.

### How often are translations updated?

Translations are typically updated with each minor release. When new strings are added to the English locale, an issue will be opened to track translation updates.

### Who reviews translation PRs?

Translation PRs are reviewed by:
1. Core maintainers for technical correctness (valid JSON, proper formatting)
2. Native speakers in the community (when available)

### How do I become a language maintainer?

Contribute translations consistently and express interest in the corresponding GitHub issue. Maintainers are community members who commit to keeping a language up to date.

---

## Resources

- [ISO 639-1 Language Codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)
- [JSON Syntax Guide](https://www.json.org/)
- [Internationalization Best Practices](https://www.w3.org/International/quicktips/)
- [Contributing to Open Source](https://opensource.guide/how-to-contribute/)

---

**Questions?** Open an issue on GitHub or reach out to the maintainers.
