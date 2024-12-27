# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "google-generativeai",
#     "pyperclip",
#     "click>=8.0.0",
#     "pytest>=7.0.0",
#     "pytest-cov>=4.1.0",
#     "coverage>=7.4.0",
#     "requests>=2.31.0",
# ]
# ///

import sys
import pathlib
import subprocess
import requests
from typing import Optional, Union
import google.generativeai as genai
import pyperclip
import click

def load_prompt_template(path_or_url: Union[pathlib.Path, str]) -> str:
    """Load the XML prompt template from the given path or URL."""
    if isinstance(path_or_url, pathlib.Path):
        if not path_or_url.exists():
            raise click.ClickException(f"Prompt template file not found: {path_or_url}")
        return path_or_url.read_text()
    else:
        try:
            response = requests.get(path_or_url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise click.ClickException(f"Failed to fetch template from URL: {str(e)}")

def get_git_diff(repo_path: pathlib.Path, compare_branch: str = "main") -> str:
    """Get git diff between current branch and specified branch."""
    try:
        # Get current branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        current_branch = result.stdout.strip()
        
        if current_branch == compare_branch:
            raise click.ClickException(
                f"Current branch '{current_branch}' is the same as comparison branch '{compare_branch}'"
            )
        
        # Get the diff
        result = subprocess.run(
            ["git", "--no-pager", "diff", compare_branch + "...HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        if not result.stdout:
            raise click.ClickException("No differences found between branches")
            
        return result.stdout
        
    except subprocess.CalledProcessError as e:
        if e.stderr:
            raise click.ClickException(f"Git error: {e.stderr}")
        raise click.ClickException(f"Failed to execute git command: {str(e)}")

def generate_pr_description(template: str, diff_content: str, api_key: str) -> str:
    """Generate PR description using Gemini API."""
    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp')
    
    # Replace placeholder with diff content
    prompt = template.replace("[[user-input]]", diff_content)
    
    try:
        response = model.generate_content(prompt)
        if response.text:
            # Extract content between OUTPUT markers
            parts = response.text.split("### OUTPUT ###")
            if len(parts) > 1:
                output_parts = parts[1].split("### END OUTPUT ###")
                if len(output_parts) > 0:
                    return output_parts[0].strip()
            return response.text
        else:
            raise click.ClickException("No response generated from Gemini")
    except Exception as e:
        raise click.ClickException(f"Error generating content: {str(e)}")

@click.command()
@click.option(
    '--repo-path',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=pathlib.Path),
    default=pathlib.Path.cwd(),
    help='Path to the git repository (defaults to current directory)'
)
@click.option(
    '--template',
    type=str,
    default='https://raw.githubusercontent.com/kkeeling/pr-generator-cli/refs/heads/main/write-pr-volato-prompt.xml',
    help='Path or URL to the XML prompt template file'
)
@click.option(
    '--compare-branch',
    type=str,
    default='main',
    help='Branch to compare against (defaults to "main")'
)
@click.option(
    '--api-key',
    envvar=['GEMINI_API_KEY', 'GOOGLE_API_KEY'],
    help='Google API key (can be set via GEMINI_API_KEY or GOOGLE_API_KEY environment variable)'
)
def main(
    repo_path: pathlib.Path,
    template: str,
    compare_branch: str,
    api_key: Optional[str]
):
    """Generate a PR description using Google's Gemini AI and copy it to clipboard.
    
    This tool compares the current branch against a specified branch (default: main),
    generates a PR description using the diff, and copies it to your clipboard.
    """
    if not api_key:
        raise click.ClickException(
            "No API key provided. Set either GEMINI_API_KEY or GOOGLE_API_KEY environment variable, "
            "or provide --api-key option"
        )

    try:
        diff_content = get_git_diff(repo_path, compare_branch)
        template_content = load_prompt_template(template)
        
        print(f"\nAnalyzing changes between current branch and '{compare_branch}'...")
        pr_description = generate_pr_description(template_content, diff_content, api_key)
        
        # Copy to clipboard and print
        pyperclip.copy(pr_description)
        print("\nGenerated PR Description:")
        print("-" * 40)
        print(pr_description)
        print("-" * 40)
        print("\nThe PR description has been copied to your clipboard!")
        
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
