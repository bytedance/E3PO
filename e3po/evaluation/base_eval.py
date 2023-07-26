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
import cv2
import os
from copy import deepcopy
import numpy as np
import shutil
import subprocess as sub

from e3po.utils import get_logger
from e3po.projection import build_projection


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
        self.test_group = opt['test_group']
        self.method_name = opt['method_name']
        self.logger = get_logger()
        self.projection = build_projection(opt)
        self.base_ts = None  # Starting timestamp of client motion trace.
        self.pre_download_duration = opt['method_settings']['pre_download_duration'] * 1000
        self.last_img_index = -1

        self.ffmpeg = self.opt['ffmpeg']['ffmpeg_path']
        if not self.ffmpeg:
            assert shutil.which('ffmpeg'), '[error] ffmpeg doesn\'t exist'
            self.ffmpeg = shutil.which('ffmpeg')
        else:
            assert os.path.exists(self.ffmpeg), f'[error] {self.ffmpeg} doesn\'t exist'
        self.logger.info(f'[ffmpeg path] {self.ffmpeg}')
        self.ffmpeg_loglevel = self.opt['ffmpeg']['loglevel']
        self.psnr_flag = opt['metric']['psnr_flag']
        self.ssim_flag = opt['metric']['ssim_flag']
        self.save_ground_truth_flag = opt['metric']['save_ground_truth_flag']
        self.save_result_img_flag = opt['metric']['save_result_img_flag']
        self.ground_truth_img_path = osp.join(self.opt['project_path'], 'result', self.opt['test_group'],
                                              'ground_truth')
        if self.save_ground_truth_flag:
            os.makedirs(self.ground_truth_img_path, exist_ok=True)
        self.pipe = None
        if self.psnr_flag or self.ssim_flag:
            self.psnr_ssim_frequency = opt['metric']['psnr_ssim_frequency']
            self.use_gpu = opt['metric']['use_gpu']
            self.fov_resolution = self.opt['metric']['fov_resolution']
            self.video_dir = opt['video']['origin']['video_dir']
            self.projection_mode = opt['video']['converted']['projection_mode']
            self.quality_list = opt['video']['converted']['quality_list']
            self.background_flag = opt['method_settings']['background']['background_flag']
            if self.background_flag:
                self.background_projection_mode = opt['method_settings']['background']['projection_mode']
            _opt = deepcopy(opt)
            _opt['projection_type'] = opt['video']['origin']['projection_type']
            _opt['method_settings']['background']['background_flag'] = False
            self.origin_projection = build_projection(_opt)

            self.result_img_path = osp.join(opt['project_path'], 'result', opt['test_group'], opt['method_name'],
                                            'frames_w')
            if not self.background_flag:
                self.result_img_path += 'o'
            if os.path.exists(self.result_img_path):
                shutil.rmtree(self.result_img_path)
            os.makedirs(self.result_img_path, exist_ok=True)

            self.frame_extractor = {}  # Frame extractor dictionary, storing cv2.VideoCapture class objects for different videos.
            self.frame_idx = {}  # Frame index dictionary, record the sequence number of the current extracted frame for each video.
            self.last_frame = {}  # Record the last extracted frame for each video.
            self._init_frame_extractor()
            self.img2video('start', self.fov_resolution)

        # Data indicators to be counted
        self.psnr = []
        self.ssim = []
        self.out_percent = []
        self.write_dict = {}

    def set_base_ts(self, base_ts):
        """
        Set starting timestamp of client motion trace.

        Parameters
        ----------
        base_ts : int
            Starting timestamp of client motion trace.
        """
        self.base_ts = base_ts

    def evaluate_motion(self, fov_ts, fov_direction):
        """
        Evaluate a motion.

        Parameters
        ----------
        fov_ts : int
            FoV motion timestamp.
        fov_direction : dict
            Motion description information:
                {'yaw': yaw, 'pitch': pitch, 'scale': scale}

        Returns
        -------
        list
            Evaluation result list, which may be empty list.
        """
        pass

    def evaluate_misc(self):
        """Calculate remaining evaluation indicators"""
        self.write_dict['AVG psnr'] = round(np.average(self.psnr), 3)
        self.write_dict['AVG ssim'] = round(np.average(self.ssim), 3)
        self.write_dict['AVG out_percent'] = round(np.average(self.out_percent), 3)

    def _init_frame_extractor(self):
        """Initialize frame extractor."""
        get_logger().info('[initialize frame extractor] start')

        video_path = osp.join(self.video_dir, self.opt['video']['origin']['video_name'])
        self.frame_extractor['ori_'] = cv2.VideoCapture()
        self.frame_idx['ori_'] = -1
        assert self.frame_extractor['ori_'].open(video_path), f"[error] Can't read video[{video_path}]"

        video_path = osp.join(self.video_dir, self.test_group, self.opt['video']['origin']['video_name'].split('.')[0],
                              self.method_name, 'converted_{}.mp4')
        for quality in self.quality_list:
            self.frame_extractor[f"{self.projection_mode}_{quality}"] = cv2.VideoCapture()
            self.frame_idx[f"{self.projection_mode}_{quality}"] = -1
            assert self.frame_extractor[f"{self.projection_mode}_{quality}"].open(
                video_path.format(quality)), f"[error] Can't read video[{video_path.format(quality)}]"

        if self.background_flag:
            video_path = osp.join(self.video_dir, self.test_group,
                                  self.opt['video']['origin']['video_name'].split('.')[0], self.method_name,
                                  'background.mp4')
            self.frame_extractor["background_"] = cv2.VideoCapture()
            self.frame_idx["background_"] = -1
            assert self.frame_extractor["background_"].open(video_path), f"[error] Can't read video[{video_path}]"

        get_logger().info('[initialize frame extractor] end')

    def push_pre_downloaded_frame(self, fov_ts, fov_direction):
        """
        Push a pre-downloaded frame into the ffmpeg pipeline.

        Parameters
        ----------
        fov_ts : int
            FoV motion timestamp.
        fov_direction : dict
            Motion description information:
                {'yaw': yaw, 'pitch': pitch, 'scale': scale}
        """
        if fov_ts > self.base_ts + self.pre_download_duration:
            return

        # Evaluate only once per frame.
        img_index = int((fov_ts - self.base_ts) * self.video_fps // 1000.0)
        if self.last_img_index == img_index:
            return
        self.last_img_index = img_index
        ground_truth_img = osp.join(self.ground_truth_img_path, f"{img_index}.png")
        if not self.save_ground_truth_flag or not os.path.exists(ground_truth_img):
            self.logger.debug(f'[evaluation] start cal fov_uv')
            fov_ypr = [float(fov_direction['yaw']), float(fov_direction['pitch']), 0]
            fov_uv = self.projection.sphere_to_uv(fov_ypr, self.fov_resolution)
            self.logger.debug(f'[evaluation] end cal fov_uv')
        else:
            fov_uv = None

        self.logger.debug(f'[evaluation] start get ground truth img')
        ground_truth = self._get_ground_truth_img(img_index, fov_uv, fov_direction)
        self.logger.debug(f'[evaluation] end get ground truth img')

        self.logger.debug(f'[evaluation] start push pre-downloaded frame')
        self.img2video('encode', ground_truth)
        self.logger.debug(f'[evaluation] end push pre-downloaded frame')
        return

    def _get_ground_truth_img(self, img_index, uv, fov_direction):
        """
        Generate or read the specified ground truth image.

        Parameters
        ----------
        img_index : int
            Frame index.
        uv : numpy.ndarray
            The spatial polar coordinates of the sampling points based on given FoV direction and resolution.
        fov_direction : dict
            FoV direction:
                {'yaw': yaw, 'pitch': pitch, 'scale': scale}

        Returns
        -------
        numpy.ndarray
           Ground truth image.

        """
        ground_truth_img = osp.join(self.ground_truth_img_path, f"{img_index}.png")
        if not self.save_ground_truth_flag or not os.path.exists(ground_truth_img):
            server_img = self.extract_frame('ori', '', img_index)
            fov_tile_list, fov_pixel_tile_list = self.origin_projection.sphere_to_tile(fov_direction)
            result = self.origin_projection.get_fov(server_img, self.opt['video']['origin']['width'],
                                                    self.opt['video']['origin']['height'], uv, fov_tile_list)
        else:
            result = np.array(cv2.imread(ground_truth_img))
        if self.save_ground_truth_flag and not os.path.exists(ground_truth_img):
            cv2.imwrite(ground_truth_img, result, [cv2.IMWRITE_JPEG_QUALITY, 100])
        return result

    def extract_frame(self, projection_mode, quality, target_idx):
        """
        Extract the video frame of the given index.

        Parameters
        ----------
        projection_mode : str
            Projection mode.
        quality : str or int
            Video quality.
        target_idx : int
            Index of the frame to extract.

        Returns
        -------
        numpy.ndarray
           Frame content.
        """
        ret = False
        while self.frame_idx[f"{projection_mode}_{quality}"] < target_idx - 1:
            ret = self.frame_extractor[f"{projection_mode}_{quality}"].grab()
            if not ret:
                break
            self.frame_idx[f"{projection_mode}_{quality}"] += 1
        if self.frame_idx[f"{projection_mode}_{quality}"] == target_idx - 1:
            ret, frame = self.frame_extractor[f"{projection_mode}_{quality}"].read()
        if ret:
            self.frame_idx[f"{projection_mode}_{quality}"] += 1
            frame = np.array(frame)
            self.last_frame[f"{projection_mode}_{quality}"] = frame
        else:
            frame = self.last_frame[f"{projection_mode}_{quality}"]
        return frame

    def img2video(self, cmd, data=None):
        """
        Convert FOV images into videos

        Parameters
        ----------
        cmd : str
            cmd should be in ['start', 'encode', 'end'].
        data : list or numpy.ndarray or None
            Different instructions require different data


        Examples
        --------
        >> self.img2video('start', self.fov_resolution)

        >> self.img2video('encode', frame)

        >> self.img2video('end')
        """
        if (self.psnr_flag or self.ssim_flag) and self.psnr_ssim_frequency == 1:
            assert cmd in ['start', 'encode', 'end'], \
                f"[error] Unrecognized cmd '{cmd}', it should be in ['start', 'encode', 'end']!"
            if cmd == 'start':
                self.logger.info("[evaluation] init video encoder")
                cmd = [self.ffmpeg, '-y', '-an',
                       '-loglevel', self.ffmpeg_loglevel,
                       '-r', str(self.opt['video']['video_fps']),
                       '-s', f'{data[1]}x{data[0]}',  # size of one frame
                       '-pix_fmt', 'bgr24',
                       '-f', 'rawvideo',
                       '-c:v', 'rawvideo',
                       '-i', '-',  # The input comes from a pipe
                       '-vcodec', 'libx264',
                       '-preset', 'faster',
                       '-pix_fmt', 'yuv420p',
                       '-g', '150',
                       '-bf', '0',
                       '-qp', '29',
                       f"{os.path.join(self.result_img_path, 'output.mp4')}"]
                self.logger.debug(''.join(x + ' ' for x in cmd))
                self.pipe = sub.Popen(cmd, stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE, bufsize=10 ** 9)
            elif cmd == 'encode':
                self.logger.debug("[evaluation] start push img")
                self.pipe.stdin.write(data)
                self.pipe.stdin.flush()
                self.logger.debug("[evaluation] end push img")
            elif cmd == 'end':
                self.logger.debug("[evaluation] start write video")
                self.pipe.stdin.flush()
                self.pipe.stdin.close()
                self.pipe = None
                self.logger.debug("[evaluation] end write video")
