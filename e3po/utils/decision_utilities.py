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

from copy import deepcopy
import numpy as np
from e3po.utils.projection_utilities import fov_to_3d_polar_coord,\
    _3d_polar_coord_to_pixel_coord, pixel_coord_to_tile


def predict_motion_tile(motion_history, motion_history_size, motion_prediction_size):
    """
    Predicting motion with given historical information and prediction window size.
    (As an example, users can implement their customized function.)

    Parameters
    ----------
    motion_history: dict
        a dictionary recording the historical motion, with the following format:

    motion_history_size: int
        the size of motion history to be used for predicting
    motion_prediction_size: int
        the size of motion to be predicted

    Returns
    -------
    list
        The predicted record list, which sequentially store the predicted motion of the future pw chunks.
         Each motion dictionary is stored in the following format:
            {'yaw ': yaw,' pitch ': pitch,' scale ': scale}
    """
    # Use exponential smoothing to predict the angle of each motion within pw for yaw and pitch.
    a = 0.3  # Parameters for exponential smoothing prediction
    hw = [d['motion_record'] for d in motion_history]
    predicted_motion = list(hw)[0]
    for motion_record in list(hw)[-motion_history_size:]:
        predicted_motion['yaw'] = a * predicted_motion['yaw'] + (1-a) * motion_record['yaw']
        predicted_motion['pitch'] = a * predicted_motion['pitch'] + (1-a) * motion_record['pitch']
        predicted_motion['scale'] = a * predicted_motion['scale'] + (1-a) * motion_record['scale']

    # The current prediction method implemented is to use the same predicted motion for all chunks in pw.
    predicted_record = []
    for i in range(motion_prediction_size):
        predicted_record.append(deepcopy(predicted_motion))

    return predicted_record


def tile_decision(predicted_record, video_size, range_fov, chunk_idx, user_data):
    """
    Deciding which tiles should be transmitted for each chunk, within the prediction window
    (As an example, users can implement their customized function.)

    Parameters
    ----------
    predicted_record: dict
        the predicted motion, with format {yaw: , pitch: , scale:}, where
        the parameter 'scale' is used for transcoding approach
    video_size: dict
        the recorded whole video size after video preprocessing
    range_fov: list
        degree range of fov, with format [height, width]
    chunk_idx: int
        index of current chunk
    user_data: dict
        user related data structure, necessary information for tile decision

    Returns
    -------
    tile_record: list
        the decided tile list of current update, each item is the chunk index
    """
    # The current tile decision method is to sample the fov range corresponding to the predicted motion of each chunk,
    # and the union of the tile sets mapped by these sampling points is the tile set to be transmitted.
    config_params = user_data['config_params']
    tile_record = []
    sampling_size = [50, 50]
    converted_width = user_data['config_params']['converted_width']
    converted_height = user_data['config_params']['converted_height']
    for predicted_motion in predicted_record:
        _3d_polar_coord = fov_to_3d_polar_coord([float(predicted_motion['yaw']), float(predicted_motion['pitch']), 0], range_fov, sampling_size)
        pixel_coord = _3d_polar_coord_to_pixel_coord(_3d_polar_coord, config_params['projection_mode'], [converted_height, converted_width])
        coord_tile_list = pixel_coord_to_tile(pixel_coord, config_params['total_tile_num'], video_size, chunk_idx)
        unique_tile_list = [int(item) for item in np.unique(coord_tile_list)]
        tile_record.extend(unique_tile_list)

    if config_params['background_flag']:
        if -1 not in user_data['latest_decision']:
            tile_record.append(-1)

    return tile_record


def generate_dl_list(chunk_idx, tile_record, latest_result, dl_list):
    """
    Based on the decision result, generate the required dl_list to be returned in the specified format.
    (As an example, users can implement their corresponding function.)

    Parameters
    ----------
    chunk_idx: int
        the index of current chunk
    tile_record: list
        the decided tile list of current update, each list item is the chunk index
    latest_result: list
        recording the latest decision result
    dl_list: list
        the decided tile list

    Returns
    -------
    dl_list: list
        updated dl_list
    """

    tile_result = []
    for i in range(len(tile_record)):
        tile_idx = tile_record[i]
        if tile_idx not in latest_result:
            if tile_idx != -1:
                tile_id = f"chunk_{str(chunk_idx).zfill(4)}_tile_{str(tile_idx).zfill(3)}"
            else:
                tile_id = f"chunk_{str(chunk_idx).zfill(4)}_background"
            tile_result.append(tile_id)

    if len(tile_result) != 0:
        dl_list.append(
            {
                'chunk_idx': chunk_idx,
                'decision_data': {
                    'tile_info': tile_result
                }
            }
        )

    return dl_list