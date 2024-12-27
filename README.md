# PR Generator CLI

A command-line tool that uses Google's Gemini AI to automatically generate pull request descriptions from git diffs. The tool analyzes the changes between your current branch and a target branch, then generates a comprehensive PR description in a standardized format.

## Prerequisites

- Python >= 3.12
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- Google API key

## Installation (easier to run directly from repo)

Clone this repository, and then follow basic usage below.

```bash
git clone https://github.com/kkeeling/pr-generator-cli.git
cd pr-generator-cli
uv run pr_generator_cli.py
```

## Usage

The basic usage is:

```bash
uv run pr_generator_cli.py --api-key YOUR_GEMINI_API_KEY
```

This will:

1. Compare your current branch against 'main'
2. Generate a PR description using Gemini AI
3. Copy the description to your clipboard

### Command Options

```bash
uv run pr_generator_cli.py --help
```

- `--repo-path PATH`: Path to the git repository (defaults to current directory)
- `--template PATH/URL`: Path or URL to the XML prompt template file (defaults to GitHub URL of write-pr-volato-prompt.xml)
- `--compare-branch TEXT`: Branch to compare against (defaults to 'main')
- `--api-key TEXT`: Google API key (can be set via GEMINI_API_KEY or GOOGLE_API_KEY environment variable)

### Remote Execution

You can run the script directly from GitHub without cloning the repository:

```bash
uv run https://raw.githubusercontent.com/kkeeling/pr-generator-cli/refs/heads/main/pr_generator_cli.py --api-key your-api-key
```

This will automatically download and execute the latest version of the script.

### Examples

1. Using environment variable for API key:
```bash
# Using GEMINI_API_KEY
export GEMINI_API_KEY=your-api-key
uv run pr_generator_cli.py

# Or using GOOGLE_API_KEY
export GOOGLE_API_KEY=your-api-key
uv run python pr_generator_cli.py
```

2. Comparing against a different branch:
```bash
uv run pr_generator_cli.py --compare-branch develop --api-key your-api-key
```

3. Using a custom template (local file or URL):
```bash
# Local file
uv run pr_generator_cli.py --template custom-template.xml --api-key your-api-key

# URL
uv run pr_generator_cli.py --template https://example.com/custom-template.xml --api-key your-api-key
```

4. Specifying a different repository:
```bash
uv run pr_generator_cli.py --repo-path /path/to/repo --api-key your-api-key
```

## Development

### Setting Up Development Environment

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pr-generator-cli.git
cd pr-generator-cli
```

### Running Tests

Run the test suite:
```bash
uv run pytest
```

Run with coverage report:
```bash
uv run pytest --cov=pr_generator_cli
```

### Project Structure

```
pr-generator-cli/
├── pr_generator_cli.py     # Main CLI script
├── write-pr-volato-prompt.xml  # Default prompt template
├── tests/                  # Test directory
│   ├── conftest.py        # Test configuration
│   └── test_pr_generator.py  # Test cases
├── pytest.ini             # Pytest configuration
└── .coveragerc            # Coverage configuration
```

## Template Format

The tool uses an XML template file to structure the PR description. The default template includes:

1. Pre-submission checklist
2. What the PR accomplishes
3. Code changes description
4. Testing details
5. Bug fix verification (if applicable)
6. Database changes (if any)
7. Additional notes

You can customize the template by creating your own XML file following the same structure as the default template.

## Error Handling

The tool handles various error cases:

- Missing or invalid API key (checks both GEMINI_API_KEY and GOOGLE_API_KEY)
- Git repository errors
- Same branch comparison
- No differences between branches
- Missing template file
- API response errors

Error messages are descriptive and provide guidance on how to resolve the issue.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests to ensure they pass
4. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
