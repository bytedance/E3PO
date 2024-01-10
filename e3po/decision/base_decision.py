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

from e3po.utils import get_logger
import os.path as osp
import os


class BaseDecision:
    """
    Base decision.

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
        self.test_group = opt['test_group']
        self.system_opt = opt['e3po_settings']

        self.ori_video_dir = self.system_opt['video']['origin']['video_dir']
        self.ori_video_name = self.system_opt['video']['origin']['video_name']
        self.approach_folder_name = self.opt['approach_name']
        self.approach_name = self.opt['approach_name']
        self.approach_module_name = f"e3po.approaches.{self.approach_folder_name}.{self.approach_name}_approach"

        self.source_folder = osp.join(
            self.ori_video_dir,
            self.test_group,
            self.ori_video_name.split('.')[0],
            self.approach_folder_name
        )
        self.decision_json_uri = osp.join(
            opt['project_path'],
            'result',
            opt['test_group'],
            self.ori_video_name.split('.')[0],
            self.approach_folder_name,
            'decision.json'
        )
        try:
            if osp.exists(self.decision_json_uri):
                os.remove(self.decision_json_uri)
        except Exception as e:
            print(f"An error occurred while deleting the json file {self.decision_json_uri}: {e}")

        self.ori_video_uri = osp.join(self.ori_video_dir, self.ori_video_name)

