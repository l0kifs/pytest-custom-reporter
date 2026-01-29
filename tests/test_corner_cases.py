"""Comprehensive corner case tests for the custom reporter plugin"""
import time
import pytest


# ============================================================================
# Setup/Teardown Failures
# ============================================================================

@pytest.fixture
def failing_setup():
    """Fixture that fails during setup"""
    raise RuntimeError("Setup failed: database connection error")


@pytest.fixture
def failing_teardown():
    """Fixture that fails during teardown"""
    yield
    raise RuntimeError("Teardown failed: cleanup error")


def test_with_failing_setup(failing_setup):
    """Test that should fail during setup phase"""
    assert True


def test_with_failing_teardown(failing_teardown):
    """Test that should fail during teardown phase"""
    assert True


# ============================================================================
# Special Characters in Messages
# ============================================================================

def test_unicode_in_error_message():
    """Test with unicode characters in error message"""
    expected = "Hello 世界 🌍"
    actual = "Hello World"
    assert expected == actual, f"Expected '{expected}' but got '{actual}'"


def test_emoji_in_assertion():
    """Test with emojis in assertion"""
    assert "🎉" == "🎊", "Party popper doesn't match confetti ball! 🎈"


def test_newlines_in_error():
    """Test with newlines in error message"""
    message = "Line 1\nLine 2\nLine 3"
    assert message == "Single line", "Multi-line\nerror\nmessage"


def test_special_escape_sequences():
    """Test with special escape sequences"""
    assert "\t\r\n" == "normal", "Tab\tCarriage\rReturn\nLinefeed"


def test_very_long_error_message():
    """Test with extremely long error message"""
    long_text = "x" * 10000
    short_text = "y"
    assert long_text == short_text, f"Expected short but got very long: {long_text}"


# ============================================================================
# Different Exception Types
# ============================================================================

def test_type_error():
    """Test that raises TypeError"""
    result = "string" + 123


def test_value_error():
    """Test that raises ValueError"""
    int("not a number")


def test_zero_division_error():
    """Test that raises ZeroDivisionError"""
    result = 1 / 0


def test_attribute_error():
    """Test that raises AttributeError"""
    obj = None
    obj.some_attribute


def test_index_error():
    """Test that raises IndexError"""
    lst = [1, 2, 3]
    item = lst[10]


def test_key_error():
    """Test that raises KeyError"""
    dct = {"a": 1}
    value = dct["nonexistent_key"]


def test_custom_exception():
    """Test that raises custom exception"""
    class CustomError(Exception):
        pass
    
    raise CustomError("This is a custom error with special data: 数据")


# ============================================================================
# Parametrized Tests
# ============================================================================

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
    (4, 7),  # This one will fail
])
def test_parametrized(input, expected):
    """Parametrized test with one failing case"""
    assert input * 2 == expected


@pytest.mark.parametrize("text", [
    "normal",
    "with spaces",
    "with-dashes",
    "unicode_世界",
    "emoji_🎉",
])
def test_parametrized_strings(text):
    """Parametrized test with various string formats"""
    assert len(text) > 0


# ============================================================================
# Multiple Marks
# ============================================================================

@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.database
def test_with_multiple_marks():
    """Test with multiple custom marks"""
    assert True


@pytest.mark.skip(reason="Temporarily disabled")
def test_skipped_with_reason():
    """Test that is explicitly skipped"""
    assert False


@pytest.mark.skipif(True, reason="Conditional skip")
def test_conditional_skip():
    """Test with conditional skip"""
    assert False


@pytest.mark.xfail(reason="Known issue")
def test_expected_failure():
    """Test that is expected to fail"""
    assert False


@pytest.mark.xfail(reason="Should pass but marked as xfail")
def test_unexpected_pass():
    """Test that passes despite xfail mark"""
    assert True


# ============================================================================
# Nested Test Classes
# ============================================================================

class TestOuterClass:
    """Outer test class"""
    
    def test_in_outer_class(self):
        """Test in outer class"""
        assert True
    
    class TestInnerClass:
        """Inner test class"""
        
        def test_in_inner_class(self):
            """Test in inner class"""
            assert True
        
        def test_failing_in_inner_class(self):
            """Failing test in inner class"""
            assert False, "Failed in nested class"


