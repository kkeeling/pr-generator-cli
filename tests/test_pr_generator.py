import pathlib
import subprocess
import sys
import requests
from typing import Optional
from unittest.mock import Mock, patch, mock_open
import pytest
import click
from click.testing import CliRunner
import google.generativeai as genai
import pyperclip
from pr_generator_cli import (
    load_prompt_template,
    get_git_diff,
    generate_pr_description,
    main
)

# Test fixtures
@pytest.fixture
def mock_template_path(tmp_path):
    template_file = tmp_path / "test_template.xml"
    template_file.write_text("<template>[[user-input]]</template>")
    return template_file

@pytest.fixture
def mock_repo_path(tmp_path):
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    return repo_dir

# Test load_prompt_template
def test_load_prompt_template_local_success(mock_template_path):
    result = load_prompt_template(mock_template_path)
    assert result == "<template>[[user-input]]</template>"

def test_load_prompt_template_local_file_not_found():
    with pytest.raises(click.ClickException) as exc_info:
        load_prompt_template(pathlib.Path("nonexistent.xml"))
    assert "Prompt template file not found" in str(exc_info.value)

@patch('requests.get')
def test_load_prompt_template_url_success(mock_get):
    mock_response = Mock()
    mock_response.text = "<template>[[user-input]]</template>"
    mock_get.return_value = mock_response
    
    result = load_prompt_template("https://example.com/template.xml")
    assert result == "<template>[[user-input]]</template>"
    mock_get.assert_called_once_with("https://example.com/template.xml")

@patch('requests.get')
def test_load_prompt_template_url_failure(mock_get):
    mock_get.side_effect = requests.RequestException("Failed to fetch")
    
    with pytest.raises(click.ClickException) as exc_info:
        load_prompt_template("https://example.com/template.xml")
    assert "Failed to fetch template from URL" in str(exc_info.value)

# Test get_git_diff
@patch('subprocess.run')
def test_get_git_diff_success(mock_run, mock_repo_path):
    # Mock subprocess.run to return expected values
    mock_run.side_effect = [
        Mock(stdout="feature-branch\n", stderr="", returncode=0),
        Mock(stdout="test diff content", stderr="", returncode=0)
    ]
    
    result = get_git_diff(mock_repo_path, "main")
    assert result == "test diff content"
    
    # Verify correct git commands were called
    assert mock_run.call_count == 2
    mock_run.assert_any_call(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=mock_repo_path,
        capture_output=True,
        text=True,
        check=True
    )
    mock_run.assert_any_call(
        ["git", "--no-pager", "diff", "main...HEAD"],
        cwd=mock_repo_path,
        capture_output=True,
        text=True,
        check=True
    )

def test_get_git_diff_same_branch():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(stdout="main\n", stderr="", returncode=0)
        
        with pytest.raises(click.ClickException) as exc_info:
            get_git_diff(pathlib.Path("."), "main")
        assert "Current branch 'main' is the same as comparison branch 'main'" in str(exc_info.value)

def test_get_git_diff_no_differences():
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = [
            Mock(stdout="feature-branch\n", stderr="", returncode=0),
            Mock(stdout="", stderr="", returncode=0)
        ]
        
        with pytest.raises(click.ClickException) as exc_info:
            get_git_diff(pathlib.Path("."), "main")
        assert "No differences found between branches" in str(exc_info.value)

def test_get_git_diff_git_error():
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git", stderr="fatal: not a git repository"
        )
        
        with pytest.raises(click.ClickException) as exc_info:
            get_git_diff(pathlib.Path("."), "main")
        assert "Git error: fatal: not a git repository" in str(exc_info.value)

# Test generate_pr_description
@patch('google.generativeai.GenerativeModel')
@patch('google.generativeai.configure')
def test_generate_pr_description_success(mock_configure, mock_model_class):
    # Mock the Gemini model response
    mock_model = Mock()
    mock_model.generate_content.return_value = Mock(text="Generated PR description")
    mock_model_class.return_value = mock_model
    
    result = generate_pr_description(
        "<template>[[user-input]]</template>",
        "test diff content",
        "fake-api-key"
    )
    
    assert result == "Generated PR description"
    mock_configure.assert_called_once_with(api_key="fake-api-key")
    mock_model_class.assert_called_once_with('gemini-2.0-flash-thinking-exp')
    mock_model.generate_content.assert_called_once_with("<template>test diff content</template>")

