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

import os.path as osp
import argparse
import yaml
import os
import sys
import logging
from .logger import get_logger


def get_opt():
    """
    Get options.
    Read command line parameters, read configuration file parameters, and initialize logger.

    Returns
    -------
    dict
        Configurations.

    Examples
    --------
    >> opt = get_opt()
    """
    # Read the command line input parameter.
    parser = argparse.ArgumentParser()
    parser.add_argument('-approach_name', type=str, required=True,
                        help="test approach name")
    parser.add_argument('-approach_type', type=str, required=True,
                        help="approach type")
    args = parser.parse_args()

    project_dir = os.path.dirname(os.path.abspath(__file__)).split('utils')[0]
    opt_path = 'e3po.yml'
    with open(project_dir + opt_path, 'r', encoding='UTF-8') as f:
        opt = yaml.safe_load(f.read())

    opt['approach_name'] = args.approach_name
    opt['approach_type'] = args.approach_type
    opt['project_path'] = project_dir[:-1]

    if not opt['e3po_settings']['video']['origin']['video_dir']:
        opt['e3po_settings']['video']['origin']['video_dir'] = osp.join(project_dir[:-1], 'source', 'video')
    opt['e3po_settings']['motion_trace']['motion_file'] = \
        osp.join(project_dir[:-1], 'source', 'motion_trace', opt['e3po_settings']['motion_trace']['motion_file'])

    # Initialize logger.
    os.makedirs(osp.join(
        opt['project_path'],
        'log',
        opt['test_group'],
        opt['e3po_settings']['video']['origin']['video_name'].split('.')[0]),
        exist_ok=True
    )
    if opt['e3po_settings']['log']['save_log_file']:
        log_file = osp.join(
            opt['project_path'],
            'log',
            opt['test_group'],
            opt['e3po_settings']['video']['origin']['video_name'].split('.')[0],
            f"{opt['approach_name']}_{os.path.basename(sys.modules['__main__'].__file__).split('.')[0]}.log"
        )
        if os.path.exists(log_file):
            os.remove(log_file)
    else:
        log_file = None
    console_log_level = opt['e3po_settings']['log']['console_log_level']
    if not console_log_level:
        console_log_level = logging.INFO
    else:
        assert console_log_level.lower() in ['notset', 'debug', 'info', 'warning', 'error',
                                             'critical'], "[error] log_level wrong. It should be set to the value in [~, 'notset', 'debug', 'info', 'warning', 'error', 'critical']"
        console_log_level = eval(f"logging.{console_log_level.upper()}")
    file_log_level = opt['e3po_settings']['log']['file_log_level']
    if not file_log_level:
        file_log_level = logging.DEBUG
    else:
        assert file_log_level.lower() in ['notset', 'debug', 'info', 'warning', 'error',
                                          'critical'], "[error] log_level wrong. It should be set to the value in [~, 'notset', 'debug', 'info', 'warning', 'error', 'critical']"
        file_log_level = eval(f"logging.{file_log_level.upper()}")
    get_logger(log_file=log_file, console_log_level=console_log_level, file_log_level=file_log_level)

    return opt
