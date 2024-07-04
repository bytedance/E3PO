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
import cv2
import numpy as np
import yaml
from e3po.utils import get_logger
from e3po.utils.projection_utilities import fov_to_3d_polar_coord
from e3po.utils.json import get_tile_info


def video_analysis(user_data, video_info):
    """
    This API allows users to analyze the full 360 video (if necessary) before the pre-processing starts.
    Parameters
    ----------
    user_data: is initially set to an empy object and users can change it to any structure they need.
    video_info: is a dictionary containing the required video information.

    Returns
    -------
    user_data:
        user should return the modified (or unmodified) user_data as the return value.
        Failing to do so will result in the loss of the information stored in the user_data object.
    """
    user_data = user_data or {}
    user_data["video_analysis"] = []

    return user_data


def init_user(user_data, video_info):
    """
    Initialization function, user initializes their parameters based on the content passed by E3PO

    Parameters
    ----------
    user_data: None
        the initialized user_data is none, where user can store their parameters
    video_info: dict
        video information of original video, user can perform preprocessing according to their requirement

    Returns
    -------
    user_data: dict
        the updated user_data
    """

    user_data = user_data or {}
    user_data["video_info"] = video_info
    user_data["config_params"] = read_config()

    return user_data


def read_config():
    """
    read the user-customized configuration file as needed

    Returns
    -------
    config_params: dict
        the corresponding config parameters
    """

    config_path = os.path.dirname(os.path.abspath(__file__)) + "/freedom.yml"
    with open(config_path, 'r', encoding='UTF-8') as f:
        opt = yaml.safe_load(f.read())['approach_settings']
    vam_size = opt['video']['vam_size']
    crop_factor = [eval(v) for v in opt['video']['crop_factor']]
    scale_factors = {k: eval(v) for k, v in opt['video']['scale_factors'].items()}
    sampling_size = [50, 50]

    config_params = {
        "vam_size": vam_size,
        "crop_factor": crop_factor,
        "scale_factors": scale_factors,
        "sampling_size": sampling_size
    }

    return config_params


def transcode_video(curr_video_frame, curr_frame_idx, network_stats, motion_history, user_data, video_info):
    """
    Transcode the video frame

    Parameters
    ----------
    curr_video_frame: array
        current video frame content
    curr_frame_idx: int
        current frame index
    network_stats: list
        network information
    motion_history: list
        historical motion information, each item with format {yaw, pitch, roll}
    user_data: dict
        user related parameters and information
    video_info: dict
        store video information

    Returns
    -------
    vam_frame: array
        transcode video frame
    user_video_spec: dict
        a dictionary storing user specific information for the preprocessed video
    user_data: dict
        updated user_data
    """

    if user_data is None or "video_info" not in user_data:
        user_data = init_user(user_data, video_info)

    config_params = user_data['config_params']

    scale = motion_history[-1]['motion_record']['scale']
    yaw = motion_history[-1]['motion_record']['yaw']
    pitch = motion_history[-1]['motion_record']['pitch']

    src_height, src_width = curr_video_frame.shape[:2]
    start_width = src_width * (config_params['scale_factors'][scale] - config_params['crop_factor'][0]) / 2
    start_height = src_height * (config_params['scale_factors'][scale] - config_params['crop_factor'][1]) / 2

    # u: azimuthal angle, v: polar angle
    u = (np.linspace(0.5, config_params['vam_size'][0] - 0.5, config_params['vam_size'][0]) + start_width) / (
            src_width * config_params['scale_factors'][scale]) * np.pi * 2
    v = (np.linspace(0.5, config_params['vam_size'][1] - 0.5, config_params['vam_size'][1]) + start_height) / (
            src_height * config_params['scale_factors'][scale]) * np.pi

    # convert the image coordinates to coordinates in 3D
    x = np.outer(np.sin(v), np.cos(u))
    y = np.outer(np.sin(v), np.sin(u))
    z = np.outer(np.cos(v), np.ones(np.size(u)))

    # rotation angles
    a, b, r = [yaw, -pitch, 0]  # the rotation matrix needs a negative sign

    # rotation matrix
    rot_a = np.array([np.cos(a) * np.cos(b), np.cos(a) * np.sin(b) * np.sin(r) - np.sin(a) * np.cos(r),
                      np.cos(a) * np.sin(b) * np.cos(r) + np.sin(a) * np.sin(r)])
    rot_b = np.array([np.sin(a) * np.cos(b), np.sin(a) * np.sin(b) * np.sin(r) + np.cos(a) * np.cos(r),
                      np.sin(a) * np.sin(b) * np.cos(r) - np.cos(a) * np.sin(r)])
    rot_c = np.array([-np.sin(b), np.cos(b) * np.sin(r), np.cos(b) * np.cos(r)])

    # rotate the image to the correct place
    xx = rot_a[0] * x + rot_a[1] * y + rot_a[2] * z
    yy = rot_b[0] * x + rot_b[1] * y + rot_b[2] * z
    zz = rot_c[0] * x + rot_c[1] * y + rot_c[2] * z
    xx = np.clip(xx, -1, 1)
    yy = np.clip(yy, -1, 1)
    zz = np.clip(zz, -1, 1)

    # calculate the (u, v) in the original equirectangular map
    map_u = ((np.arctan2(yy, xx) + 2 * np.pi) % (2 * np.pi)) * src_width / (2 * np.pi) - 0.5
    map_v = np.arccos(zz) * src_height / np.pi - 0.5
    map_u = np.clip(map_u, 0, src_width - 1)
    map_v = np.clip(map_v, 0, src_height - 1)
    dstMap_u, dstMap_v = cv2.convertMaps(map_u.astype(np.float32), map_v.astype(np.float32), cv2.CV_16SC2)

    # remap the frame according to pitch and yaw
    vam_frame = cv2.remap(curr_video_frame, dstMap_u, dstMap_v, cv2.INTER_LINEAR)

    user_video_spec = {
        'segment_info': {'yaw': yaw, 'pitch': pitch, 'scale': scale},
        'tile_info': {'chunk_idx': curr_frame_idx, 'tile_idx': 1}
    }

    return vam_frame, user_video_spec, user_data


