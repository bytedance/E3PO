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
import os.path as osp
from copy import deepcopy
from e3po.utils.json import get_video_json_size
from e3po.utils.projection_utilities import \
    fov_to_3d_polar_coord, _3d_polar_coord_to_pixel_coord
from e3po.utils.misc import get_video_size
from e3po.utils.network_trace import update_network
import subprocess


def update_curr_fov(curr_fov, curr_motion):
    """
    Updating current motion information

    Parameters
    ----------
    curr_fov: dict
        recording the fov information, with format {"curr_motion", "range_fov", "fov_resolution"}
    curr_motion: dict
        recording the motion information, with format {"yaw", "pitch", "scale"}

    Returns
    -------
    curr_fov: dict
        updated current fov information
    """

    curr_fov['curr_motion'] = curr_motion
    return curr_fov


def calc_arrival_ts(settings, dl_list, video_size, network_record):
    """
    Calculate the available timestamp of downloaded video tiles

    Parameters
    ----------
    settings: dict
        system configuration information
    dl_list: list
        the decided and downloaded tile list
    video_size: dict
        the video size after video preprocessing
    network_record : list of dict
        Full list of network state records. Each record is a dictionary containing at least
        the 'start_ms' field, indicating when the record becomes active.

    Returns
    -------
    arrival_list: list
        the calculated available tile chunks list
    """

    arrival_list = {}
    rendering_delay = settings.system_opt['network_trace']['rendering_delay']

    network_history = []
    network_last_idx = 0
    curr_network_ts = 0
    last_chunk_complete_time = 0    # Time when the previous chunk finished downloading

    for row in dl_list:
        chunk_idx = row['chunk_idx']
        chunk_size = 0
        for tile_id in row['decision_data']['tile_info']:
            chunk_size += get_video_json_size(video_size, chunk_idx, tile_id)

        need_download_size = chunk_size         # Size of the chunk that needs to be downloaded
        curr_ts = row['decision_data']['system_ts']
        if curr_network_ts < curr_ts:
            curr_network_ts = curr_ts
        if last_chunk_complete_time < curr_ts:  # The previous chunk completed downloading before this one
            last_chunk_complete_time = curr_ts

        while need_download_size > 0:           # The current chunk has not finished downloading
            network_history, network_last_idx = update_network(curr_network_ts, network_last_idx, network_history,
                                                               network_record)
            network_stats = network_history[-1]  # Get the current available bandwidth
            max_download_size = network_stats['throughput_MBps'] * min(network_stats['start_ms'] + network_stats['duration_ms'] - last_chunk_complete_time,
                                                                       network_stats['duration_ms']) * 1000     # In Bytes

            if max_download_size >= need_download_size: # Current available bandwidth can complete the download
                download_delay = chunk_size / network_stats['throughput_MBps'] / 1000   # In ms
                chunk_complete_time = last_chunk_complete_time + download_delay
                need_download_size = 0
                last_chunk_complete_time = chunk_complete_time
            else:
                need_download_size -= max_download_size
                last_chunk_complete_time = network_stats['start_ms'] + network_stats['duration_ms']
                curr_network_ts = network_stats['start_ms'] + network_stats['duration_ms']

        download_delay = chunk_complete_time - row['decision_data']['system_ts']
        playable_ts = row['decision_data']['system_ts'] + download_delay + network_stats['rtt_ms'] + rendering_delay

        if chunk_idx not in arrival_list.keys():                # new chunk
            tmp_arrival_list = []
            for tile_id in row['decision_data']['tile_info']:
                tmp_arrival_list.append(
                    {
                        'playable_ts': playable_ts,
                        'tile_id': tile_id,
                    }
                )
            arrival_list[chunk_idx] = {
                'chunk_idx': chunk_idx,
                'chunk_size': chunk_size,
                'tile_list': tmp_arrival_list
            }
        else:                                           # same chunk
            for tile_id in row['decision_data']['tile_info']:
                arrival_list[chunk_idx]['tile_list'].append(
                    {
                        'playable_ts': playable_ts,
                        'tile_id': tile_id
                    }
                )
            arrival_list[chunk_idx]['chunk_size'] += chunk_size
    settings.logger.info("[decision to playable] end")

    return arrival_list


