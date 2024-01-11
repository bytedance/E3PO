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
import os.path as osp


def write_video_json(json_path, dst_video_size, chunk_info, user_video_spec):
    """
    Write result to json file in json_path

    Parameters
    ----------
    json_path : str
        Absolute path of json file
    dst_video_size : list
        In json format
    chunk_info: dict
        chunk information
    user_video_spec:
        User specific video results

    """
    fpath, _ = osp.split(json_path)
    os.makedirs(fpath, exist_ok=True)

    chunk_idx = user_video_spec['tile_info']['chunk_idx']
    tile_idx = user_video_spec['tile_info']['tile_idx']
    if tile_idx != -1:
        result_video_name = f"chunk_{str(chunk_idx).zfill(4)}_tile_{str(tile_idx).zfill(3)}"
    else:
        result_video_name = f"chunk_{str(chunk_idx).zfill(4)}_background"

    if osp.exists(json_path):
        with open(json_path, 'r') as file:
            json_data = json.load(file)
        json_data[result_video_name] = {
            'video_size': dst_video_size,
            'user_video_spec': user_video_spec,
            'chunk_info': chunk_info
        }
        with open(json_path, 'w') as file:
            json.dump(json_data, file, indent=2, sort_keys=True)
    else:
        with open(json_path, "w", encoding='utf-8') as file:
            json_data = {
                result_video_name: {
                    'video_size': dst_video_size,
                    'user_video_spec': user_video_spec,
                    'chunk_info': chunk_info
                }
            }
            json.dump(json_data, file, indent=2, sort_keys=True)


def write_decision_json(json_path, curr_ts, dl_list):
    """
    Given the decision JSON path, write the decision results

    Parameters
    ----------
    json_path: str
        the decision JSON path
    curr_ts: int
        current system timestamp
    dl_list: list
        decided download tile list

    Returns
    -------
        None
    """

    # insert the system timestamp in decision result
    result = []
    for i in range(len(dl_list)):
        tmp_result = dl_list[i]
        tmp_result['decision_data']['system_ts'] = curr_ts
        result.append(tmp_result)

    # update depends on whether there exists json file
    fpath, _ = osp.split(json_path)
    os.makedirs(fpath, exist_ok=True)
    if osp.exists(json_path):
        with open(json_path, 'r') as file:
            existing_data = json.load(file)
        existing_data.extend(result)
        with open(json_path, 'w') as file:
            json.dump(existing_data, file, indent=2, sort_keys=True)
    else:
        with open(json_path, "w", encoding='utf-8') as file:
            json.dump(result, file, indent=2, sort_keys=True)


def read_video_json(video_json_path):
    """
    Read the video_json file

    Parameters
    ----------
    video_json_path: str
        the video json file path

    Returns
    -------
    video_json: dict
        the video size of preprocessed video, with the format of dictionary
    """
    try:
        with open(video_json_path, encoding='UTF-8') as f:
            video_json = json.load(f)
        return video_json
    except Exception as e:
        raise ValueError(f"Error reading file: {video_json_path}")


def read_decision_json(decision_json_path):
    """
    Read the decision_json file

    Parameters
    ----------
    decision_json_path: str
        the decision json file path

    Returns
    -------
    decision_record: dict
        decision record, with the format of dictionary
    """
    if os.path.exists(decision_json_path):
        with open(decision_json_path, encoding="utf-8") as f:
            decision_record = json.load(f)
    return decision_record


def write_evaluation_json(result, json_path):
    """
    Write result to json file in json_path

    Parameters
    ----------
    result : list
        In json format
    json_path : str
        Absolute path of json file.
    """
    fpath, _ = osp.split(json_path)
    os.makedirs(fpath, exist_ok=True)
    if osp.exists(json_path):
        os.remove(json_path)
    with open(json_path, "w", encoding='utf-8') as f:
        json.dump(result, f, indent=2, sort_keys=True)


def get_video_json_size(video_size, chunk_idx, tile_id):
    """
    Read the corresponding file size from video_size.json

    Parameters
    ----------
    video_size: dict
        video size of preprocessed video
    chunk_idx: int
        chunk index, indicates which chunk should be located
    tile_id: str
        tile id, indicates which tile should be located

    Returns
    -------
    tile_size: int
        the corresponding tile size of required tile
    """

    try:
        tile_size = video_size[tile_id]['video_size']
    except KeyError:
        raise Exception(f"[get size error] tile_id={tile_id} not found!")

    return tile_size


def get_tile_info(video_size, tile_id):
    """
    Read the corresponding tile information from video_size.json

    Parameters
    ----------
    video_size: dict
        video size of preprocessed video
    tile_id: str
        tile id, indicates which tile should be located

    Returns
    -------
    tile_info: dict
        the corresponding tile information
    """

    try:
        tile_info = video_size[tile_id]
    except KeyError:
        raise Exception(f"[get size error] tile_id={tile_id} not found!")

    return tile_info


def update_video_json(video_json_path, dst_video_sizes):
    """
    For transcoding approach, update the video size

    Parameters
    ----------
    video_json_path: str
        the path of video json file
    dst_video_sizes: list
        each item records the corresponding video frame size

    Returns
    -------
        None
    """

    video_json = read_video_json(video_json_path)
    for chunk_idx in range(len(dst_video_sizes)):
        frame_size = dst_video_sizes[chunk_idx]['frame_size']
        tile_index = 1
        frame_id = f"chunk_{str(chunk_idx).zfill(4)}_tile_{str(tile_index).zfill(3)}"
        video_json[frame_id]['video_size'] = frame_size

    with open(video_json_path, 'w') as file:
        json.dump(video_json, file, indent=2, sort_keys=True)
