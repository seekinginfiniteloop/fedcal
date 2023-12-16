# fedcal _meta.py
#
# Copyright (c) 2023 Adam Poulemanos. All rights reserved.
#
# fedcal is open source software subject to the terms of the
# MIT license, found in the
# [GitHub source directory](https://github.com/psuedomagi/fedcal)
# in the LICENSE.md file.
#
# It may be freely distributed, reused, modified, and distributed under the
# terms of that license, but must be accompanied by the license and the
# accompanying copyright notice.

"""
_meta is an internal support module containing the `MagicDelegator`
metaclass, which facilitates cloning magic/dunder methods from the
underlying target class, which is `pd.Timestamp` for `FedStamp` and
`pd.DatetimeIndex` for `FedIndex`.
"""

import inspect
from typing import Any, Callable


class MagicDelegator(type):

    """
    `MagicDelegator` is a metaclass that facilitates cloning magic/dunder
    methods from the target class, which is `pd.Timestamp` for `FedStamp`
    and `pd.DatetimeIndex` for `FedIndex`. This allows us to maintain
    compositional principles, and avoid writing excessive boilerplate.
    Essentially, all we do here is check for magic methods not in the
    child class (i.e. `FedStamp`) and clone them from the target class
    (i.e. `pd.Timestamp`).

    Coupled with attribute delegation to the target class,
    this metaclass enables `FedStamp` and `FedIndex` to
    act as if they were `pd.Timestamp` and `pd.DatetimeIndex`, respectively,
    and seamlessly integrate into pandas operations.
    """

    def __new__(
        mcs,
        cls,
        name: str,
        bases: tuple[type, ...],
        dct: dict[str, Any],
        delegate_to: str | None = None,
        delegate_class: type | None = None,
    ) -> Any:
        """
        Generates a new class with the magic methods cloned from the
        target class.

        Parameters
        ----------
        name
            class name
        bases
            any base classes as a tuple
        dct
            class dictionary

        **delegate_to** (class argument)
            name of new class's target attribute to delegate magic methods to
            (e.g. 'timestamp' for `FedStamp`), by default None
        **delegate_class** (class argument)
            name of the , by default None

        Returns
        -------
            New class (i.e. `FedStamp`) with magic methods cloned from
            target class for target attribute.

        Raises
        ------
        TypeError
            Raises TypeError is delegate_to or delegate_class are None.
        """
        if delegate_to is None or delegate_class is None:
            raise TypeError(
                "MagicDelegator requires 'delegate_to' attribute name and 'delegate_class'"
            )

        @staticmethod
        def create_magic_method(method_name: str) -> Callable[..., Any]:
            """
            Static method used to create magic methods from the target class.

            Parameters
            ----------
            method_name
            Name of the magic method (e.g. `__eq__`)

            Returns
            -------
                Cloned magic method.
            """

            def magic_method(self, *args, **kwargs) -> Any:
                """
                Helper method to call the magic method from the target class.
                This is used to create the magic methods for the new class
                (e.g. we take `pd.Timestamp`'s `__eq__` and clone it for `FedStamp`).

                Parameters
                ----------
                self
                    The instance of the new class.
                *args
                    Positional arguments to pass to the magic method.
                **kwargs
                    Keyword arguments to pass to the magic method.
                    (e.g. `FedStamp.__eq__(self, other)`)


                Returns
                -------
                Any
                    Returns the result of the magic method call.

                Raises
                ------
                AttributeError
                    Raises AttributeError if an attribute name cannot be found
                    in the new class's instance.
                AttributeError
                    Raises AttributeError if the method name cannot be found
                    in the target class.

                """
                if delegate_to not in self.__dict__:
                    raise AttributeError(
                        f"Attribute '{delegate_to}' not found in {self}"
                    )

                delegated_attr = self.__dict__[delegate_to]
                method = getattr(delegated_attr, method_name)
                return method(*args, **kwargs)

            return magic_method

        excluded_methods: set[str] = {
            "__getattr__",
            "__setattr__",
            "__getattribute__",
            "__init__",
            "__new__",
            "__del__",
            "__repr__",
            "__class__",
            "__dict__",
            "__subclasshook",
            "__setstate_cython__",
            "__setstate__",
            "__init_subclass__",
            "__hash__",
            "__getstate__",
            "__dir__",
            "__reduce__",
            "__reduce_ex__",
            "__reduce_cython__",
            "__doc__",
        }
        magic_methods: list[str] = [
            name
            for name, _ in inspect.getmembers(delegate_class, inspect.isroutine)
            if name.startswith("__")
            and name.endswith("__")
            and name not in excluded_methods
        ]

        for method_name in magic_methods:
            if method_name not in dct:
                dct[method_name] = create_magic_method(method_name=method_name)

        return super().__new__(cls, name, bases, dct)
