import os.path as osp
import sys

e3po_path = osp.sep.join(osp.dirname(__file__).split(osp.sep)[:-1])
if e3po_path not in sys.path:
    sys.path.insert(0, e3po_path)
