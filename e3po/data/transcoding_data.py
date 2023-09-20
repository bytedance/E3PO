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


from e3po.utils.registry import data_registry
from .base_data import BaseData

@data_registry.register()
class TranscodingData(BaseData):
    """
    TranscodingData data.

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
        """
        Each approach should config some initial parameters in this function.

        Parameters
        ----------
        opt : dict
            Configurations.
        """
        super(TranscodingData, self).__init__(opt)

    def process_video(self):
        self._convert_ori_video()
        self._generate_viewport()
        self._generate_h264()
        self._get_viewport_size()
        self._del_intermediate_file(self.work_folder, ['converted'], ['.json'])

    def _convert_ori_video(self):
        """
        This function implements the conversion of original video, with some given
        transcoding parameters.
        """
        pass

    def _generate_viewport(self):
        """
        This function generates the viewport content that would be transmitted to the
        client, which should be implemented for each approach.
        """
        pass

    def _generate_h264(self):
        """
        This function simulates the process of encoding the generated viewport content.
        """
        pass

    def _get_viewport_size(self):
        """
        This function get the file size of encoded viewport content.
        """
        pass