@patch('google.generativeai.GenerativeModel')
@patch('google.generativeai.configure')
def test_generate_pr_description_empty_response(mock_configure, mock_model_class):
    # Mock empty response
    mock_model = Mock()
    mock_model.generate_content.return_value = Mock(text=None)
    mock_model_class.return_value = mock_model
    
    with pytest.raises(click.ClickException) as exc_info:
        generate_pr_description(
            "<template>[[user-input]]</template>",
            "test diff content",
            "fake-api-key"
        )
    assert "No response generated from Gemini" in str(exc_info.value)

@patch('google.generativeai.GenerativeModel')
@patch('google.generativeai.configure')
def test_generate_pr_description_api_error(mock_configure, mock_model_class):
    # Mock API error
    mock_model = Mock()
    mock_model.generate_content.side_effect = Exception("API error")
    mock_model_class.return_value = mock_model
    
    with pytest.raises(click.ClickException) as exc_info:
        generate_pr_description(
            "<template>[[user-input]]</template>",
            "test diff content",
            "fake-api-key"
        )
    assert "Error generating content: API error" in str(exc_info.value)

# Test main CLI command
def test_main_success_with_api_key_option_local_template(mock_template_path, mock_repo_path):
    with patch('pr_generator_cli.load_prompt_template') as mock_load_template, \
         patch('pr_generator_cli.get_git_diff') as mock_get_diff, \
         patch('pr_generator_cli.generate_pr_description') as mock_generate, \
         patch('pyperclip.copy') as mock_copy, \
         patch('click.echo') as mock_echo:
        
        # Mock return values
        mock_load_template.return_value = "<template>[[user-input]]</template>"
        mock_get_diff.return_value = "test diff content"
        mock_generate.return_value = "Generated PR description"
        
        # Create runner and invoke command with --api-key
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                '--repo-path', str(mock_repo_path),
                '--template', str(mock_template_path),
                '--compare-branch', 'main',
                '--api-key', 'fake-api-key'
            ]
        )
        
        assert result.exit_code == 0
        mock_load_template.assert_called_once()
        mock_get_diff.assert_called_once()
        mock_generate.assert_called_once()
        mock_copy.assert_called_once_with("Generated PR description")

def test_main_success_with_gemini_env_var_url_template(mock_repo_path):
    with patch('pr_generator_cli.load_prompt_template') as mock_load_template, \
         patch('pr_generator_cli.get_git_diff') as mock_get_diff, \
         patch('pr_generator_cli.generate_pr_description') as mock_generate, \
         patch('pyperclip.copy') as mock_copy, \
         patch('click.echo') as mock_echo:
        
        # Mock return values
        mock_load_template.return_value = "<template>[[user-input]]</template>"
        mock_get_diff.return_value = "test diff content"
        mock_generate.return_value = "Generated PR description"
        
        # Create runner and invoke command with GEMINI_API_KEY env var
        runner = CliRunner(env={'GEMINI_API_KEY': 'fake-api-key'})
        result = runner.invoke(
            main,
            [
                '--repo-path', str(mock_repo_path),
                '--template', str(mock_template_path),
                '--compare-branch', 'main'
            ]
        )
        
        assert result.exit_code == 0
        mock_load_template.assert_called_once()
        mock_get_diff.assert_called_once()
        mock_generate.assert_called_once()
        mock_copy.assert_called_once_with("Generated PR description")

def test_main_success_with_google_env_var(mock_template_path, mock_repo_path):
    with patch('pr_generator_cli.load_prompt_template') as mock_load_template, \
         patch('pr_generator_cli.get_git_diff') as mock_get_diff, \
         patch('pr_generator_cli.generate_pr_description') as mock_generate, \
         patch('pyperclip.copy') as mock_copy, \
         patch('click.echo') as mock_echo:
        
        # Mock return values
        mock_load_template.return_value = "<template>[[user-input]]</template>"
        mock_get_diff.return_value = "test diff content"
        mock_generate.return_value = "Generated PR description"
        
        # Create runner and invoke command with GOOGLE_API_KEY env var
        runner = CliRunner(env={'GOOGLE_API_KEY': 'fake-api-key'})
        result = runner.invoke(
            main,
            [
                '--repo-path', str(mock_repo_path),
                '--template', str(mock_template_path),
                '--compare-branch', 'main'
            ]
        )
        
        assert result.exit_code == 0
        mock_load_template.assert_called_once()
        mock_get_diff.assert_called_once()
        mock_generate.assert_called_once()
        mock_copy.assert_called_once_with("Generated PR description")