def generate_display_result(curr_display_frames, current_display_chunks, curr_fov, dst_video_frame_uri, frame_idx, video_size, user_data, video_info):
    """
    Generate the required fov images for the freedom approach

    Parameters
    ----------
    curr_display_frames: list
        current available video tile frames
    current_display_chunks: list
        current available video chunks
    curr_fov: dict
        current fov information, with format {"curr_motion", "range_fov", "fov_resolution"}
    dst_video_frame_uri: str
        the uri of generated fov frame
    frame_idx: int
        frame index of current display frame
    video_size: dict
        the video.json file generated after video preprocessing
    user_data: dict
        user related parameters and information
    video_info: dict
        video information for evaluation

    Returns
    -------
    user_data: dict
        updated user_data
    """

    if user_data is None or "video_info" not in user_data:
        user_data = init_user(user_data, video_info)

    client_fov = [float(curr_fov['curr_motion']['yaw']), float(curr_fov['curr_motion']['pitch']), 0]

    frame_idx_temp = frame_idx
    if frame_idx_temp > len(current_display_chunks) - 1:
        frame_idx_temp = len(current_display_chunks) - 1
    server_fov = get_server_fov(video_size, frame_idx_temp)

    # generate client image
    _3d_polar_coord = fov_to_3d_polar_coord(client_fov, curr_fov['range_fov'], curr_fov['fov_resolution'])
    coord_x_arr, coord_y_arr = _3d_polar_coord_to_pixel_coord(_3d_polar_coord, server_fov, user_data)
    fov_result = generate_fov_img(curr_display_frames[0], coord_x_arr, coord_y_arr)

    # write the calculated fov image into file
    cv2.imwrite(dst_video_frame_uri, fov_result, [cv2.IMWRITE_JPEG_QUALITY, 100])
    get_logger().debug(f'[evaluation] end get display img {frame_idx}')

    return user_data


def get_server_fov(video_size, frame_idx):
    """
    Get motion information of the corresponding vam frame
    Parameters
    ----------
    video_size
    frame_idx

    Returns
    -------

    """
    tile_id = f"chunk_{str(frame_idx).zfill(4)}_tile_{str(1).zfill(3)}"

    tile_info = get_tile_info(video_size, tile_id)

    segment_info = tile_info['user_video_spec']['segment_info']

    server_motion = {
        "pitch": segment_info["pitch"],
        "yaw": segment_info["yaw"],
        "scale": segment_info["scale"]
    }

    return server_motion