def get_curr_display_chunks(arrival_list, curr_ts):
    """
    Get the available video tiles for current chunk, before curr_ts

    Parameters
    ----------
    arrival_list: list
        the calculated available tile chunks list, before the current timestamp
    curr_ts: int
        current system timestamp

    Returns
    -------
    curr_display_chunks: list
        currently available chunks, each item with the format {'playable_ts', 'tile_id'}

    """

    curr_display_chunks = []
    for arrival_idx in range(len(arrival_list)):
        if arrival_list[arrival_idx]['tile_list'][0]['playable_ts'] <= curr_ts:
            _tile_list = []
            arrival_chunk_tile_list = arrival_list[arrival_idx]['tile_list']
            for _tile_idx in range(len(arrival_chunk_tile_list)):      # check the playable_ts for each tile
                if arrival_chunk_tile_list[_tile_idx]['playable_ts'] <= curr_ts:
                    _tile_list.append(arrival_chunk_tile_list[_tile_idx])
                else:
                    break
            _arrival_chunk = deepcopy(arrival_list[arrival_idx])
            _arrival_chunk['tile_list'] = _tile_list
            curr_display_chunks.append(_arrival_chunk)
        else:
            continue
    return curr_display_chunks


def get_curr_display_frames(settings, current_display_chunks, curr_ts, frame_idx):
    """
    Retrieve available video frames, before the curr_ts

    Parameters
    ----------
    settings: dict
        system configuration information
    current_display_chunks: list
        each item with the format {'playable_ts', 'tile_id'}
    curr_ts: int
        current system timestamp
    frame_idx: int
        frame index according to the current system timestamp

    Returns
    -------
    curr_display_frames: list
        each item records one available tile frame, according to the current_display_chunks
    """

    curr_display_frames = []
    chunk_idx = int((curr_ts - settings.base_ts) // (settings.video_info['chunk_duration'] * 1000))

    if chunk_idx <= len(current_display_chunks) - 1:                # exists current chunk
        tile_list = current_display_chunks[chunk_idx]['tile_list']
    else:                                                           # not exists current chunk
        print("do not exist current chunks")
        tile_list = current_display_chunks[-1]['tile_list']

    if settings.approach_mode == "on_demand":
        for tile_info in tile_list:
            tile_id = tile_info['tile_id']
            tile_video_path = osp.join(
                settings.dst_video_folder,
                f'{tile_id}.mp4'
            )
            tile_frame = extract_frame(tile_video_path, frame_idx % settings.chunk_frame_num, settings.ffmpeg_settings)
            curr_display_frames.append(tile_frame)
    elif settings.approach_mode == "transcoding":
        tile_video_path = osp.join(
            settings.dst_video_folder,
            f"{settings.approach_folder_name}.mp4"
        )
        if frame_idx > len(current_display_chunks) - 1:
            frame_idx = len(current_display_chunks) - 1
        tile_frame = extract_frame(tile_video_path, frame_idx, settings.ffmpeg_settings)
        curr_display_frames.append(tile_frame)
    else:
        raise ValueError("error when read the approach mode, which should be on_demand or transcoding!")

    return curr_display_frames


def generate_benchmark_result(settings, curr_fov, frame_idx):
    """
    Generate the benchmark fov video frame, with given motion information

    Parameters
    ----------
    settings: dict
        system configuration information
    curr_fov: dict
        current fov information, with format {"curr_motion", "range_fov", "fov_resolution"}
    frame_idx: int
        frame index with current system timestamp

    Returns
    -------
    dst_benchmark_frame_uri: str
        uri of the generated fov frame
    """

    settings.logger.debug(f'[evaluation] start get benchmark img')

    dst_benchmark_frame_uri = osp.join(settings.benchmark_img_path, f"{frame_idx}.png")
    fov_ypr = [float(curr_fov['curr_motion']['yaw']), float(curr_fov['curr_motion']['pitch']), 0]
    _3d_polar_coord = fov_to_3d_polar_coord(fov_ypr, curr_fov['range_fov'], curr_fov['fov_resolution'])

    if not settings.save_benchmark_flag or not os.path.exists(dst_benchmark_frame_uri):
        src_img = extract_frame(settings.ori_video_uri, frame_idx, settings.ffmpeg_settings)
        src_height, src_width = src_img.shape[:2]
        inter_order = get_interpolation(settings.opt['e3po_settings']['metric']['inter_mode'])
        pixel_coord = _3d_polar_coord_to_pixel_coord(_3d_polar_coord, settings.video_info['projection'], [src_height, src_width])
        dstMap_u, dstMap_v = cv2.convertMaps(pixel_coord[0].astype(np.float32), pixel_coord[1].astype(np.float32), cv2.CV_16SC2)
        result = cv2.remap(src_img, dstMap_u, dstMap_v, inter_order)
    else:
        result = np.array(cv2.imread(dst_benchmark_frame_uri))

    if settings.save_benchmark_flag and not os.path.exists(dst_benchmark_frame_uri):
        cv2.imwrite(dst_benchmark_frame_uri, result, [cv2.IMWRITE_JPEG_QUALITY, 100])

    settings.logger.debug(f'[evaluation] end get benchmark img')

    return dst_benchmark_frame_uri


def extract_frame(video_uri, frame_idx, ffmpeg_settings):
    """Extract the video frame of the given index."""
    frame_uri = osp.join(osp.dirname(video_uri), f"{frame_idx}.png")
    cmd = f"{ffmpeg_settings['ffmpeg_path']} " \
          f"-i {video_uri} " \
          f"-vf select='eq(n\,{frame_idx})' " \
          f"-vframes 1 " \
          f"-y {frame_uri} " \
          f"-loglevel {ffmpeg_settings['loglevel']} "
    os.system(cmd)

    assert os.path.exists(frame_uri), f"Error: File {frame_uri} does not exist."
    frame = cv2.imread(frame_uri)
    os.remove(frame_uri)

    return frame


def write_dict(settings, max_bandwidth, total_size, metric_360PI, cost, avg_psnr, avg_ssim, avg_mse, avg_vmaf, gc_score):
    """
    Organize the calculated results into the required dictionary format

    Returns
    -------
    misc_dict: dict
        the final evaluation result, with required dictionary format
    """
    max_bandwidth = round(max_bandwidth / 125 / 1000, 3)
    avg_bandwidth = round(total_size / (settings.video_info['duration']
                                        + settings.pre_download_duration / 1000) / 125 / 1000, 3)
    total_transfer_size = round(total_size / 1000 / 1000, 6)
    metric_360PI = round(metric_360PI, 6)
    gc_score = round(gc_score, 6)

    misc_dict = {
        'MAX bandwidth': f"{max_bandwidth}Mbps",
        'AVG bandwidth': f"{avg_bandwidth}Mbps",
        "AVG PSNR": f"{avg_psnr}dB",
        "AVG SSIM": f"{avg_ssim}",
        "AVG MSE": f"{avg_mse}",
        "AVG VMAF": f"{avg_vmaf}",
        "Cost": f"{cost}",
        'Total transfer size': f"{total_transfer_size}MB",
        '360PI': f"{metric_360PI}",
        'GC Score': f"{gc_score}"
    }

    return misc_dict


def encode_display_video(settings):
    """
    Encode the generated sequence of video frames

    Parameters
    ----------
    settings: dict
            system configuration information
    Returns
    -------
        None
    """
    # encoding the benchmark video stream
    ffmpeg_settings = settings.ffmpeg_settings
    encoding_params = settings.encoding_params

    if not osp.exists(settings.benchmark_video_uri):
        os.chdir(settings.benchmark_img_path)
        cmd = f"{ffmpeg_settings['ffmpeg_path']} " \
              f"-r {encoding_params['video_fps']} " \
              f"-start_number 0 " \
              f"-i %d.png " \
              f"-threads {ffmpeg_settings['thread']} " \
              f"-preset {encoding_params['preset']} " \
              f"-c:v {encoding_params['encoder']} " \
              f"-g {encoding_params['gop']} " \
              f"-bf {encoding_params['bf']} " \
              f"-qp {encoding_params['qp_list'][0]} " \
              f"-y benchmark.mp4 " \
              f"-loglevel {ffmpeg_settings['loglevel']}"
        settings.logger.debug(cmd)
        os.system(cmd)

    # encoding the approach video stream
    os.chdir(settings.result_img_path)
    cmd = f"{ffmpeg_settings['ffmpeg_path']} " \
          f"-r {encoding_params['video_fps']} " \
          f"-start_number 0 " \
          f"-i %d.png " \
          f"-threads {ffmpeg_settings['thread']} " \
          f"-preset {encoding_params['preset']} " \
          f"-c:v {encoding_params['encoder']} " \
          f"-g {encoding_params['gop']} " \
          f"-bf {encoding_params['bf']} " \
          f"-qp {encoding_params['qp_list'][0]} " \
          f"-y output.mp4 " \
          f"-loglevel {ffmpeg_settings['loglevel']}"
    settings.logger.debug(cmd)
    os.system(cmd)


def get_interpolation(inter_mode):
    """
    Gets the interpolation mode for cv2

    Parameters
    ----------
    inter_mode: str
        interpolation method in cv2

    Returns
    -------
    inter_order:
        the corresponding interpolation mode in cv2
    """

    if inter_mode == 'bilinear':
        inter_order = cv2.INTER_LINEAR
    elif inter_mode == 'nearest':
        inter_order = cv2.INTER_NEAREST
    elif inter_mode == 'cubic':
        inter_order = cv2.INTER_CUBIC
    elif inter_mode == 'area':
        inter_order = cv2.INTER_AREA
    elif inter_mode == 'lanczos4':
        inter_order = cv2.INTER_LANCZOS4
    else:
        raise NotImplementedError('unknown mode')

    return inter_order


def evaluate_misc(settings, arrival_list, video_size):
    """
    Calculating remaining evaluation indicators

    Parameters
    ----------
    settings: dict
        system configuration information
    arrival_list: list
        the calculated available tile chunks list, before the current timestamp
    video_size: dict
        the video size after video preprocessing

    Returns
    -------
    misc_dict: dict
        evaluation result with required format
    """

    total_size = 0
    max_bandwidth = 0

    for chunk_idx in range(len(arrival_list)):
        chunk_size = arrival_list[chunk_idx]['chunk_size']
        if max_bandwidth < chunk_size / settings.video_info['chunk_duration']:
            max_bandwidth = chunk_size / settings.video_info['chunk_duration']
        total_size += chunk_size

    # calculate average psnr and ssim
    avg_psnr = round(np.average(settings.psnr), 3)
    avg_ssim = round(np.average(settings.ssim), 3)
    avg_mse = round(np.average(settings.mse), 3)

    gc_score = calculate_gc_score(settings, total_size, video_size)

    # calculate average vmaf
    avg_vmaf = calculate_vmaf(settings.benchmark_img_path, settings.result_img_path)

    # calculate 360PI metric
    metric_360PI, cost = calculate_metric_360PI(settings, total_size, video_size, avg_vmaf)

    # write results into JSON file
    misc_dict = write_dict(settings, max_bandwidth, total_size, metric_360PI, cost, avg_psnr, avg_ssim, avg_mse, avg_vmaf, gc_score)

    return [misc_dict]


def calculate_metric_360PI(settings, total_bw, video_size, vmaf):
    """
    Calculate the final grand challenge score

    Parameters
    ----------
    settings: dict
        system configuration information
    total_bw: int
        the calculated bandwidth usage of different approaches
    video_size:
        the video size of preprocessed video

    Returns
    -------
    metirc_360PI: float
        the calculated final metric of different approaches
    """

    # calculate the storage
    total_storage = 0
    for tile_id in video_size.keys():
        total_storage += video_size[tile_id]['video_size']
    total_storage = round(total_storage / 1000 / 1000 / 1000, 6)  # GB

    # calculate the bandwidth
    total_bw = round(total_bw / 1000 / 1000 / 1000, 6)  # GB

    # calculate the computation
    if settings.opt['approach_type'] == 'on_demand':
        total_calc = 0
    elif settings.opt['approach_type'] == 'transcoding':
        total_calc = settings.video_info['duration']    # (s)
        total_storage = 0
    else:
        raise ValueError("error when read the approach mode!")

    # calculate the total cost
    w_1 = settings.gc_metrics['gc_w1']
    w_2 = settings.gc_metrics['gc_w2']
    w_3 = settings.gc_metrics['gc_w3']
    cost = w_1*total_bw + w_2*total_storage + w_3*total_calc

    # calculate the parameters of original video
    video_duration = settings.video_info['duration']
    cost_ori, vmaf_ori = calc_ori_video_para(settings.ori_video_uri, w_1, w_2, w_3, video_duration)            # fixme, the ori_video_ori should be a parameter

    # calculate the defined metric
    metric_360PI = calculate_distance(settings, cost, vmaf, cost_ori, vmaf_ori)

    return metric_360PI, [cost]


def calculate_vmaf(benchmark_img_path, result_img_path):
    """
    Parameters
    ----------
    benchmark_img_path
    result_img_path

    Returns
    -------
    The calculated VMAF value.
    """
    command = [
        'ffmpeg',
        '-i', result_img_path+"/%d.png",
        '-i', benchmark_img_path+"/%d.png",
        '-filter_complex',
        'libvmaf=model=version=vmaf_4k_v0.6.1:log_path=erp.log',
        '-f', 'null',
        '-'
    ]

    # execute the ffmpeg command and get the output result.
    result = subprocess.run(command, capture_output=True, text=True)

    # get the vmaf Score
    for line in result.stderr.split('\n'):
        if 'VMAF score' in line:
            vmaf_score = float(line.split(':')[1].strip())
            return vmaf_score

    return None


def calculate_distance(settings, cost, vmaf, cost_ori, vmaf_ori):
    """
    Parameters
    ----------
    settings:
    cost: the calculated cost of current approach
    vmaf: the calculated vmaf of current approach
    cost_ori: the calculated cost of source video
    vmaf_ori: the calculated vmaf of source video

    Returns
    -------
    The calculated distance between the point (cost, point) to the ground truth line.
    """
    trans_para = settings.system_opt['metric']['trans_para'] * 1000

    distance = abs(trans_para * cost - vmaf + (vmaf_ori - trans_para * cost_ori)) / np.sqrt(trans_para ** 2 + 1)

    # determine whether the dot is above or below the ground truth line
    vmaf_line = trans_para * (cost - cost_ori) + vmaf_ori
    if vmaf < vmaf_line:
        distance = - distance

    return distance


def calc_ori_video_para(ori_video_uri, w_1, w_2, w_3, video_duration):
    """
    Parameters
    ----------
    ori_video_uri: the uri of source video
    w_1: the weight parameter for calculating bandwidth cost
    w_2: the weight parameter for calculating storage cost
    w_3: the weight parameter for calculating computation cost
    video_duration: the video duration of source video

    Returns
    -------
    The calculated cost and vmaf values of source video, as the upper bound
    """

    vmaf_ori = 100
    video_size = get_video_size(ori_video_uri)
    video_storage = round(video_size / 1000 / 1000 / 1000, 6)              # GB
    video_bw = round(video_size / 1000 / 1000 / 1000, 6)                   # GB
    cost_ori = w_1 * video_bw + w_2 * video_storage + w_3 * video_duration

    return cost_ori, vmaf_ori

def calculate_gc_score(settings, total_bw, video_size):
    """
    Calculate the final grand challenge score

    Parameters
    ----------
    settings: dict
        system configuration information
    total_bw: int
        the calculated bandwidth usage of different approaches
    video_size:
        the video size of preprocessed video

    Returns
    -------
    gc_score: float
        the calculated final grand challenge score of different approaches
    """

    total_storage = 0

    for tile_id in video_size.keys():
        total_storage += video_size[tile_id]['video_size']

    total_storage = round(total_storage / 1000 / 1000 / 1000, 6)  # GB
    total_bw = round(total_bw / 1000 / 1000 / 1000, 6)  # GB

    if settings.opt['approach_type'] == 'on_demand':
        total_calc = 0
    elif settings.opt['approach_type'] == 'transcoding':
        total_calc = settings.video_info['duration']    # (s)
        total_storage = 0
    else:
        raise ValueError("error when read the approach mode!")

    mse = round(np.average(settings.mse), 3)
    w_1 = settings.gc_metrics['gc_w1']
    w_2 = settings.gc_metrics['gc_w2']
    w_3 = settings.gc_metrics['gc_w3']
    alpha = settings.gc_metrics['gc_alpha']
    beta = settings.gc_metrics['gc_beta']

    gc_score = 1 / (alpha * mse + beta * (w_1*total_bw + w_2*total_storage + w_3*total_calc))

    return gc_score