# ============================================================================
# Stdout/Stderr Output
# ============================================================================

def test_with_stdout_output():
    """Test that prints to stdout"""
    print("This is stdout output")
    print("Multiple lines")
    print("With special chars: 世界 🌍")
    assert True


def test_with_stderr_output():
    """Test that prints to stderr"""
    import sys
    print("This is stderr output", file=sys.stderr)
    print("Error message with unicode: 错误", file=sys.stderr)
    assert True


def test_with_both_outputs():
    """Test with both stdout and stderr"""
    import sys
    print("STDOUT: Normal message")
    print("STDERR: Error message", file=sys.stderr)
    assert True


# ============================================================================
# Long Running Tests
# ============================================================================

def test_slow_test():
    """Test that takes some time to execute"""
    time.sleep(0.1)
    assert True


def test_very_slow_test():
    """Test that takes longer to execute"""
    time.sleep(0.2)
    assert True


# ============================================================================
# Complex Assertions
# ============================================================================

def test_complex_dict_comparison():
    """Test with complex nested dictionary comparison"""
    expected = {
        "users": [
            {"name": "Alice", "age": 30, "tags": ["admin", "user"]},
            {"name": "Bob", "age": 25, "tags": ["user"]},
        ],
        "metadata": {
            "version": "1.0",
            "timestamp": "2026-01-29"
        }
    }
    
    actual = {
        "users": [
            {"name": "Alice", "age": 31, "tags": ["admin", "user"]},  # Age differs
            {"name": "Bob", "age": 25, "tags": ["user"]},
        ],
        "metadata": {
            "version": "1.0",
            "timestamp": "2026-01-29"
        }
    }
    
    assert expected == actual


def test_complex_list_comparison():
    """Test with complex list comparison"""
    expected = [1, 2, 3, 4, 5]
    actual = [1, 2, 3, 5, 4]  # Order differs
    assert expected == actual


# ============================================================================
# Edge Cases with Test Names
# ============================================================================

def test_with_very_long_name_that_goes_on_and_on_and_includes_lots_of_details_about_what_is_being_tested_in_this_particular_test_case():
    """Test with extremely long name"""
    assert True


# ============================================================================
# Fixture Combinations
# ============================================================================

@pytest.fixture
def sample_data():
    """Fixture providing sample data"""
    return {"value": 42}


@pytest.fixture
def another_fixture(sample_data):
    """Fixture that depends on another fixture"""
    return sample_data["value"] * 2


def test_with_multiple_fixtures(sample_data, another_fixture):
    """Test using multiple fixtures"""
    assert sample_data["value"] == 42
    assert another_fixture == 84


# ============================================================================
# Tests with Warnings
# ============================================================================

def test_that_triggers_warning():
    """Test that triggers a deprecation warning"""
    import warnings
    warnings.warn("This is deprecated", DeprecationWarning)
    assert True


# ============================================================================
# Empty or Minimal Tests
# ============================================================================

def test_empty_pass():
    """Test with just pass"""
    pass


def test_minimal():
    """Minimal test"""
    assert True


# ============================================================================
# Tests with Context Managers
# ============================================================================

def test_with_pytest_raises():
    """Test using pytest.raises context manager"""
    with pytest.raises(ValueError, match="invalid literal"):
        int("not a number")


def test_with_pytest_warns():
    """Test using pytest.warns context manager"""
    import warnings
    with pytest.warns(DeprecationWarning):
        warnings.warn("deprecated", DeprecationWarning)


# ============================================================================
# Tests with Subprocesses or External Resources
# ============================================================================

def test_with_subprocess():
    """Test that spawns a subprocess"""
    import subprocess
    result = subprocess.run(["echo", "Hello World"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Hello World" in result.stdout


# ============================================================================
# Encoding Issues
# ============================================================================

def test_with_latin1_characters():
    """Test with Latin-1 characters"""
    text = "Café résumé naïve"
    assert len(text) > 0


def test_with_cyrillic_characters():
    """Test with Cyrillic characters"""
    text = "Привет мир"
    assert text == "Hello world", f"Expected English but got Cyrillic: {text}"


def test_with_mixed_encodings():
    """Test with mixed character encodings"""
    text = "English, 中文, العربية, Русский, 日本語"
    assert "English" in text
