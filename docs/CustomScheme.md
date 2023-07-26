# Custom Scheme
We have provided some reference solutions, each of which includes: 
data processing module, 
projection mapping module, 
decision module and evaluation module.
Below, we will first introduce how to use the register to call various customized modules, 
and then provide a simple example to illustrate which parts of the customization solution need to be implemented.

## How to use register
Each module is dynamically instantiated through a register.
We define registers for them in [utils/register.py](../e3po/utils/registry.py):
```
data_registry = Registry('data_registry')
decision_registry = Registry('decision_registry')
evaluation_registry = Registry('evaluation_registry')
projection_registry = Registry('projection_registry')
```
Taking the tile based solution's data module as an example,
You need to use a Python decorator to register your class:
```
from e3po.utils.registry import data_registry

@data_registry.register()
class TileBasedData(BaseData):
    def __init__(self, opt):
        super(TileBasedData, self).__init__(opt)
        ...
```
In addition, you also need to modify the end of the file name corresponding to this class to `_data.py`, 
so that the file can be automatically import into the program by [data/__init__.py](../e3po/data/__init__.py).
Then you can declare class objects in the following ways:
```
from e3po.utils import get_opt
from e3po.utils.registry import data_registry

opt = get_opt() # read config file
data = data_registry['TileBasedData'](opt)
```
In fact, You only need to specify the class name in the configuration file:
```
data_type: TileBasedData
decision_type: TileBasedDecision
projection_type: ErpProjection
evaluation_type: TileBasedEvaluation
```
Then declare the class object through the `build_[module name]` function in `[module name]/__init__.py`:
```
from e3po.utils import get_opt
from e3po.data import build_data

opt = get_opt()
data = build_data(opt)
```

## How to implement your  method
We provide two types of solutions: on-demand solution and transcoding solution.
Here are two examples to introduce how to implement your methods based on these two solutions.

### On-demand Solution
We use Custom-EAC solution as an example to illustrate how to implement your on-demand solution.
This requires the implementation of data module, projection module, decision module, and evaluation module. 
The following will introduce these four modules in sequence.

1. Data module<br>
    Your class needs to inherit from `data.tile_based_data.TileBasedData` and override the corresponding functions within it.
    More details can be viewed in file [data/tile_based_data.py](../e3po/data/tile_based_data.py),
    here is a brief introduction to `TileBasedData`:
    ```
    @data_registry.register()
    class TileBasedData(BaseData):
       def __init__(self, opt):
           ...
       def process_video(self):
       # prepare_data.py will call this function. 
           self._convert_ori_video() # Defined in BaseData, used to convert the original video format.
           self._generate_chunk()
           self._generate_tile()
           self._get_tile_size()
           self._del_intermediate_file(['converted', 'background.mp4'], ['.json']) # Defined in BaseData, used to delete intermediate files.
       def _generate_chunk(self):
       # Divide the video into chunks according to the description in the configuration file.
           ...
       def _generate_tile(self):
       # Divide the video chunks into tiles according to the description in the configuration file.
           ...
       def _get_tile_size(self):
       # Read the file size of all tiles and write them to the video_size.json in a fixed format.
           ...     
       def get_size(self, *args):
       # Obtain the corresponding video tile size based on the given parameters.
           ...
       def get_background_size(self, *args):
       # Obtain the corresponding background video file size based on the given parameters.
           ...
    ```
    Custom-EAC solution uses different tile segmentation methods, 
    so it is necessary to rewrite some functions in `TileBasedData`.
    Function details can be viewed in file [data/custom_eac_data.py](../e3po/data/custom_eac_data.py):
    ```
    @data_registry.register()
    class CustomEacData(TileBasedData):
        def _convert_ori_video(self):
            ...
        def _generate_tile(self):
            ...
        def _get_tile_size(self):
            ...
    ```

