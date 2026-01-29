"""Basic tests to verify the plugin works correctly"""
import pytest


def test_passing():
    """A test that passes"""
    assert 1 + 1 == 2


def test_failing():
    """A test that fails"""
    assert 1 + 1 == 3


@pytest.mark.skip(reason="Testing skip functionality")
def test_skipped():
    """A test that is skipped"""
    assert True


def test_with_marker():
    """A test with custom marker"""
    assert True
