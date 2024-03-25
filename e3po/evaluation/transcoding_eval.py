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

import importlib
from e3po.utils.registry import evaluation_registry
from .base_eval import BaseEvaluation
from e3po.utils.json import read_decision_json, read_video_json
from e3po.utils.evaluation_utilities import *
from e3po.utils import pre_processing_client_log, write_evaluation_json
from e3po.utils.psnr_ssim import calculate_psnr_ssim_mse
from e3po.utils.misc import generate_motion_clock, generate_dst_frame_uri


@evaluation_registry.register()
class TranscodingEvaluation(BaseEvaluation):
    """
    Transcoding evaluation, which is suitable for transcoding approaches.

    Parameters
    ----------
    opt : dict
        Configurations.
    """

    def __init__(self, opt):
        super(TranscodingEvaluation, self).__init__(opt)

    def make_evaluation(self):
        """
        Performing evaluation process for transcoding approaches, and recording the evaluation results into JSON file.

        Returns
        -------
            None
        """

        evaluation_result = []
        dl_list = read_decision_json(self.decision_json_path)
        video_size = read_video_json(self.video_json_path)
        arrival_list = calc_arrival_ts(self, dl_list, video_size, self.network_stats)

        pre_downloading_duration = arrival_list[1]['tile_list'][0]['playable_ts']
        self.set_base_ts(pre_downloading_duration)
        motion_record = pre_processing_client_log(self.system_opt)
        motion_clock = generate_motion_clock(self, motion_record)

        approach = importlib.import_module(self.approach_module_name)
        user_data = None
        for motion_ts in motion_clock:
            curr_ts = motion_ts + pre_downloading_duration
            frame_idx = int(motion_ts * self.video_fps // 1000.0)
            if self.last_img_index == frame_idx:
                continue
            self.last_img_index = frame_idx

            current_display_chunks = get_curr_display_chunks(arrival_list, curr_ts)
            curr_display_frames = get_curr_display_frames(self, current_display_chunks, curr_ts, frame_idx)
            dst_video_frame_uri = generate_dst_frame_uri(self.result_img_path, frame_idx)
            curr_fov = update_curr_fov(self.curr_fov, motion_record[motion_ts])
            user_data = approach.generate_display_result(curr_display_frames, current_display_chunks, curr_fov, dst_video_frame_uri, frame_idx, video_size, user_data, self.video_info)
            dst_benchmark_frame_uri = generate_benchmark_result(self, curr_fov, frame_idx)
            psnr, ssim, mse = calculate_psnr_ssim_mse(dst_benchmark_frame_uri, dst_video_frame_uri, self.use_gpu, self.psnr_flag, self.ssim_flag)
            self.psnr.append(psnr)
            self.ssim.append(ssim)
            self.mse.append(mse)
            evaluation_result.append([{'frame_idx': frame_idx, 'psnr': psnr, 'ssim': ssim, 'mse': mse, 'yaw': curr_fov['curr_motion']['yaw'], 'pitch': curr_fov['curr_motion']['pitch'], 'motion_ts': motion_ts}])
        encode_display_video(self)
        evaluation_result.append(evaluate_misc(self, arrival_list, video_size))
        write_evaluation_json(evaluation_result, self.evaluation_json_path)

        self.logger.info(f"transcoding evaluation end.")