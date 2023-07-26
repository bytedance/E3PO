# Introduction
E3PO is an **O**pen **P**latform for **3**60° video streaming simulation and **E**valuation, 
which is named by reversing the order of OP3E. With unified video source and motion trace, 
E3PO can simulate and compare different 360° video streaming approaches through providing an universal and open platform. 
Particularly, comparison of 360° video preprocessing (projection and tiling), 
streaming strategies (motion prediction and bitrate adaptation), evaluation (V-PSNR and bandwidth), 
as well as visual results of different approaches can be conducted on E3PO. We hope it can achieve: 

- Help beginners get started faster.
- Make it easier for researchers to implement and test their approaches.
- Enable people to use more advanced algorithms.


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
Prepare an 8K, 30fps 360° video with equi-rectangular projection (ERP), rename and place it at /e3po/source/video/sample.mp4. 
By default, the first 10 seconds of the video will be evaluated. To change the video parameters, please refer to [BasicTutorial](./docs/BasicTutorial.md).
3. Motion Trace<br>
Prepare a motion trace file (Similar to that downloaded from [360VidStr](https://github.com/360VidStr/A-large-dataset-of-360-video-user-behaviour/blob/main/AggregatedDataset/7.txt)), rename and place it at /e3po/source/motion_trace/motion_trace.log.



## Run scripts
Taking the ERP approach as an example, executes the following steps.
1. Run the [prepare_data.py](./e3po/prepare_data.py) script
```
python ./e3po/prepare_data.py -opt options/example/E1.yml
```
2. Run the [make_decision.py](./e3po/make_decision.py) script
```
python ./e3po/make_decision.py -opt options/example/E1.yml
```
3. Run the [make_evaluation.py](./e3po/make_evaluation.py) script
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

We have implemented eight typical approaches on E3PO, with their detailed descriptions shown in the following table.

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
We welcome more people to join us in maintaining and building E3PO. For ease of current stage management, users can submit their contributions to E3PO, provided that they meet the following two requirements:

- The submitted code should be reviewed by the E3PO group.
- The submitted code should follow the [GPL 2.0 License](./COPYING) adopted by E3PO.


# License

[GPL 2.0 License](./COPYING)
