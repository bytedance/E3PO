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

# Read all file names in 'decision' folder.
# Then import all the decision modules that end with '_decision.py'
eval_folder = os.path.dirname(os.path.abspath(__file__))
for file_name in scan_file_name(eval_folder, '_decision.py'):
    importlib.import_module(f'e3po.decision.{file_name}')


def build_decision(opt):
    """
    Build decision from options.

    Parameters
    ----------
    opt : dict
        It must contain a key named: 'decision_type'

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
    assert opt['decision_type'], '[creat decision] Do not specify decision_type.'
    decision = decision_registry[opt['decision_type']](opt)
    get_logger().info(f'[creat decision] {decision.__class__.__name__} is created')
    return decision
