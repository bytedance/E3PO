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

from collections import OrderedDict
import os


def pre_processing_client_log(opt):
    """
    Read and process client logs, return client_record dictionary.

    Parameters
    ----------
    opt : dict
        Configurations.

    Returns
    -------
    dict
        Client record after frame filling. Its insertion order is in ascending order of timestamp.
            key = timestamp,
            value = {'yaw': yaw, 'pitch': pitch, 'scale': scale}
    """
    # read client log
    client_log_path = opt['motion_trace']['motion_file']
    assert os.path.exists(client_log_path), f'[error] {client_log_path} doesn\'t exist'
    interval = int(1000 / opt['motion_trace']['sample_frequency'])
    client_log_user_index = opt['motion_trace']['column_idx']
    client_record = read_client_log(client_log_path, interval, client_log_user_index)

    # frame filling
    interval = int(1000 / opt['motion_trace']['motion_frequency'])
    video_duration = opt['video']['video_duration']
    client_record = frame_interpolation(client_record, interval, video_duration)
    return client_record


def read_client_log(client_log_path, interval, client_log_user_index):
    """
    Read and process client logs, return client_record dictionary.

    Parameters
    ----------
    client_log_path : str
        Path to client log file.
    interval : int
        The motion sampling interval of the original file, in milliseconds.
    client_log_user_index : int
        Indicate which user's data to use。

    Returns
    -------
    dict
        Client record before frame filling. Its insertion order is in ascending order of timestamp.
            key = timestamp,
            value = {'yaw': yaw, 'pitch': pitch, 'scale': scale}
    """
    client_record = OrderedDict()
    with open(client_log_path, 'r') as f:
        _ = f.readline()
        index = 0
        while True:
            line_pitch = f.readline()[:-1].split(' ')
            line_yaw = f.readline()[:-1].split(' ')
            if len(line_pitch) <= 1:
                break
            index += 1
            if index != client_log_user_index:
                continue

            for i in range(len(line_yaw)):
                if i < 280:
                    scale = 2
                elif i < 300:
                    scale = 4
                elif i < 400:
                    scale = 2
                elif i < 500:
                    scale = 4
                else:
                    scale = 2
                client_record[i * interval] = {'yaw': float(line_yaw[i]), 'pitch': float(line_pitch[i]), 'roll': 0, 'scale': scale}

    return client_record


def frame_interpolation(client_record, interval, video_duration):
    """
    For client_record, let any two adjacent ordered record groups of timestamp be (a, b),
    and insert new records between a and b at interval.
    The value of the new record is consistent with that of a.

    Parameters
    ----------
    client_record : dict
        Client record before frame filling. Its insertion order is in ascending order of timestamp.
            key = timestamp,
            value = {'yaw': yaw, 'pitch': pitch, 'scale': scale}
    interval : int
        The motion sampling interval of the original file, in milliseconds.
    video_duration : int
        If the length of client record is not sufficient to cover the video duration,
        unchanged motion records will be inserted at the end of client record.

    Returns
    -------
    dict
        Client record after frame filling.
            key = timestamp,
            value = {'yaw': yaw, 'pitch': pitch, 'scale': scale}
    """
    result_client_record = OrderedDict()

    # If the length of client record is not sufficient to cover the video duration,
    # unchanged motion records will be inserted at the end of client record.
    client_keys = list(client_record.keys())
    if client_keys[-1] <= client_keys[0] + video_duration * 1000:
        client_keys.append(client_keys[0] + video_duration * 1000)
        client_record[client_keys[-1]] = client_record[client_keys[-2]]

    # In Python 3, the order in which dict.keys() returns values is the insertion order,
    # while the insertion order of client_record is in ascending order of timestamp
    for i in range(1, len(client_keys)):
        ts_a = client_keys[i - 1]
        yaw_a = client_record[ts_a]['yaw']
        pitch_a = client_record[ts_a]['pitch']
        ts_b = client_keys[i]
        yaw_b = client_record[ts_b]['yaw']
        pitch_b = client_record[ts_b]['pitch']
        ts_tmp = client_keys[i - 1]
        while ts_tmp < ts_b:
            # If there are duplicate keys, only the saved key value pairs will be saved
            result_client_record[ts_tmp] = {}
            result_client_record[ts_tmp]['yaw'] = yaw_a + (yaw_b - yaw_a) * (ts_tmp - ts_a) / (ts_b - ts_a)
            result_client_record[ts_tmp]['pitch'] = pitch_a + (pitch_b - pitch_a) * (ts_tmp - ts_a) / (ts_b - ts_a)
            result_client_record[ts_tmp]['scale'] = client_record[ts_a]['scale']
            ts_tmp += interval

    return result_client_record