def test_main_no_api_key():
    """Test that the script fails when no API key is provided."""
    with patch.dict('os.environ', {}, clear=True), \
         patch('pathlib.Path.exists') as mock_exists, \
         patch('subprocess.run') as mock_run, \
         patch('pr_generator_cli.load_prompt_template') as mock_load_template, \
         patch('pr_generator_cli.get_git_diff') as mock_get_diff, \
         patch('pr_generator_cli.generate_pr_description') as mock_generate, \
         patch('click.echo') as mock_echo:
        
        # Mock file system and subprocess to prevent actual operations
        mock_exists.return_value = True
        mock_run.return_value = Mock(stdout="feature-branch\n", stderr="", returncode=0)
        
        # Create runner with empty env to ensure no API keys
        runner = CliRunner()
        
        # Invoke command with empty environment
        result = runner.invoke(main, [
            '--repo-path', '.',
            '--compare-branch', 'main',
            '--template', 'test.xml'
        ], env={})
        
        assert result.exit_code == 1
        assert "No API key provided" in result.output
        # Functions should not be called since API key validation happens first
        mock_load_template.assert_not_called()
        mock_get_diff.assert_not_called()
        mock_generate.assert_not_called()
        mock_run.assert_not_called()

def test_main_click_exception(mock_template_path, mock_repo_path):
    with patch('pr_generator_cli.load_prompt_template') as mock_load_template, \
         patch('pr_generator_cli.get_git_diff') as mock_get_diff:
        # Mock ClickException
        mock_load_template.side_effect = click.ClickException("Test error")
        
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                '--repo-path', str(mock_repo_path),
                '--template', str(mock_template_path),
                '--compare-branch', 'main',
                '--api-key', 'fake-api-key'
            ]
        )
        
        assert result.exit_code == 1
        assert "Error: Test error" in result.output

def test_main_unexpected_exception(mock_template_path, mock_repo_path):
    with patch('pr_generator_cli.load_prompt_template') as mock_load_template, \
         patch('pr_generator_cli.get_git_diff') as mock_get_diff:
        # Mock unexpected exception
        mock_load_template.side_effect = Exception("Unexpected error")
        
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                '--repo-path', str(mock_repo_path),
                '--template', str(mock_template_path),
                '--compare-branch', 'main',
                '--api-key', 'fake-api-key'
            ]
        )
        
        assert result.exit_code == 1
        assert "Unexpected error: Unexpected error" in result.output

def test_main_script(monkeypatch):
    """Test the __main__ block."""
    with patch('subprocess.run') as mock_run, \
         patch('google.generativeai.GenerativeModel') as mock_model_class, \
         patch('google.generativeai.configure') as mock_configure, \
         patch('pyperclip.copy') as mock_copy:
        
        # Mock subprocess.run to return expected values
        mock_run.side_effect = [
            Mock(stdout="feature-branch\n", stderr="", returncode=0),
            Mock(stdout="test diff content", stderr="", returncode=0)
        ]
        
        # Mock Gemini API
        mock_model = Mock()
        mock_model.generate_content.return_value = Mock(text="Generated PR description")
        mock_model_class.return_value = mock_model
        
        # Mock sys.argv to provide required arguments
        monkeypatch.setattr('sys.argv', [
                'pr_generator_cli.py',
                '--repo-path', '.',
                '--compare-branch', 'main',
                '--api-key', 'test-key'
            ])
        
        # Read and execute the script
        with open('pr_generator_cli.py', 'r') as f:
            script_content = f.read()
        
        # Create namespace with all required imports
        namespace = {
            '__name__': '__main__',
            'sys': sys,
            'pathlib': pathlib,
            'subprocess': subprocess,
            'genai': genai,
            'pyperclip': pyperclip,
            'click': click,
            'Optional': Optional,
            'load_prompt_template': load_prompt_template,
            'get_git_diff': get_git_diff,
            'generate_pr_description': generate_pr_description,
            'main': main
        }
        
        # Execute the script and expect SystemExit(0) for successful execution
        with pytest.raises(SystemExit) as exc_info:
            exec(script_content, namespace)
        assert exc_info.value.code == 0
        
        # Verify the mocks were called correctly
        mock_run.assert_any_call(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=pathlib.Path('.'),
            capture_output=True,
            text=True,
            check=True
        )
        mock_run.assert_any_call(
            ["git", "--no-pager", "diff", "main...HEAD"],
            cwd=pathlib.Path('.'),
            capture_output=True,
            text=True,
            check=True
        )
        mock_model.generate_content.assert_called_once()
        mock_configure.assert_called_once_with(api_key="test-key")
        mock_copy.assert_called_once_with("Generated PR description")
