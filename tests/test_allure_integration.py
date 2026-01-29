"""Tests for allure.id() marker collection"""
import json
from pathlib import Path

import pytest
import allure


# Separate the verification tests from the data generation tests
# This file contains both test cases with allure_id markers AND tests that verify collection


@allure.id("TEST-001")
def test_with_allure_id():
    """Test with allure.id marker"""
    assert True


@allure.id("TEST-002")
def test_another_with_allure_id():
    """Another test with allure.id marker"""
    assert 1 + 1 == 2


@allure.id("TEST-003")
@pytest.mark.skip(reason="Skipped test with allure ID")
def test_skipped_with_allure_id():
    """Skipped test with allure.id marker"""
    pass


def test_without_allure_id():
    """Test without allure.id marker"""
    assert True


@allure.id("TEST-005")
@pytest.mark.parametrize("value", [1, 2, 3])
def test_parametrized_with_allure_id(value):
    """Parametrized test with allure.id marker"""
    assert value > 0


class TestAllureIdCollection:
    """Test class to verify allure_id collection"""
    
    @allure.id("TEST-100")
    def test_in_class_with_allure_id(self):
        """Test in class with allure.id marker"""
        assert True
    
    def test_in_class_without_allure_id(self):
        """Test in class without allure.id marker"""
        assert True

