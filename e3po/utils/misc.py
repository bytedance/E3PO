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

import os
import json


def scan_file_name(dir_path, suffix=None):
    """
    Recursively scan all files with the specified suffix in the target folder and return the file names.

    Parameters
    ----------
    dir_path : str
        Path of the directory.
    suffix : str
        Expected file name suffix.

    Returns
    -------
    list
        All file names that meet the requirements.
    """
    result = []
    for root, dirs, files in os.walk(dir_path, topdown=False):
        if suffix is None:
            result += [os.path.splitext(os.path.basename(file)) for file in files if not file.startswith('.')]
        else:
            result += [os.path.splitext(os.path.basename(file))[0] for file in files if not file.startswith('.') and file.endswith(suffix)]
    return result


def write_json(result, json_path):
    """
    Write result to json file in json_path

    Parameters
    ----------
    result : list
        In json format
    json_path : str
        Absolute path of json file.
    """
    fpath, _ = os.path.split(json_path)
    os.makedirs(fpath, exist_ok=True)
    if os.path.exists(json_path):
        os.remove(json_path)
    with open(json_path, "w", encoding='utf-8') as f:
        json.dump(result, f, indent=2, sort_keys=True)
