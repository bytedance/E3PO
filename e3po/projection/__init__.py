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

import importlib
from copy import deepcopy
import os

from e3po.utils import scan_file_name, get_logger
from e3po.utils.registry import projection_registry


__all__ = ['build_projection']

# Read all file names in 'projection' folder. # Then import all the projection modules that end with '_projection.py'
projection_folder = os.path.dirname(os.path.abspath(__file__))
approaches_projection_folder = os.path.abspath(os.path.join(projection_folder, '..', 'approaches'))

for file_name in scan_file_name(projection_folder, '_projection.py'):
    importlib.import_module(f'e3po.projection.{file_name}')
for file_name in scan_file_name(approaches_projection_folder, '_projection.py'):
    approach_name = file_name[:-11]
    importlib.import_module(f'e3po.approaches.{approach_name}.{file_name}')

def build_projection(opt):
    """
    Build projection from options.

    Parameters
    ----------
    opt : dict
        It must contain a key named: 'projection_type'

    Returns
    -------
    object
        Class object generated based on opt.

    Raises
    ------
    KeyError
        Do not specify projection_type or do not found in projection_registry registry.

    Examples
    --------
    >> projection = build_projection(opt)
    """
    opt = deepcopy(opt)
    assert opt['projection_type'], '[create projection] Do not specify projection_type.'
    projection = projection_registry[opt['projection_type']](opt)
    get_logger().info(f'[create projection] {projection.__class__.__name__} is created')
    return projection
