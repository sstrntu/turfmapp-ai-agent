#!/usr/bin/env python3
"""
TURFMAPP Test Runner

Comprehensive test runner for TURFMAPP backend following code.md standards.
Provides different test execution modes and coverage reporting.
"""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path
from typing import List, Optional


def run_command(command: List[str], description: str) -> int:
    """
    Run a command and return its exit code.
    
    Args:
        command: Command to run as list of strings
        description: Human readable description of the command
        
    Returns:
        Exit code of the command
    """
    print(f"\n🔄 {description}")
    print(f"Command: {' '.join(command)}")
    print("=" * 50)
    
    try:
        result = subprocess.run(command, check=False)
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
        return result.returncode
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return 1


def run_basic_tests() -> int:
    """
    Run basic functionality tests.
    
    Returns:
        Exit code (0 for success)
    """
    return run_command(
        ["python", "-m", "pytest", "tests/test_simple.py", "-v"],
        "Basic Functionality Tests"
    )


def run_utility_tests() -> int:
    """
    Run utility function tests.
    
    Returns:
        Exit code (0 for success)
    """
    return run_command(
        ["python", "-m", "pytest", "tests/test_utils/", "-v"],
        "Utility Function Tests"
    )


def run_api_tests() -> int:
    """
    Run API endpoint tests.
    
    Returns:
        Exit code (0 for success)
    """
    return run_command(
        ["python", "-m", "pytest", "tests/test_api/", "-v"],
        "API Endpoint Tests"
    )


def run_core_tests() -> int:
    """
    Run core module tests.
    
    Returns:
        Exit code (0 for success)
    """
    return run_command(
        ["python", "-m", "pytest", "tests/test_core/", "-v"],
        "Core Module Tests"
    )


def run_all_tests() -> int:
    """
    Run all tests.
    
    Returns:
        Exit code (0 for success)
    """
    return run_command(
        ["python", "-m", "pytest", "tests/", "-v"],
        "All Tests"
    )


def run_tests_with_coverage() -> int:
    """
    Run all tests with coverage reporting.
    
    Returns:
        Exit code (0 for success)
    """
    commands = [
        # Run tests with coverage
        (["python", "-m", "pytest", "tests/", "--cov=app", "--cov-report=term-missing", "--cov-report=html", "-v"], 
         "Tests with Coverage Report"),
        
        # Show coverage summary
        (["python", "-m", "coverage", "report", "--show-missing"], 
         "Coverage Summary")
    ]
    
    exit_codes = []
    for command, description in commands:
        exit_codes.append(run_command(command, description))
    
    # Return non-zero if any command failed
    return max(exit_codes)


def run_specific_test(test_path: str) -> int:
    """
    Run a specific test file or test function.
    
    Args:
        test_path: Path to test file or specific test function
        
    Returns:
        Exit code (0 for success)
    """
    return run_command(
        ["python", "-m", "pytest", test_path, "-v"],
        f"Specific Test: {test_path}"
    )


def run_fast_tests() -> int:
    """
    Run tests in fast mode (no coverage, parallel execution).
    
    Returns:
        Exit code (0 for success)
    """
    return run_command(
        ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-x"],
        "Fast Tests (fail fast mode)"
    )


def lint_and_format() -> int:
    """
    Run code linting and formatting checks.
    
    Returns:
        Exit code (0 for success)
    """
    commands = [
        # Check if we have the tools
        (["python", "-c", "import black, flake8"], "Check linting tools availability"),
        
        # Format check
        (["python", "-m", "black", "--check", "--diff", "app/", "tests/"], 
         "Code Formatting Check"),
        
        # Lint check
        (["python", "-m", "flake8", "app/", "tests/", "--max-line-length=120", "--extend-ignore=E203,W503"], 
         "Code Linting Check")
    ]
    
    exit_codes = []
    for command, description in commands:
        exit_codes.append(run_command(command, description))
    
    return max(exit_codes)


def install_test_dependencies() -> int:
    """
    Install test dependencies.
    
    Returns:
        Exit code (0 for success)
    """
    dependencies = [
        "pytest",
        "pytest-asyncio", 
        "pytest-mock",
        "pytest-cov",
        "coverage",
        "black",
        "flake8"
    ]
    
    return run_command(
        ["python", "-m", "pip", "install"] + dependencies,
        "Install Test Dependencies"
    )


def show_help() -> None:
    """Show help message with available commands."""
    help_text = """
🧪 TURFMAPP Test Runner

USAGE:
    python run_tests.py [COMMAND]

COMMANDS:
    basic       Run basic functionality tests only
    utils       Run utility function tests only  
    api         Run API endpoint tests only
    core        Run core module tests only
    all         Run all tests (default)
    coverage    Run all tests with coverage report
    fast        Run tests in fast mode (fail on first error)
    specific    Run specific test (provide test path as second argument)
    lint        Run code linting and formatting checks
    install     Install test dependencies
    help        Show this help message

EXAMPLES:
    python run_tests.py                    # Run all tests
    python run_tests.py basic             # Run basic tests only
    python run_tests.py api               # Run API tests only
    python run_tests.py coverage          # Run with coverage
    python run_tests.py specific tests/test_simple.py::TestBasicFunctionality::test_simple_math

ENVIRONMENT:
    Set TESTING=true environment variable for all test runs.
    
COVERAGE:
    HTML coverage report will be generated in htmlcov/ directory.
    
TEST STRUCTURE:
    tests/
    ├── test_simple.py              # Basic functionality tests
    ├── test_core/                  # Core module tests
    │   ├── test_config.py
    │   └── test_auth.py
    ├── test_api/                   # API endpoint tests
    │   └── test_v1/
    │       ├── test_auth.py
    │       ├── test_chat.py
    │       ├── test_preferences.py
    │       └── test_upload.py
    └── test_utils/                 # Utility function tests
        └── test_sessions.py
    """
    print(help_text)


def main() -> int:
    """
    Main test runner entry point.
    
    Returns:
        Exit code (0 for success)
    """
    # Set testing environment
    import os
    os.environ["TESTING"] = "true"
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        command = "all"
    else:
        command = sys.argv[1].lower()
    
    print(f"🧪 TURFMAPP Test Runner - Command: {command}")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Execute based on command
    if command == "basic":
        return run_basic_tests()
    elif command == "utils":
        return run_utility_tests()
    elif command == "api":
        return run_api_tests()
    elif command == "core":
        return run_core_tests()
    elif command == "all":
        return run_all_tests()
    elif command == "coverage":
        return run_tests_with_coverage()
    elif command == "fast":
        return run_fast_tests()
    elif command == "specific":
        if len(sys.argv) < 3:
            print("❌ Error: Please provide test path for specific command")
            print("Example: python run_tests.py specific tests/test_simple.py")
            return 1
        return run_specific_test(sys.argv[2])
    elif command == "lint":
        return lint_and_format()
    elif command == "install":
        return install_test_dependencies()
    elif command == "help":
        show_help()
        return 0
    else:
        print(f"❌ Error: Unknown command '{command}'")
        print("Run 'python run_tests.py help' for available commands")
        return 1


if __name__ == "__main__":
    exit_code = main()
    print(f"\n🏁 Test runner finished with exit code: {exit_code}")
    sys.exit(exit_code)