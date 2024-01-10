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
from e3po.utils.registry import decision_registry


__all__ = ['build_decision']

# Read all file names in 'decision' folder. Then import all the decision modules that end with '_decision.py'
decision_folder = os.path.dirname(os.path.abspath(__file__))

for file_name in scan_file_name(decision_folder, '_decision.py'):
    importlib.import_module(f'e3po.decision.{file_name}')


def build_decision(opt):
    """
    Build decision from options.

    Parameters
    ----------
    opt : dict
        It must contain a key named: 'approach_type'

    Returns
    -------
    object
        Class object generated based on opt.

    Raises
    ------
    KeyError
        Do not specify decision_type or do not found in decision_registry registry.

    Examples
    --------
    >> decision = build_decision(opt)
    """
    opt = deepcopy(opt)
    assert opt['approach_type'], '[create decision] Do not specify data_type.'
    if opt['approach_type'] == 'on_demand':
        approach_data = 'OnDemandDecision'
    elif opt['approach_type'] == 'transcoding':
        approach_data = 'TranscodingDecision'
    else:
        raise ValueError("error when read the approach mode, which should be on_demand or transcoding!")
    decision = decision_registry[approach_data](opt)
    get_logger().info(f'[create decision] {decision.__class__.__name__} is created')
    return decision
