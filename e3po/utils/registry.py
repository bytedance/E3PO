# E3PO, an open platform for 360˚ video streaming simulation and evaluation.
# Copyright 2023 ByteDance Ltd. and/or its affiliates
#
# This file is part of E3PO.
#
# E3PO is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# E3PO is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see:
#    <https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html>

class Registry:
    """
    The registrar provides a dictionary that stores the name and content of a class or function.

    Parameters
    ----------
    registry_name : str
        Name of specific registry.

    Attributes
    ----------
    _name : str
        Name of specific registry.
    _content : dict
        Content of this registry.

    Examples
    --------
    >> test_registry = Registry('test_registry')

    >> @test_registry.register()

    >> class MyClass:

    ...
    """
    def __init__(self, registry_name=None):
        self._name = registry_name
        self._content = dict()

    def register(self, obj=None):
        if obj is None:
            def wrapper(object):
                name = object.__name__
                if name in self._content:
                    print(f"[error] Object {name} has been registered in {self._name}!")
                self._content[name] = object
                return object
            return wrapper
        name = obj.__name__
        if name in self._content:
            print(f"[error] Object {name} has been registered in {self._name}!")
        self._content[name] = obj

    def __getitem__(self, key):
        return self._content[key]


data_registry = Registry('data_registry')
decision_registry = Registry('decision_registry')
evaluation_registry = Registry('evaluation_registry')