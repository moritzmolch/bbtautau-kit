"""
Unit tests for the xyh.filters.util module.

This module tests the Wrapper and WrapperMeta metaclass implementation,
including class creation, registration, and the wrap decorator functionality.
"""

import inspect
from collections import OrderedDict

import pytest

# Import the module under test
from xyh.core.wrapper import Wrapper, WrapperMeta

# =============================================================================
# Tests for WrapperMeta Metaclass
# =============================================================================


@pytest.fixture(autouse=True)
def setup_wrapper_meta():
    """Fixture to reset the WrapperMeta registry before each test."""
    WrapperMeta._register.clear()
    yield
    WrapperMeta._register.clear()


class TestWrapperMeta:
    """Tests for the WrapperMeta metaclass."""

    def test_wrapper_meta_creates_class(self):
        """Test that WrapperMeta correctly creates a new class."""

        # Define a simple class dictionary with __module__ and __call__ set
        cls_dict = {
            "__module__": "test_module",
            "__call__": lambda self: OrderedDict(),
        }
        TestClass = WrapperMeta("TestClass", (Wrapper,), cls_dict)

        # Validate base class attributes
        assert TestClass.__name__ == "TestClass"
        assert TestClass.__module__ == "test_module"

        # Validate inheritance
        assert issubclass(TestClass, Wrapper)

        # Validate that the __call__ method is set
        assert callable(TestClass.__call__)

        # Validate that the __call__ method returns expected output
        assert TestClass.__call__(object) == OrderedDict()

    def test_wrapper_meta_adds_lambda_function_as_method(self):
        """
        Test that WrapperMeta correctly adds a lambda function in cls_dict as
        method.
        """

        # Define a simple class dictionary with __module__ and __call__ set
        cls_dict = {
            "add": lambda self, a, b: a + b,
            "__call__": lambda self: OrderedDict(),  # needs to be implemented
        }
        TestClass = WrapperMeta("TestClass", (Wrapper,), cls_dict)
        instance = TestClass()

        # Verify that the add method is available
        assert hasattr(TestClass, "add")

        # Verify that add is a method and has expected input parameters
        assert inspect.ismethod(instance.add)
        assert list(inspect.signature(instance.add).parameters.keys()) == [
            "a",
            "b",
        ]

        # Verify that add method code runs
        assert instance.add(2, 3) == 5

    def test_wrapper_meta_adds_def_function_as_method(self):
        """
        Test that WrapperMeta correctly adds a function with positional and
        keyword arguments in cls_dict as method.
        """

        # Define a test function with arguments and keyword arguments
        def get(self, name: str, default: str = "default"):
            return name if name is not None else default

        # Define a simple class dictionary with __module__ and __call__ set
        cls_dict = {
            "get": get,
            "__call__": lambda self: OrderedDict(),  # needs to be implemented
        }
        TestClass = WrapperMeta("TestClass", (Wrapper,), cls_dict)
        instance = TestClass()

        # Verify that the get method is available
        assert hasattr(TestClass, "get")

        # Verify that get is a method and has expected input parameters
        assert inspect.ismethod(instance.get)
        assert list(inspect.signature(instance.get).parameters.keys()) == [
            "name",
            "default",
        ]

        # Verify that get method code runs
        assert instance.get("test") == "test"
        assert instance.get(None, default="default") == "default"

    def test_wrapper_meta_registers_class(self):
        """Test that created classes are registered in _register."""
        cls_dict = {"__call__": lambda self: OrderedDict()}
        TestRegisterClass = WrapperMeta(
            "TestRegisterClass", (Wrapper,), cls_dict
        )

        assert "TestRegisterClass" in WrapperMeta._register
        assert WrapperMeta._register["TestRegisterClass"] is TestRegisterClass

    def test_wrapper_meta_raises_error_for_duplicate_names(self):
        """Test that duplicate class names raise ValueError."""
        cls_dict = {"__call__": lambda self: OrderedDict()}

        # First creation should succeed
        WrapperMeta("UniqueClass", (Wrapper,), cls_dict)

        # Second creation with same name should fail
        with pytest.raises(
            ValueError,
            match="Wrapper class with name UniqueClass already exists",
        ):
            WrapperMeta("UniqueClass", (Wrapper,), cls_dict)

    def test_wrapper_meta_raises_error_when_call_is_missing(self):
        """Test that classes without __call__ method raise ValueError."""
        cls_dict = {"__module__": "test.module"}  # No __call__ method

        MissingWrapper = WrapperMeta("MissingCallMethod", (Wrapper,), cls_dict)

        with pytest.raises(
            TypeError,
            match=(
                "Can't instantiate abstract class .* abstract method "
                + "'__call__'"
            ),
        ):
            # Attempt to instantiate without providing a concrete __call__
            # implementation
            MissingWrapper()
