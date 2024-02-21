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

import os.path as osp
import os
import shutil
from e3po.utils import get_logger


class BaseEvaluation:
    """
    Base Evaluation.

    Parameters
    ----------
    opt : dict
        Configurations.

    Notes
    -----
    Almost all class public attributes are directly read or indirectly processed from the yaml configuration file.
    Their specific meanings can be found in 'docs/Config.md'.
    """

    def __init__(self, opt):
        self.opt = opt
        self.logger = get_logger()
        self.system_opt = opt['e3po_settings']
        self.test_group = opt['test_group']
        self.ori_video_name = self.system_opt['video']['origin']['video_name']
        self.ori_video_dir = self.system_opt['video']['origin']['video_dir']
        self.ori_video_uri = osp.join(self.ori_video_dir, self.ori_video_name)
        self.approach_folder_name = self.opt['approach_name']
        self.approach_name = self.opt['approach_name']
        self.approach_mode = self.opt['approach_type']
        self.approach_module_name = f"e3po.approaches.{self.approach_folder_name}.{self.approach_name}_approach"
        self.pre_download_duration = int(
            self.system_opt['network_trace']['pre_download_duration'] * 1000
        )
        self.base_ts = None
        self.last_img_index = -1

        # ffmpeg information
        self.ffmpeg_settings = self.system_opt['ffmpeg']
        if not self.ffmpeg_settings['ffmpeg_path']:
            assert shutil.which('ffmpeg'), '[error] ffmpeg doesn\'t exist'
            self.ffmpeg_settings['ffmpeg_path'] = shutil.which('ffmpeg')
        else:
            assert os.path.exists(self.ffmpeg_settings['ffmpeg_path']), \
                f'[error] {self.ffmpeg_settings["ffmpeg_path"]} doesn\'t exist'

        # evaluation metrics
        self.psnr_flag = self.system_opt['metric']['psnr_flag']
        self.ssim_flag = self.system_opt['metric']['ssim_flag']
        self.save_benchmark_flag = self.system_opt['metric']['save_benchmark_flag']
        self.benchmark_img_path = osp.join(
            self.opt['project_path'],
            'result',
            self.opt['test_group'],
            self.ori_video_name.split('.')[0],
            'benchmark'
        )
        if self.save_benchmark_flag:
            os.makedirs(self.benchmark_img_path, exist_ok=True)
        self.pipe = None
        self.benchmark_video_uri = osp.join(
            self.benchmark_img_path,
            'benchmark.mp4'
        )

        self.psnr_ssim_frequency = self.system_opt['metric']['psnr_ssim_frequency']
        self.use_gpu = self.system_opt['metric']['use_gpu']
        self.video_dir = self.system_opt['video']['origin']['video_dir']

        # background stream
        self.result_img_path = osp.join(
            opt['project_path'],
            'result',
            opt['test_group'],
            self.ori_video_name.split('.')[0],
            self.approach_folder_name,
            'output_frames'
        )

        if os.path.exists(self.result_img_path):
            shutil.rmtree(self.result_img_path)
        os.makedirs(self.result_img_path, exist_ok=True)

        self.frame_extractor = {}       # storing cv2.VideoCapture class objects
        self.frame_idx = {}             # record the sequence number of the current extracted frame
        self.last_frame = {}            # record the last extracted frame for each video.

        # data indicators to be counted
        self.psnr = []
        self.ssim = []
        self.mse = []

        # evaluation result path
        self.evaluation_json_path = osp.join(
            opt['project_path'],
            'result',
            opt['test_group'],
            self.ori_video_name.split('.')[0],
            self.approach_folder_name,
            'evaluation.json'
        )
        try:
            if osp.exists(self.evaluation_json_path):
                os.remove(self.evaluation_json_path)
        except Exception as e:
            print(f"An error occurred while deleting the json file {self.evaluation_json_path}: {e}")

        # e3po metrics
        self.gc_metrics = {
            'gc_w1': self.system_opt['metric']['gc_w1'],
            'gc_w2': self.system_opt['metric']['gc_w2'],
            'gc_w3': self.system_opt['metric']['gc_w3'],
            'gc_alpha': self.system_opt['metric']['gc_alpha'],
            'gc_beta': self.system_opt['metric']['gc_beta'],
        }
        self.dst_video_folder = osp.join(
            self.ori_video_dir,
            self.test_group,
            self.ori_video_name.split('.')[0],
            self.approach_folder_name,
            'dst_video_folder'
        )

        # related parameters for all approaches
        self.video_fps = self.system_opt['video']['video_fps']
        self.decision_json_path = osp.join(
            opt['project_path'],
            'result',
            opt['test_group'],
            self.ori_video_name.split('.')[0],
            self.approach_folder_name,
            'decision.json'
        )
        self.video_json_path = osp.join(
            self.system_opt['video']['origin']['video_dir'],
            opt['test_group'],
            self.ori_video_name.split('.')[0],
            self.approach_folder_name,
            'video_size.json'
        )
        self.video_info = {
            'width': self.system_opt['video']['origin']['width'],
            'height': self.system_opt['video']['origin']['height'],
            'projection': self.system_opt['video']['origin']['projection_mode'],
            'duration': self.system_opt['video']['video_duration'],
            'chunk_duration': self.system_opt['video']['chunk_duration'],
            'video_fps': self.system_opt['video']['video_fps']
        }
        self.network_stats = [{
            'rtt': self.system_opt['network_trace']['rtt'],
            'bandwidth': self.system_opt['network_trace']['bandwidth'],
            'rendering_delay': self.system_opt['network_trace']['rendering_delay'],
            'curr_ts': -1
        }]
        self.curr_fov = {
            'curr_motion': None,
            'range_fov': self.system_opt['metric']['range_fov'],
            'fov_resolution': self.system_opt['metric']['fov_resolution']
        }
        self.encoding_params = self.system_opt['encoding_params']
        self.chunk_frame_num = self.video_fps * self.video_info['chunk_duration']


    def set_base_ts(self, base_ts):
        """Set starting timestamp of client motion trace."""
        self.base_ts = base_ts
