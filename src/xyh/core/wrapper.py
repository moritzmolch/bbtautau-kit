import inspect
from abc import ABCMeta, abstractmethod
from collections import OrderedDict


class WrapperMeta(ABCMeta):
    _register = {}

    def __new__(meta_cls, cls_name, bases, cls_dict):
        # Check if a Wrapper class with the same name has already been
        # registered
        if cls_name in meta_cls._register:
            raise ValueError(
                f"Wrapper class with name {cls_name} already exists"
            )

        # Create the new class and add it to the internal register
        cls = super().__new__(meta_cls, cls_name, bases, cls_dict)
        meta_cls._register[cls_name] = cls

        return cls

    def get_class(cls, cls_name):
        """
        Retrieve a registered Wrapper class by name.

        Parameters
        ----------
        cls_name : str
            The name of the Wrapper class to retrieve.

        Returns
        -------
        type
            The registered Wrapper class.
        """
        return cls._register.get(cls_name)


class Wrapper(metaclass=WrapperMeta):
    """
    Wrap a function and add it as __call__ method to a new class with the name
    of the wrapped function.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self._args = args
        self._kwargs = kwargs

    @abstractmethod
    def _wrapped_func(self) -> OrderedDict[str, str]:
        """
        Abstract method that must be implemented by subclasses.
        This method will be used in `__call__` when the wrapper instance is
        invoked.
        """
        raise NotImplementedError(
            "Subclasses must implement the __wrapped_func__ method."
        )

    def _sanitize_expression(self, expression: str):
        # Strip spaces and remove '\n' characters
        return " ".join(
            [
                line.strip()
                for line in expression.split("\n")
                if len(line.strip()) > 0
            ]
        )

    @abstractmethod
    def __call__(self) -> OrderedDict[str, str]:
        """
        Abstract method that must be implemented by subclasses.
        This method will be called when the wrapper instance is invoked.
        """

        # Get the 'raw' result from the __wrapped_func method
        result = self._wrapped_func()

        # Sanitize the expressions (remove linebreaks and extra whitespace)
        for key, value in result.copy().items():
            result[key] = self._sanitize_expression(value)

        return result

    def get_instance(self, cls_name: str):
        return self.get_class(cls_name)(*self._args, **self._kwargs)

    @classmethod
    def wrap(
        cls,
        func=None,
    ):
        """
        Decorator to wrap a function and create a new Wrapper subclass with the
        function as its __call__ method.

        Parameters
        ----------

        func : callable
            The function to be wrapped.

        Returns
        -------
        type
            A new subclass of Wrapper with the wrapped function as its __call__
            method.
        """
        # Get the first element in the stack, i.e., the module before entering
        # the parent module of `WrapperMeta`
        frame = inspect.stack()[1]
        module = inspect.getmodulename(frame.filename)
        cls_name = func.__name__

        # Construct the class dictionary with the function as the 'run' method
        cls_dict = {
            "__module__": module,
            "_wrapped_func": func,
            "__call__": func,
        }

        # Create a new class that inherits from Wrapper
        wrapper_class = WrapperMeta(cls_name, (cls,), cls_dict)

        return wrapper_class
