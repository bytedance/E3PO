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
import os.path as osp


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
            result += [os.path.splitext(os.path.basename(file))[0] for file in files if
                       not file.startswith('.') and file.endswith(suffix)]
    return result


def generate_motion_clock(settings, motion_record):
    """
    Generate client-side clock, based on the motion trace

    Parameters
    ----------
    settings: dict
        system configuration information
    motion_record: list
        motion trace

    Returns
    -------
    motion_clock: list
        generated motion clock, each item represents a system timestamp
    """

    video_duration = settings.system_opt['video']['video_duration'] * 1000
    client_ts = list(motion_record.keys())
    max_motion_ts = video_duration if client_ts[-1] > video_duration else client_ts[-1]
    system_interval = int(1000 / settings.system_opt['motion_trace']['motion_frequency'])
    motion_clock = list(range(0, max_motion_ts, system_interval))

    return motion_clock


def update_motion(motion_ts, curr_ts, motion_history, motion_record):
    """
    Update the motion information.

    Parameters
    ----------
    motion_ts: int
        motion timestamp
    curr_ts: int
        current system timestamp
    motion_history: list
        record historical motion information
    motion_record: dict
        head movement, with format {yaw, pitch, roll}

    Returns
    -------
    motion_history: list
        updated historical motion information
    """

    motion_info = {
        'motion_ts': motion_ts,
        'system_ts': curr_ts,
        'motion_record': motion_record
    }
    motion_history.append(motion_info)

    return motion_history


def save_video_frame(dst_video_frame_uri, dst_video_frame):
    """
    Write video frame to image file

    Parameters
    ----------
    dst_video_frame_uri: str
        the path of destination frame
    dst_video_frame: array
        the video frame content

    Returns
    -------
        None
    """

    cv2.imwrite(dst_video_frame_uri, dst_video_frame, [cv2.IMWRITE_JPEG_QUALITY, 100])


def generate_dst_frame_uri(result_img_path, img_idx):
    """
    Generates the uri of the video frame, with given image index

    Parameters
    ----------
    result_img_path: str
        the path for storing generated images
    img_idx: int
        the image index

    Returns
    -------
    dst_video_frame_uri
        the uri of generated video frame
    """

    dst_video_frame_uri = osp.join(result_img_path, f"{img_idx}.png")
    return dst_video_frame_uri


def get_video_size(dst_video_uri):
    """
    Get the video size after transcoding

    Parameters
    ----------
    dst_video_uri: str

    Returns
    -------
    video_size: int
    """

    video_size = os.path.getsize(dst_video_uri)
    return video_size