2. Projection module<br>
    Your class needs to inherit from `projection.tile_projection.TileProjection` and override the corresponding functions within it.
    More details can be viewed in file [projection/tile_projection.py](../e3po/projection/tile_projection.py),
    here is a brief introduction to `TileProjection`:
    ```
    @projection_registry.register()
    class TileProjection(BaseProjection):
        def __init__(self, opt):
            ...
        def sphere_to_tile(self, fov_ypr)::
        # Sample the fov range corresponding to the spherical viewpoint coordinates, map the sampling points to the tiles they belong to, 
        # and return the tile union of all sampling points and the tile number corresponding to each pixel point.
            ...
        @classmethod
        def uv_to_coor(cls, *args):
        # Convert spherical coordinates to planar coordinates.
            pass
        def _coord_to_tile(self, pixel_coord, w, h):
        # Convert plane coordinates to tile indexes.
            ...
        def get_fov(self, *args):
        # Generate FOV image.
            ...
        def _fov_result(self, fov_uv, w, h, client_tile_list, server_tile_list):
        # Sampling coordinates required for generating FOV images.
            ...
    ```
    Custom-EAC solution uses different tile segmentation methods and projection methods, 
    so it is necessary to rewrite some functions in `TileProjection`.
    Function details can be viewed in file [projection/custom_eac_projection.py](../e3po/projection/custom_eac_projection.py):
    ```
    @projection_registry.register()
    class CustomEacProjection(TileProjection):
        @classmethod
        def uv_to_coor(cls, *args):
            ...
        def _coord_to_tile(self, pixel_coord, w, h):
            ...
        def erp_to_eac(self, img, inter_mode):
        #  Due to the use of a special projection format, 
        #  this function is required to generate video frames during data preprocessing.
            ...
    ```

3. Decision module<br>
    Since this scheme does not change the decision-making method of tile type schemes, 
    there is no need to rewrite any content.
    Simply call class `decision.tile_decision.TileBasedDecision` directly is OK.
    Here is a brief introduction to `TileBasedDecision`:
    ```
    @decision_registry.register()
    class TileBasedDecision(BaseDecision):
        def __init__(self, opt):
            ...
        def push_hw(self, motion_ts, motion):
        # make_decision.py will call this function. 
            ...
        def decision(self):
        # make_decision.py will call this function. 
            ...
        def _predict_motion_tile(self):
        # Based on motion within the given historical window, predict the motion within the prediction window.
            ...
        def _tile_decision(self, predicted_record):
        # Based on the prediction results, determine the tile range to be transmitted for each chunk within the prediction window.
            ...
        def _bitrate_decision(self, tile_record):
        # For each chunk that needs to be transmitted, determine its bitrate separately.
            ...
    ```
   

4. Evaluation module<br>
    Since this scheme does not change the decision-making method of tile type schemes, 
    there is no need to rewrite any content.
    Simply call class `evaluation.tile_eval.TileBasedEvaluation` directly is OK.
    Here is a brief introduction to `TileBasedEvaluation`:
    ```
    @evaluation_registry.register()
    class TileBasedEvaluation(BaseEvaluation):
    def __init__(self, opt):
        ...
    def _decision_to_playable(self):
        # Calculate when the client can play what content and the transmission volume of each chunk based on decision information,
        # network bandwidth, RTT, decision location, and rendering delay.
        ...
    def evaluate_motion(self, fov_ts, fov_direction):
        # Evaluate a certain motion.
        ...
    def evaluate_misc(self):
        # Summative evaluation.
        ...
    def _calculate_psnr_ssim(self, fov_direction, server_tile_list, img_index):
        # Generate ground truth image and actual FOV image based on motion, and calculate PSNR and SSIM
        ...
    ```

### Transcoding Solution
We use Freedom1 solution as an example to illustrate how to implement your transcoding solution.
This requires the implementation of data module, projection module, decision module, and evaluation module. 
The following will introduce these four modules in sequence.

