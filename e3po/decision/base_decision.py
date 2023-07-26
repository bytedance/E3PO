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

    def push_hw(self, motion_ts, motion):
        """
        Push input data into the queue self.hw.

        Parameters
        ----------
        motion_ts : int
            Motion timestamp.
        motion : dict
            Motion description information:
                {'yaw': yaw, 'pitch': pitch, 'scale': scale}
        """
        pass

    def decision(self):
        """
        Determine whether to make a decision based on historical information and return decision results

        Returns
        -------
        list
            Decision result list, which may be empty list.
        """
        pass
