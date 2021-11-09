"""
    This file is part of Align Objects.

    Copyright (C) 2021 Project Studio Q inc.

    Animation Offset Shift is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import importlib
import os


def get_funcs(func_name):
    this_path = os.path.dirname(__file__)
    module_list = [f for f in os.listdir(this_path) if (f.endswith(".py")) and (f != "__init__.py")]
    path_list = ["." + os.path.splitext(f)[0] for f in module_list]

    functions = []
    for path in path_list:
        module = importlib.import_module(path, package=__package__)
        if hasattr(module, func_name):
            functions += [getattr(module, func_name)]
        
    return functions


def register_package():
    for func in get_funcs("register"):
        func()


def unregister_package():
    for func in get_funcs("unregister"):
        func()
