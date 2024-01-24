<div align=center>
    <font size=10>Organized and sponsored by</font>
</div>

<div align=center>
    <img src=bytedance.jpg height= 60 />
</div>


# Challenge Description
In recent times, 360-degree video on-demand streaming has garnered significant interest across academia and the industry. With sales of VR headsets from prominent brands like Meta and Pico surpassing 10 million units and Apple's recent entry into the scene with its debut spatial computing device, it's evident that the horizon for 360-degree videos and their applications is expanding rapidly. These videos, distinct from traditional 2D counterparts, come with challenges like immense data transmission volume and stringent interactive latency demands. Due to the complexity of the overall system, there is yet no universally endorsed processing solution for 360-degree video transmission.

To foster advancements in 360-degree video on-demand streaming, ByteDance presents this challenge. Participants will benefit from our open-source evaluation platform, [E3PO](https://github.com/bytedance/E3PO), designed entirely in Python. E3PO facilitates the simulation and assessment of a 360-degree video streaming system, empowering contestants to focus on the creation and finesse of pivotal algorithms.


# Task
Contestants shall design and implement a 360-degree video on-demand streaming solution using E3PO. The goal of the solution is to deliver the best user viewing quality using the least system resources. We use the objective video quality of user's actual viewing area on the terminal device, measured by $MSE$ to evaluate the user viewing quality. In terms of system recources, we consider three major costs:
- $w_1 * C_b$: the bandwidth cost of streaming all data from the server to user
- $w_2*C_s$: the storage cost of storing video data on the server
- $w_3*C_c$: the computation cost for some solutions that require real-time processing or transcoding


We define a performance metric score as follows. The denominator of the formula can be considered as a Lagrangian variant of the rate-distortion optimization problem, and its physical interpretation is to minimize the distortion and cost simultaneously.

<div align=center>
    <img src=./formula.jpg width=400 height= />
</div>

The weight coefficients $\alpha = 0.006$ and $\beta=10$ ($\alpha$ and $\beta$ may changes for different test video sequences) are used to control the distortion and cost, respectively. Meanwhile, for the weights $w_1=0.09$, $w_2=0.000015$, and $w_3=0.000334$ in the cost, we referred to the pricing table on the [AWS](https://aws.amazon.com/) official website. The unit for $C_b$ and $C_s$ is GB, and $C_c$ represents the duration of the video playback in seconds.

Note that E3PO automatically measures performance metrics and calculates $S$ for each simulation. We provide [**8K panoramic video sequences as well as real users' head motion trace**](https://bytedance.larkoffice.com/drive/folder/QQgJfhxs7lor3xdb0WGcTYMsnPb) data for contestants' testing and final evaluation.


# Important Dates
<div align="center">

| Challenge Relase |   Register by   |    Upload by    | Notifications on | Camera-Ready due |
|:-------------:|:---------------:|:---------------:|:----------------:|:-------------:|
| September 11, 2023  | January 26, 2024 | February 26, 2024 |  March 8, 2024  | March 15, 2024

</div>

# Registration
This challenge is open to any individual, academic or commercial institution. Interested individuals are welcome to participate as a team. Each team can have one or more members (up to 4). Each individual can only be part of one team. The organizers reserve the right to disqualify any participant for misleading information or inappropriate behavior during the challenge.

Participants can register for this grand challenge by either filling out the [**registration form**](https://wenjuan.feishu.cn/m?t=s3fCWQuPlLPi-it3o) or sending their registration information to the organizer via email. Once we receive your information, we will confirm your registration. Please note that we only accept submissions from registered teams. After registration, please download and sign up with Lark and join the [**discussion group**](mmsys24gc_group.jpeg) for all future updates of the challenge and Q&A. 

For the submission guidelines, please refer to [**MMSys2024 Submission Guidelines**](https://github.com/bytedance/E3PO/blob/main/mmsys24gc/submission.md)

# Awards
The teams ranking top three in the final evaluation win the challenge. All winning teams will receive a cash prize sponsored by ByteDance, as presented in the table below. Meanwhile, all winning teams are expected to publish their technical papers in MMSys proceedings (providing the paper passes the quality review before the camera-ready deadline), participate the conference to present their solutions, and pay the full conference registration. Teams that fail to meet these expectations are considered to give up the awards. 

<div align="center">

| First Prize | Second Prize | Third Prize |
|:-------------:|:-------------:|:-------------:|
| $4000 |  $2500  | $1500

</div>


# Challenge Organizers
- Yongqiang Gui (guiyongqiang@bytedance.com)
- Yanyan Suo (suoyanyan@bytedance.com)
- Tian Zhang (zhangtian.ztzt@bytedance.com)
- Guangbao Xu (xuguangbao@bytedance.com)
- Shu Shi (shishu.1513@bytedance.com)