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
from e3po.utils.registry import data_registry


__all__ = ['build_data']

# Read all file names in 'data' and 'approaches' folders. Then import all the data modules that end with '_data.py'
data_folder = os.path.dirname(os.path.abspath(__file__))

for file_name in scan_file_name(data_folder, '_data.py'):
    importlib.import_module(f'e3po.data.{file_name}')


def build_data(opt):
    """
    Build data from options.

    Parameters
    ----------
    opt : dict
        It must contain keys named: 'approach_type'

    Returns
    -------
    object
        Class object generated based on opt.

    Raises
    ------
    KeyError
        Do not specify data_type or do not found in data_registry registry.

    Examples
    --------
    >> data = build_data(opt)
    """
    opt = deepcopy(opt)
    assert opt['approach_type'], '[create data] Do not specify data_type.'
    if opt['approach_type'] == 'on_demand':
        approach_data = 'OnDemandData'
    elif opt['approach_type'] == 'transcoding':
        approach_data = 'TranscodingData'
    else:
        raise ValueError("error when read the approach mode, which should be on_demand or transcoding!")
    data = data_registry[approach_data](opt)
    get_logger().info(f'[create data] {data.__class__.__name__} is created')
    return data
