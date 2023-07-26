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
from e3po.decision import build_decision
from e3po.utils import get_opt, get_logger, pre_processing_client_log, write_json


def make_decision(opt):
    decision = build_decision(opt)
    decision_result = []
    if not decision:
        return decision_result
    motion_record = pre_processing_client_log(opt)
    motion_ts_bar = tqdm(list(motion_record.keys()), leave=False)
    for motion_ts in motion_ts_bar:
        decision.push_hw(motion_ts, motion_record[motion_ts])
        decision_result += decision.decision()
    motion_ts_bar.close()
    return decision_result


if __name__ == '__main__':
    opt = get_opt()
    get_logger().info('[make decision] start')
    decision_result = make_decision(opt)
    result_path = osp.join(opt['project_path'], 'result', opt['test_group'], opt['method_name'], 'decision.json')
    write_json(decision_result, result_path)
    get_logger().info(f'[write json] path: {result_path}')
    get_logger().info('[make decision] end')
