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

import logging
from tqdm import tqdm

logger_names = []


def get_logger(logger_name='e3po', console_log_level=logging.INFO, file_log_level=logging.DEBUG, log_file=None):
    """
    Get the logger.
    Initialize when the target logger has not been initialized, otherwise return the initialized logger.
    Add a TqdmStreamHandler by default, and when specifying logfile, also add a FileHandler.

    Parameters
    ----------
    logger_name :str
        root logger name.
    console_log_level : int
        The log level displayed on the command line.
    file_log_level : int
        The log level of log file records.
    log_file : str
        The log filename. If specified, a FileHandler will be added to the root logger.

    Returns
    -------
    logging.Logger:
        The logger.

    Examples
    --------
    >> get_logger(log_file='test.log')

    >> logger = get_logger()

    >> logger.info('info')

    2023-07-05 18:00:40,460 INFO: info

    >> logger.debug('debug')
    """
    logger = logging.getLogger(logger_name)
    if logger_name in logger_names:
        return logger

    format_str = "%(asctime)s %(levelname)s: %(message)s"
    tqdm_handler = TqdmLoggingHandler(console_log_level)
    tqdm_handler.setFormatter(logging.Formatter(format_str))
    logger.addHandler(tqdm_handler)

    logger.propagate = False
    if log_file is not None:
        file_handler = logging.FileHandler(log_file, 'w', delay=True)
        file_handler.setFormatter(logging.Formatter(format_str))
        file_handler.setLevel(file_log_level)
        logger.addHandler(file_handler)

    logger.setLevel(min(console_log_level, file_log_level))
    logger_names.append(logger_name)
    return logger


# From https://stackoverflow.com/questions/38543506/change-logging-print-function-to-tqdm-write-so-logging-doesnt-interfere-wit/38739634#38739634
class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)
