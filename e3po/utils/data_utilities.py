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

import cv2
import os
import numpy as np
import os.path as osp
from e3po.utils import get_logger, extract_frame
from e3po.utils.misc import get_video_size
from e3po.utils.projection_utilities import transform_projection


def generate_source_video(settings, ori_video_path, chunk_idx):
    """
    Segment the original video into chunks.

    Parameters
    ----------
    settings: dict
        configuration information of the approach
    ori_video_path: str
        original video path
    chunk_idx: int
        index of current chunk to be generated

    Returns
    -------
    source_video_uri: str
        video uri (uniform resource identifier) of the generated video chunk
    """

    settings.logger.info("[generating chunk] start")
    settings.logger.info(f"[generating chunk] chunk_idx={chunk_idx}")

    source_video_uri = osp.join(settings.work_folder, f'chunk_{str(chunk_idx).zfill(4)}.mp4')
    chunk_duration = settings.chunk_duration
    s_1 = str(chunk_idx * chunk_duration % 60).zfill(2)
    m_1 = str(chunk_idx * chunk_duration // 60).zfill(2)
    h_1 = str(chunk_idx * chunk_duration // 3600).zfill(2)
    s_2 = str(((chunk_idx + 1) * chunk_duration) % 60).zfill(2)
    m_2 = str(((chunk_idx + 1) * chunk_duration) // 60).zfill(2)
    h_2 = str(((chunk_idx + 1) * chunk_duration) // 3600).zfill(2)

    ffmpeg_settings = settings.ffmpeg_settings
    cmd = f"{ffmpeg_settings['ffmpeg_path']} " \
          f"-i {ori_video_path} " \
          f"-threads {ffmpeg_settings['thread']} " \
          f"-preset faster " \
          f"-c:v libx264 " \
          f"-bf 0 " \
          f"-ss {h_1}:{m_1}:{s_1} " \
          f"-to {h_2}:{m_2}:{s_2} " \
          f"-y {source_video_uri} " \
          f"-loglevel {ffmpeg_settings['loglevel']}"
    settings.logger.debug(cmd)
    os.system(cmd)
    settings.logger.info("[generating chunk] end")

    return source_video_uri


def update_chunk_info(settings, chunk_idx):
    """
    Update the information of current chunk

    Parameters
    ----------
    settings: dict
        configuration information of the approach
    chunk_idx: int
        the recorded chunk index of current chunk

    Returns
    -------
    chunk_info: dict
        the updated chunk information
    """

    if settings.approach_mode == "on_demand":
        chunk_info = {
            'chunk_idx': chunk_idx,
            'chunk_duration': settings.chunk_duration,
            'start_second': settings.chunk_duration * chunk_idx,
            'end_second': settings.chunk_duration * (chunk_idx + 1)
        }
    elif settings.approach_mode == "transcoding":
        chunk_info = {
            'chunk_idx': chunk_idx,
            'chunk_duration': 1000 / settings.video_info['video_fps']
        }
    else:
        raise ValueError("error when read the approach mode, which should be on_demand or transcoding!")

    return chunk_info


def encode_dst_video(settings, dst_video_folder, encoding_params, user_video_spec):
    """
    Encode the preprocessed frames into video.

    Parameters
    ----------
    settings: dict
        configuration information of the approach
    dst_video_folder: str
        path of the preprocessed video frames
    encoding_params: dict
        encoding parameters provided by E3PO
    user_video_spec: dict
        a dictionary recording user specific information

    Returns
    -------
    dst_video_uri: str
        video uri (uniform resource identifier) of the encoded video
    """

    if settings.approach_mode == "on_demand":
        chunk_idx = user_video_spec['tile_info']['chunk_idx']
        tile_idx = user_video_spec['tile_info']['tile_idx']
        if tile_idx != -1:  # normal tile stream
            result_video_name = f"chunk_{str(chunk_idx).zfill(4)}_tile_{str(tile_idx).zfill(3)}"
        else:               # background stream
            result_video_name = f"chunk_{str(chunk_idx).zfill(4)}_background"
    elif settings.approach_mode == "transcoding":
        result_video_name = settings.approach_folder_name
    else:
        raise ValueError("error when read the approach mode, which should be on_demand or transcoding!")

    dst_video_uri = osp.join(dst_video_folder, f'{result_video_name}.mp4')
    os.chdir(dst_video_folder)
    cmd = f"{settings.ffmpeg_settings['ffmpeg_path']} " \
          f"-r {encoding_params['video_fps']} " \
          f"-start_number 0 " \
          f"-i %d.png " \
          f"-threads {settings.ffmpeg_settings['thread']} " \
          f"-preset {encoding_params['preset']} " \
          f"-c:v {encoding_params['encoder']} " \
          f"-g {encoding_params['gop']} " \
          f"-bf {encoding_params['bf']} " \
          f"-qp {encoding_params['qp_list'][0]} " \
          f"-y {dst_video_uri} " \
          f"-loglevel {settings.ffmpeg_settings['loglevel']}"
    settings.logger.debug(cmd)
    os.system(cmd)

    return dst_video_uri


def remove_temp_files(dst_video_folder):
    """
    Delete intermediate generated files

    Parameters
    ----------
    dst_video_folder: str
        the folder storing intermediate generated files

    Returns
    -------
        None

    """

    for root, dirs, files in os.walk(dst_video_folder):
        for file in files:
            if file.lower().endswith(".png"):
                file_path = os.path.join(root, file)
                os.remove(file_path)
            if file.lower().endswith(".h264"):
                file_path = os.path.join(root, file)
                os.remove(file_path)
    get_logger().info('[delete the generated png images]')


def remove_temp_video(video_uri):
    """
    Delete intermediate generated videos

    Parameters
    ----------
    video_uri: str
        the video uri of intermediate generated video

    Returns
    -------
        None

    """
    try:
        if os.path.exists(video_uri):
            os.remove(video_uri)
            get_logger().info('[delete the generated video]')
    except Exception as e:
        print(f"An error occurred while deleting the video file {video_uri}: {e}")


def transcode_video(source_video_uri, src_proj, dst_proj, src_resolution, dst_resolution, dst_video_folder, chunk_info, ffmpeg_settings):
    """
    Transcoding videos with different projection formats and different resolutions

    Parameters
    ----------
    source_video_uri: str
        source video uri
    src_proj: str
        source video projection
    dst_proj: str
        destination video projection
    src_resolution: list
        source video resolution with format [height, width]
    dst_resolution: list
        destination video resolution with format [height, width]
    dst_video_folder: str
        path of the destination video
    chunk_info: dict
        chunk information
    ffmpeg_settings: dict
        ffmpeg related information, with format {ffmpeg_path, log_level, thread}

    Returns
    -------
    transcode_video_uri: str
        uri (uniform resource identifier) of the transcode video
    """

    tmp_cap = cv2.VideoCapture()
    assert tmp_cap.open(source_video_uri), f"[error] Can't read video[{source_video_uri}]"
    frame_count = int(tmp_cap.get(cv2.CAP_PROP_FRAME_COUNT))
    tmp_cap.release()

    for frame_idx in range(frame_count):
        source_frame = extract_frame(source_video_uri, frame_idx, ffmpeg_settings)
        pixel_coord = transform_projection(dst_proj, src_proj, dst_resolution, src_resolution)
        dstMap_u, dstMap_v = cv2.convertMaps(pixel_coord[0].astype(np.float32), pixel_coord[1].astype(np.float32), cv2.CV_16SC2)
        transcode_frame = cv2.remap(source_frame, dstMap_u, dstMap_v, cv2.INTER_LINEAR)
        transcode_frame_uri = osp.join(dst_video_folder, f"{frame_idx}.png")
        cv2.imwrite(transcode_frame_uri, transcode_frame, [cv2.IMWRITE_JPEG_QUALITY, 100])

    transcode_video_uri = source_video_uri.split("chunk")[0] + 'transcode_chunk_' + str(chunk_info["chunk_idx"]).zfill(4) + '.mp4'
    # Ensure the highest possible quality
    cmd = f"{ffmpeg_settings['ffmpeg_path']} " \
          f"-start_number 0 " \
          f"-i {osp.join(dst_video_folder, '%d.png')} " \
          f"-threads {ffmpeg_settings['thread']} " \
          f"-c:v libx264 " \
          f"-preset slow " \
          f"-g 30 " \
          f"-bf 0 " \
          f"-qp {10} " \
          f"-y {transcode_video_uri} " \
          f"-loglevel {ffmpeg_settings['loglevel']}"
    os.system(cmd)
    remove_temp_files(dst_video_folder)

    return transcode_video_uri


def segment_video(ffmpeg_settings, source_video_uri, dst_video_folder, segmentation_info):
    """
    Segment video tile from the original video

    Parameters
    ----------
    ffmpeg_settings: dict
        ffmpeg related information
    source_video_uri: str
        video uri of original video
    dst_video_folder: str
        folder path of the segmented video tile
    segmentation_info: dict
        tile information
        
    Returns
    -------
        None
    """

    out_w = segmentation_info['segment_out_info']['width']
    out_h = segmentation_info['segment_out_info']['height']
    start_w = segmentation_info['start_position']['width']
    start_h = segmentation_info['start_position']['height']

    result_frame_path = osp.join(dst_video_folder, f"%d.png")

    cmd = f"{ffmpeg_settings['ffmpeg_path']} " \
          f"-i {source_video_uri} " \
          f"-threads {ffmpeg_settings['thread']} " \
          f"-vf \"crop={out_w}:{out_h}:{start_w}:{start_h}\" " \
          f"-q:v 2 -f image2 {result_frame_path} " \
          f"-loglevel {ffmpeg_settings['loglevel']}"

    os.system(cmd)


def resize_video(ffmpeg_settings, source_video_uri, dst_video_folder, dst_video_info):
    """
    Given width and height, resizing the original video.

    Parameters
    ----------
    ffmpeg_settings: dict
        ffmpeg related information
    source_video_uri: str
        video uri of original video
    dst_video_folder: str
        folder path of the segmented video tile
    dst_video_info: dict
        information of the destination video

    Returns
    -------
        None
    """

    dst_video_w = dst_video_info['width']
    dst_video_h = dst_video_info['height']

    result_frame_path = osp.join(dst_video_folder, f"%d.png")
    cmd = f"{ffmpeg_settings['ffmpeg_path']} " \
          f"-i {source_video_uri} " \
          f"-threads {ffmpeg_settings['thread']} " \
          f"-preset faster " \
          f"-vf scale={dst_video_w}x{dst_video_h}" \
          f",setdar={dst_video_w}/{dst_video_h} " \
          f"-q:v 2 -f image2 {result_frame_path} " \
          f"-loglevel {ffmpeg_settings['loglevel']}"

    os.system(cmd)


def get_video_frame_sizes(ffmpeg_settings, dst_video_uri):
    """
    Extracting frames from the encoded video to obtain the data size of each frame

    Parameters
    ----------
    ffmpeg_settings: dict
        ffmpeg related information
    dst_video_uri: str
        uri of the generated video

    Returns
    -------
    frame_size: list
        a list recording the size of each frame, where each element of the list
        is a dictionary with format {frame_idx, frame_size}
    """

    dst_video_path = osp.dirname(dst_video_uri)
    os.chdir(dst_video_path)

    cmd = f"{ffmpeg_settings['ffmpeg_path']} " \
          f"-i {dst_video_uri} " \
          f"-threads {ffmpeg_settings['thread']} " \
          f"-f image2 " \
          f"-vcodec copy " \
          f"-bsf h264_mp4toannexb " \
          f"-y {osp.join(dst_video_path, '%d.h264')} " \
          f"-loglevel {ffmpeg_settings['loglevel']}"

    os.system(cmd)

    frame_size = []
    frame_num = len([f for f in os.listdir(dst_video_path) if f.endswith('h264')])
    for frame_idx in range(1, frame_num + 1):
        frame_uri = osp.join(dst_video_path, f"{frame_idx}.h264")
        size = get_video_size(frame_uri)
        frame_size.append({
            'frame_idx': frame_idx,
            'frame_size': size
        })

    return frame_size