1. Data module<br>
    Your class needs to inherit from `data.based_data.BasedData` and override the corresponding functions within it.
    More details can be viewed in file [data/based_data.py](../e3po/data/base_data.py),
    here is a brief introduction to `BasedData`:
    ```
    class BaseData:
       def __init__(self, opt):
           ...
       def process_video(self):
       # prepare_data.py will call this function. 
           pass
       def _convert_ori_video(self):
       # Convert the original video format.
           ...
       def _del_intermediate_file(self, start_list, end_list):
       # Delete intermediate files.
           ... 
       def get_size(self, *args):
       # Obtain the corresponding video tile size based on the given parameters.
           ...
       def get_background_size(self, *args):
       # Obtain the corresponding background video file size based on the given parameters.
           ...
    ```
    Freedom1 solution need to rewrite some functions in `TileBasedData`.
    Function details can be viewed in file [data/freedom1_data.py](../e3po/data/freedom1_data.py):
    ```
    @data_registry.register()
    class CustomEacData(TileBasedData):
        def _convert_ori_video(self):
            ...
        def process_video(self):
            self._convert_ori_video()
            self._generate_vam()
            self._generate_h264()
            self._get_vam_size()
            self._del_intermediate_file(['converted'], ['.json'])
        def _generate_vam(self):
        # Generate VAM images.
            ...
        def _generate_h264(self):
        # Generate videos using VAM images and extract H264 files.
            ...
        def _get_vam_size(self):
        # Read the file size of all h264 files and write them to the video_size.json in a fixed format.
            ..
        def get_size(self, *args):
        # Obtain the corresponding h264 file size based on the given parameters.
            ...
    ```

2. Projection module<br>
    Your class needs to inherit from `projection.base_projection.BaseProjection` and override the corresponding functions within it.
    More details can be viewed in file [projection/base_projection.py](../e3po/projection/base_projection.py),
    here is a brief introduction to `BaseProjection`:
    ```
    class BaseProjection:
        def __init__(self, opt):
            ...
        def sphere_to_uv(self, fov_ypr)::
        # Sample the given FOV at the given sampling frequency and output the spatial polar coordinates of the sampling points.
            ...
        @classmethod
        def uv_to_coor(cls, *args):
        # Convert spherical coordinates to planar coordinates.
            pass
        def get_fov(self, *args):
        # Generate FOV image.
            ...
    ```
    Freedom1 solution uses different tile segmentation methods and projection methods, 
    so it is necessary to rewrite some functions in `BaseProjection`.
    Function details can be viewed in file [projection/freedom1_projection.py](../e3po/projection/freedom1_projection.py):
    ```
    @projection_registry.register()
    class Freedom1Projection(BaseProjection):
        @classmethod
        def uv_to_coor(cls, *args):
            ...
        def get_fov(self, *args):
            ...
        def _fov_result(self, fov_uv, server_motion)::
        # Sampling coordinates required for generating FOV images.
            ...
    ```

3. Decision module<br>
    The decision for Freedom1 solution is completed in the data preprocessing stage.

4. Evaluation module<br>
    Your class needs to inherit from `evaluation.basl_eval.BaseEvaluation` and override the corresponding functions within it.
    More details can be viewed in file [evaluation/base_eval.py](../e3po/evaluation/base_eval.py),
    here is a brief introduction to `BaseEvaluation`:
    ```
    class BaseEvaluation:
    def __init__(self, opt):
        ...
    def set_base_ts(self, base_ts):
    # 
        ...
    def evaluate_motion(self, fov_ts, fov_direction):
    # Evaluate a certain motion.
        pass
    def evaluate_misc(self):
    # Summative evaluation.
        ...
    def _init_frame_extractor(self):
    # Initialize frame extractor
        ...
    def _get_ground_truth_img(self, img_index, uv, fov_direction):
    # Generate or read ground truth image.
        ...
    def extract_frame(self, projection_mode, quality, target_idx):
    # Extract frame from video.
        ...
    def img2video(self, cmd, data=None):
    # Convert FOV frames into video.
        ...
    ```
    Freedom1 solution need to rewrite some functions in `BaseEvaluation`.
    Function details can be viewed in file [evaluation/freedom1_eval.py](../e3po/evaluation/freedom1_eval.py):
    ```
    @evaluation_registry.register()
    class Freedom1Evaluation(BaseEvaluation):
    def __init__(self, opt):
        ...
    def _decision_to_playable(self):
        # Calculate when the client can play what content and the transmission volume of each chunk based on decision information,
        # network bandwidth, RTT, decision location, and rendering delay.
        ...
    def evaluate_motion(self, fov_ts, fov_direction):
        # Evaluate a certain motion.
        ...
    def evaluate_misc(self):
        # Summative evaluation.
        ...
    def _calculate_psnr_ssim(self, fov_direction, server_tile_list, img_index):
        # Generate ground truth image and actual FOV image based on motion, and calculate PSNR and SSIM
        ...
    ```
