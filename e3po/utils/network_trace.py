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
import json
from collections import OrderedDict
import os


def pre_processing_network_log(opt):
    """
    read network log
    """
    network_log_path = opt['network_trace']['network_file']
    assert os.path.exists(network_log_path), f'[error] {network_log_path} doesn\'t exist'
    network_record = OrderedDict()
    start_ms = 0
    with open(network_log_path, 'r') as f:
        network_data = json.load(f)
        for i in range(len(network_data)):
            network_record[i] = network_data[i]
            network_record[i]['throughput_MBps'] *= opt['network_trace']['network_scale_ratio']
            network_record[i]['start_ms'] = start_ms
            start_ms += network_record[i]['duration_ms']

    return network_record

def update_network(curr_ts, network_last_idx, network_history, network_record):
    """
    Updates the network history based on the current timestamp.

    Parameters
    ----------
    curr_ts : int
        Current system timestamp in milliseconds.
    network_last_idx : int
        Index of the last processed entry in the network_record list, used to avoid reprocessing.
    network_history : list
        A list storing the historical network state records that have already been processed.
    network_record : list of dict
        Full list of network state records. Each record is a dictionary containing at least
        the 'start_ms' field, indicating when the record becomes active.

    Returns
    -------
    network_history : list
        The updated list of processed network state records.
    network_last_idx : int
        The updated index pointing to the last processed entry in network_record.
    """
    for i in range(network_last_idx, len(network_record)):
        if curr_ts >= network_record[i]['start_ms'] and len(network_history) < (i + 1):
            network_history.append(network_record[i])
            network_last_idx = i + 1
        elif curr_ts < network_record[i]['start_ms']:
            break

    return network_history, network_last_idx