def generate_fov_img(curr_display_frame, coor_x_arr, coor_y_arr):
    """
    Generate fov image from the current available frame

    Parameters
    ----------
    curr_display_frame: array
        current available frame, i.e., vam in freedom approach
    coor_x_arr: array
        horizontal pixel coordinates
    coor_y_arr: array
        vertical pixel coordinates

    Returns
    -------
    fov_result: array
        the generated fov frame result
    """

    dst_map_u, dst_map_v = cv2.convertMaps(coor_x_arr.astype(np.float32), coor_y_arr.astype(np.float32), cv2.CV_16SC2)
    fov_result = cv2.remap(curr_display_frame, dst_map_u, dst_map_v, cv2.INTER_LINEAR)

    return fov_result


def _3d_polar_coord_to_pixel_coord(_3d_polar_coord, curr_motion, user_data):
    """
    For the freedom approach, generate corresponding pixel coordinates from 3d polar coordinates

    Parameters
    ----------
    _3d_polar_coord: array
        3d polar coordinate
    curr_motion: dict
        motion for generating the display frame, with format {yaw, pitch, scale}
    user_data: dict
        user related parameters and information
    Returns
    -------
    coor_x_arr: array
        horizontal pixel coordinates
    coor_y_arr: array
        vertical pixel coordinates
    """

    config_params = user_data['config_params']
    server_scale = curr_motion['scale']
    a, b, r = [curr_motion['yaw'], -curr_motion['pitch'], 0]
    rot_a = np.array([np.cos(a) * np.cos(b), np.sin(a) * np.cos(b), -np.sin(b)])
    rot_b = np.array([np.cos(a) * np.sin(b) * np.sin(r) - np.sin(a) * np.cos(r),
                      np.sin(a) * np.sin(b) * np.sin(r) + np.cos(a) * np.cos(r), np.cos(b) * np.sin(r)])
    rot_c = np.array([np.cos(a) * np.sin(b) * np.cos(r) + np.sin(a) * np.sin(r),
                      np.sin(a) * np.sin(b) * np.cos(r) - np.cos(a) * np.sin(r), np.cos(b) * np.cos(r)])

    u, v = np.split(_3d_polar_coord, 2, axis=-1)
    u = u.reshape(u.shape[:2])
    v = v.reshape(v.shape[:2])

    u = np.pi + u
    v = np.pi / 2 - v

    x = np.sin(v) * np.cos(u)
    y = np.sin(v) * np.sin(u)
    z = np.cos(v)

    xx = rot_a[0] * x + rot_a[1] * y + rot_a[2] * z
    yy = rot_b[0] * x + rot_b[1] * y + rot_b[2] * z
    zz = rot_c[0] * x + rot_c[1] * y + rot_c[2] * z
    xx = np.clip(xx, -1, 1)
    yy = np.clip(yy, -1, 1)
    zz = np.clip(zz, -1, 1)

    u = (np.arctan2(yy, xx) + np.pi * 2) % (np.pi * 2) - np.pi
    v = np.pi / 2 - np.arccos(zz)

    # calculate Vam coverage
    view_coverage_width = config_params['crop_factor'][0] / config_params['scale_factors'][server_scale] * (2 * np.pi)
    view_coverage_height = config_params['crop_factor'][1] / config_params['scale_factors'][server_scale] * np.pi
    view_coverage_height = view_coverage_height if view_coverage_height <= np.pi else np.pi
    coor_x_arr = (u / view_coverage_width + 0.5) * config_params['vam_size'][0] - 0.5
    coor_y_arr = (-v / view_coverage_height + 0.5) * config_params['vam_size'][1] - 0.5

    vam_width, vam_height = config_params['vam_size']
    coor_x_arr = np.clip(coor_x_arr, 0, vam_width - 1)
    coor_y_arr = np.clip(coor_y_arr, 0, vam_height - 1)

    return coor_x_arr, coor_y_arr