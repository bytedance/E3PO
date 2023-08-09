# Introduction
E3PO is an **O**pen **P**latform for **3**60° video streaming simulation and **E**valuation.
E3PO is designed to support the simulation of a variety of 360° video streaming approaches that have been proposed so far, including projection based, tile based, or transcoding based. Particularly, E3PO allows users to convert 360° video into standard or customized projections, segment video into equal or adaptive sizes, implement customized motion prediction algorithms, apply different streaming strategies, and evaluate using any user-specific metrics. Most importantly, E3PO generats the actual visual sequences that will display on the user screen for each simulation. 

Therefore, E3PO provides a perfect solution to objectively compare the performance of different 360° video streaming approaches, using the same video content and same motion trace.



# Framework
The framework of E3PO is illustrated as the following figure, which consists of three principal modules, i.e., the ***video pre-processor***, the ***streaming simulator*** and the ***system evaluator***.

To simulate a streaming approach, the ***video pre-processor*** first segments the 360° panoramic video into small video tile chunks according to users’ specific projection and tiling parameters. Then the ***streaming simulator*** reads the provided head motion trace, and simulates the detailed streaming actions which include when and which video chunk is transmitted. Last, the ***system evaluator*** synthesizes the video sequence that is displayed on the user screen and calculates various metrics.

![](/docs/Framework.jpg "e3po_framework")



# Quick Start

## Code & Dataset
1. Download E3PO code
```
git clone https://github.com/bytedance/E3PO.git
```

2. Video Source<br>
Prepare a 360° video, rename and place it at /e3po/source/video/sample.mp4. 
By default, the 360° video is 8K, 30 fps, with equi-rectangular projection (ERP), and only the first 10 seconds of the video will be used. To change any parameters, please refer to [BasicTutorial](./docs/BasicTutorial.md).
3. Motion Trace<br>
Prepare a motion trace file (Similar to that downloaded from [360VidStr](https://github.com/360VidStr/A-large-dataset-of-360-video-user-behaviour/blob/main/AggregatedDataset/7.txt)), rename and place it at /e3po/source/motion_trace/motion_trace.log.



## Run scripts
To simulate the streaming process, three python scripts need to be executed sequentially. For example, with the sample simulation E1 we have provided in the project: 
1. Run the [prepare_data.py](./e3po/prepare_data.py) script (***video pre-processor*** module)
```
python ./e3po/prepare_data.py -opt options/example/E1.yml
```
2. Run the [make_decision.py](./e3po/make_decision.py) script (***streaming simulator*** module)
```
python ./e3po/make_decision.py -opt options/example/E1.yml
```
3. Run the [make_evaluation.py](./e3po/make_evaluation.py) script (***system evaluator*** module)
```
python ./e3po/make_evaluation.py -opt options/example/E1.yml
```

Corresponding results can be found at 
```
|---e3po
    |---source
        |---video
            |---[example]
                |---[sample]
                    |---[E1]
                        |---video_size.json
                        |---converted_29.mp4
    |---result
        |---[example]
            |---[E1]
                |---decision.json
                |---evaluation.json
                |---frames
                    |---xxx.png
                    |---output.mp4
    |---log
        |---[example]
            |---E1_evaluation.log
            |---E1_prepare_data.log
```

## Examples
We have implemented eight simple but typical approaches, with their detailed descriptions shown in the following table.

|  Name             | Projection | Background Stream |  Tiling | Resolution |
|  ----             | ----       | ----              | ----    | ----       |
|  E1               | ERP        | w/o               | 6x6     | -          |
|  C1               | CMP        | w/o               | 6x6     | -          |
|  C2               | CMP        | w/                | 6x6     | -          |
|  C3               | CMP        | w/                | 6x12    | -          |
|  A1               | EAC        | w/                | 6x12    | -          |
|  F1 (Freedom)     | ERP        | w/o               | 1x1     | 1680x1120  |
|  F2 (Freedom)     | ERP        | w/o               | 1x1     | 2400x2176  |
|  Full             | ERP        | w/o               | 1x1     | -          |


The visual comparison results of these eight approaches are illustrated as the following figure.

![](/docs/comparison.jpg "comparison_results")


For more details, please refer to [BasicTutorial](./docs/BasicTutorial.md).


# Contributes
We welcome researchers to simulate their own streaming systems using E3PO and submit their implementation bakc to this project, so that the community can better compare the performance of different solutions. Users making contributions to E3PO shall meet the following two requirements:

- The submitted code should be reviewed by the E3PO group.
- The submitted code should follow the [GPL 2.0 License](./COPYING) adopted by E3PO.


# License

[GPL 2.0 License](./COPYING)
