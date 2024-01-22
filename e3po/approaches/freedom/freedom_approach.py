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
from e3po.utils.projection_utilities import fov_to_3d_polar_coord, _3d_polar_coord_to_pixel_coord
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
        'tile_info': {'chunk_idx': curr_frame_idx, 'tile_idx': 1},
        'curr_ts': motion_history[-1]['system_ts'],
        'motion_ts': motion_history[-1]['motion_ts']
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
    server_fov = get_server_fov(video_size, frame_idx)

    # render vam to the sphere
    ori_erp_img = vam_2_ori_erp(curr_display_frames[0], server_fov, user_data)

    # generate the client image
    _3d_polar_coord = fov_to_3d_polar_coord(client_fov, curr_fov['range_fov'], curr_fov['fov_resolution'])
    pixel_coord = _3d_polar_coord_to_pixel_coord(_3d_polar_coord, 'erp', [3840, 7680])

    dstMap_u, dstMap_v = cv2.convertMaps(pixel_coord[0].astype(np.float32), pixel_coord[1].astype(np.float32),
                                         cv2.CV_16SC2)
    fov_result = cv2.remap(ori_erp_img, dstMap_u, dstMap_v, cv2.INTER_LINEAR)

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


def recover_erp_img(vam_image, erp_height, erp_width, scale_factor):
    """
    Generate the rotated erp image, from which the vam is cropped
    Parameters
    ----------
    vam_image: current available viewport image
    erp_height: original erp height
    erp_width: original erp weight
    scale_factor: parameter for scaling the original erp frame

    Returns
    -------
    the recovered erp image
    """
    scaled_erp_height, scaled_erp_width = int(erp_height * scale_factor), int(erp_width * scale_factor)
    vam_height, vam_width = vam_image.shape[:2]
    scaled_img = np.zeros((scaled_erp_height, scaled_erp_width, 3), np.uint8)
    scaled_img[int(scaled_erp_height / 2 - vam_height / 2):int(scaled_erp_height / 2 + vam_height / 2), int(scaled_erp_width / 2 - vam_width / 2):int(scaled_erp_width / 2 + vam_width / 2), :] = vam_image

    des_size = [erp_width, erp_height]
    erp_img = cv2.resize(scaled_img, des_size, interpolation=cv2.INTER_AREA)

    return erp_img


def vam_2_ori_erp(vam_image, server_motion, user_data):
    """
    Generate the original erp image
    Parameters
    ----------
    vam_image: current available viewport image
    server_motion: server motion
    user_data:

    Returns
    -------
    The original erp image
    """
    scale = server_motion['scale']

    erp_width = user_data['video_info']['width']
    erp_height = user_data['video_info']['height']
    scale_factor = user_data['config_params']['scale_factors'][scale]

    recovered_erp_img = recover_erp_img(vam_image, erp_height, erp_width, scale_factor)

    # target image coordinates in the dst image
    u = np.linspace(0.5, erp_width - 0.5, erp_width) * np.pi * 2 / erp_width
    v = np.linspace(0.5, erp_height - 0.5, erp_height) * np.pi / erp_height

    # Convert the image coordinates to coordinates in 3D
    x = np.outer(np.sin(v), np.cos(u))
    y = np.outer(np.sin(v), np.sin(u))
    z = np.outer(np.cos(v), np.ones(np.size(u)))

    # rotation angles
    a, b, r = [float(server_motion['yaw']), -float(server_motion['pitch']), 0]  # the rotation matrix needs a negative sign

    # inverse rotation matrix
    rot_a = np.array([np.cos(a) * np.cos(b), np.sin(a) * np.cos(b), -np.sin(b)])
    rot_b = np.array([np.cos(a) * np.sin(b) * np.sin(r) - np.sin(a) * np.cos(r),
                      np.sin(a) * np.sin(b) * np.sin(r) + np.cos(a) * np.cos(r), np.cos(b) * np.sin(r)])
    rot_c = np.array([np.cos(a) * np.sin(b) * np.cos(r) + np.sin(a) * np.sin(r),
                      np.sin(a) * np.sin(b) * np.cos(r) - np.cos(a) * np.sin(r), np.cos(b) * np.cos(r)])

    # rotate the image to the correct place
    xx = rot_a[0] * x + rot_a[1] * y + rot_a[2] * z
    yy = rot_b[0] * x + rot_b[1] * y + rot_b[2] * z
    zz = rot_c[0] * x + rot_c[1] * y + rot_c[2] * z
    zz = np.clip(zz, -1, 1)

    # calculate the (u, v) in the original erp map
    map_u = ((np.arctan2(yy, xx) + 2 * np.pi) % (2 * np.pi)) * erp_width / (2 * np.pi) - 0.5
    map_v = np.arccos(zz) * erp_height / np.pi - 0.5

    # remap
    dstMap_u, dstMap_v = cv2.convertMaps(map_u.astype(np.float32), map_v.astype(np.float32), cv2.CV_16SC2)
    ori_erp_img = cv2.remap(recovered_erp_img, dstMap_u, dstMap_v, cv2.INTER_LINEAR)

    return ori_erp_img
