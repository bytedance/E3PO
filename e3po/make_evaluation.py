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
from tqdm import tqdm

import add_e3po_to_enviroment
from e3po.evaluation import build_evaluation
from e3po.utils import get_opt, get_logger, pre_processing_client_log, write_json


def make_evaluation(opt):
    evaluation = build_evaluation(opt)
    evaluation_result = []
    if not evaluation:
        return evaluation_result
    motion_record = pre_processing_client_log(opt)
    client_record_ts = list(motion_record.keys())
    base_ts = client_record_ts[0]
    pre_downloaded_time = opt['method_settings']['pre_download_duration'] * 1000
    evaluation.set_base_ts(base_ts)

    client_record_ts = [i for i in client_record_ts if i - base_ts < opt['video']['video_duration'] * 1000]
    motion_ts_bar = tqdm(client_record_ts, leave=False)
    for motion_ts in motion_ts_bar:
        motion_ts_bar.set_description(f"[evaluation] ts={motion_ts}")
        if 2000 <= motion_ts < 2000 + pre_downloaded_time:
            evaluation.push_pre_downloaded_frame(motion_ts, motion_record[motion_ts])
        elif 2000 + pre_downloaded_time <= motion_ts:
            evaluation_result += evaluation.evaluate_motion(motion_ts, motion_record[motion_ts])
    motion_ts_bar.close()
    evaluation_result += evaluation.evaluate_misc()
    evaluation.img2video('end')
    return evaluation_result


if __name__ == '__main__':
    opt = get_opt()
    get_logger().info('[evaluation] start')
    evaluation_result = make_evaluation(opt)
    if opt['method_settings']['background']['background_flag']:
        result_path = osp.join(opt['project_path'], 'result', opt['test_group'], opt['video']['origin']['video_name'].split('.')[0],
                               opt['method_name'], 'evaluation_w.json')
    else:
        result_path = osp.join(opt['project_path'], 'result', opt['test_group'], opt['video']['origin']['video_name'].split('.')[0],
                               opt['method_name'], 'evaluation_wo.json')
    write_json(evaluation_result, result_path)
    get_logger().info(f'[write json] path: {result_path}')
    get_logger().info('[evaluation] end')
