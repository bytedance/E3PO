# Custom Scheme
We have provided some reference solutions, each of which includes: 
* data processing module
* projection module 
* decision module

Below, we will first introduce how to use the register to call various customized modules, and then provide a simple example to illustrate which parts of these customized solution should be implemented.

## How to use register
Each module is dynamically instantiated through a register. E3PO defines registers for them in [utils/register.py](../e3po/utils/registry.py):
```
data_registry = Registry('data_registry')
decision_registry = Registry('decision_registry')
evaluation_registry = Registry('evaluation_registry')
projection_registry = Registry('projection_registry')
```
Taking the **data** module of on_demand mode as an example, E3PO uses a Python decorator to register your class: 
```
from e3po.utils.registry import data_registry

@data_registry.register()
class OnDemandData(BaseData):
    def __init__(self, opt):
        super(OnDemandData, self).__init__(opt)
        ...
```
In addition, you also need to modify the suffix of this class name as `_data.py`, such that this class can be automatically import into the program by [data/__init__.py](../e3po/data/__init__.py). Then E3PO declares class object as follows,
```
from e3po.utils import get_opt
from e3po.utils.registry import data_registry

opt = get_opt() # read config file
data = data_registry['OnDemandData'](opt)
```
In fact, you only need to specify the class name in the configuration file,
```
data_type: OnDemandData
decision_type: OnDemandDecision
projection_type: ErpProjection
evaluation_type: OnDemandEvaluation
```
Then declare the class object through the `build_[module name]` function in `[module name]/__init__.py`:
```
from e3po.utils import get_opt
from e3po.data import build_data

opt = get_opt()
data = build_data(opt)
```

## How to implement your approach
We provide two types of modes: on-demand mode and transcoding mode. Here are two examples to introduce how to implement your approach based on these two modes, respectively.

### On-demand Mode
We use Custom-EAC approach as an example to illustrate how to implement your on-demand approach. This requires the implementation of **data** module, **projection** module, and **decision** module, which are described as follows.

1. Data module<br>
    Your class needs to inherit from `data.tile_based_data.OnDemandData` and override the corresponding functions within it. More details can be viewed in file [data/tile_based_data.py](../e3po/data/on_demand_data.py). A brief introduction of `OnDemandData` is:
    ```
    @data_registry.register()
    class OnDemandData(BaseData):
       def __init__(self, opt):
           ...
       def process_video(self):
       # make_preprocessing.py will call this function. 
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
    Custom-EAC approach uses customized tile segmentation methods, so it is necessary to rewrite some functions in `OnDemandData`. Function details can be viewed in file [approach/custom_eac/custom_eac_data.py](../e3po/approaches/custom_eac/custom_eac_data.py):
    ```
    @data_registry.register()
    class CustomEacData(OnDemandData):
        def _convert_ori_video(self):
            ...
        def _generate_tile(self):
            ...
        def _get_tile_size(self):
            ...
    ```

2. Projection module<br>
    Your class needs to inherit from `projection.tile_projection.TileProjection` and override the corresponding functions within it. More details can be viewed in file [projection/tile_projection.py](../e3po/projection/tile_projection.py). A brief introduction of `TileProjection` is:
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
    Custom-EAC approach uses different tile segmentation methods and projection methods, so it is necessary to rewrite some functions in `TileProjection`. Function details can be viewed in file [approaches/custom_eac/custom_eac_projection.py](../e3po/approaches/custom_eac/custom_eac_projection.py):
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
        def generate_fov(self, *args):
            ...
    ```

3. Decision module<br>
    Your class needs to inherit from `decision.on_demand_decision.OnDemandDecision` and override the corresponding functions within it. More details can be viewed in file [decision/on_demand_decision.py](../e3po/decision/on_demand_decision.py). A brief introduction of `OnDemandDecision` is:
    ```
    @decision_registry.register()
    class CustomEacDecision(OnDemandDecision):
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

### Transcoding Mode
We use Freedom1 solution as an example to illustrate how to implement your transcoding solution.
This requires the implementation of data module, projection module, and decision module. 

1. Data module<br>
    Your class needs to inherit from `data.transcoding_data.TranscodingData` and override the corresponding functions within it. More details can be viewed in file [data/transcoding_data.py](../e3po/data/transcoding_data.py), here is a brief introduction to `TranscodingData`:
    ```
    class BaseData:
        def __init__(self, opt):
            ...
        def process_video(self):
            # prepare_data.py will call this function. 
            pass
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
    ```
    Freedom1 approach need to rewrite some functions in `TranscodingData`. Function details can be viewed in file [approaches/freedom1/freedom1_data.py](../e3po/approaches/freedom1/freedom1_data.py):
    ```
    @data_registry.register()
    class Freedom1Data(TranscodingData):
        def _convert_ori_video(self):
            ...
        def process_video(self):
            self._convert_ori_video()
            self._generate_viewport()
            self._generate_h264()
            self._get_viewport_size()
            self._del_intermediate_file(['converted'], ['.json'])
        def _generate_viewport(self):
        # Generate VAM images.
            ...
        def _generate_h264(self):
        # Generate videos using VAM images and extract H264 files.
            ...
        def _get_viewport_size(self):
        # Read the file size of all h264 files and write them to the video_size.json in a fixed format.
            ..
        def get_size(self, *args):
        # Obtain the corresponding h264 file size based on the given parameters.
            ...
    ```

2. Projection module<br>
    Your class needs to inherit from `projection.base_projection.BaseProjection` and override the corresponding functions within it. More details can be viewed in file [projection/base_projection.py](../e3po/projection/base_projection.py), here is a brief introduction to `BaseProjection`:
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
        def generate_fov(self, *args):
        # Generate FOV image.
            ...
    ```
    Freedom1 approach uses different tile segmentation methods and projection methods, so it is necessary to rewrite some functions in `BaseProjection`.
    Function details can be viewed in file [approaches/freedom1/freedom1_projection.py](../e3po/approaches/freedom1/freedom1_projection.py):
    ```
    @projection_registry.register()
    class Freedom1Projection(BaseProjection):
        @classmethod
        def uv_to_coor(cls, *args):
            ...
        def generate_fov(self, *args):
            ...
        def _fov_result(self, fov_uv, server_motion)::
        # Sampling coordinates required for generating FOV images.
            ...
    ```

3. Decision module<br>
    The decision for Freedom1 solution is completed in the data preprocessing stage.
