<center>
    Organized and sponsored by 
</center>
<div align=center>
    <img src=./bytedance.png width=200 height= /> 
    <img src=./PICO_logo.png width=200 height= />
</div>

# Challenge Description
In recent times, 360-degree video on-demand streaming has garnered significant interest across academia and the industry. With sales of VR headsets from prominent brands like Meta and Pico surpassing 10 million units and Apple's recent entry into the scene with its debut spatial computing device, it's evident that the horizon for 360-degree videos and their applications is expanding rapidly. These videos, distinct from traditional 2D counterparts, come with challenges like immense data transmission volume and stringent interactive latency demands. Due to the complexity of the overall system, there is yet no universally endorsed processing solution for 360-degree video transmission.

To foster advancements in 360-degree video on-demand streaming, ByteDance presents this challenge. Participants will benefit from our open-source evaluation platform, [E3PO](https://github.com/bytedance/E3PO), designed entirely in Python. E3PO facilitates the simulation and assessment of a 360-degree video streaming system, empowering contestants to focus on the creation and finesse of pivotal algorithms.


# Task
Contestants shall design and implement a 360-degree video on-demand streaming solution using E3PO. The goal of the solution is to deliver the best user viewing quality using the least system resources. We use the objective video quality of user's actual viewing area on the terminal device, measured by [Viewport PSNR](https://web.archive.org/web/20160909173146id_/http://web.stanford.edu:80/~harilaks/pdfs/2015_ISMAR.pdf) (denoted as $VPSNR$ in this challenge) to evaluate the user viewing quality. In terms of system recources, we consider three major costs:
- $C_b$: the bandwidth cost of streaming all data from the server to user
- $C_s$: the storage cost of storing video data on the server
- $C_c$: the computation cost for some solutions that require real-time processing or transcoding





We define a performance metric score as follows: 
$$S=\frac{VPSNR}{w_1*C_b+w_2*C_s + w_3*C_c}$$
Note that E3PO automatically measures performance metrics and calculates $S$ for each simulation.  We will provide 8K panoramic video sequences as well as real users' head motion trace data for contestants' testing and final evaluation.


# Important Dates
 - | Challenge Relase | Register by | Upload by | Notifications on | Camera-Ready due
 :-: | :-: | :-: | :-: | :-: | :-:
MMSys Challenge24 | Sep. 11th | Jan. 12th | Feb. 5th | Feb. 16th | Mar. 1th



# Registration
This challenge is open to any individual, academic or commercial institution (except ByteDance employees). Interested individuals are welcome to participate as a team. Each team can have one or more members (up to 4). Each individual can only be part of one team. The organizers reserve the right to disqualify any participant for misleading information or inappropriate behavior during the challenge.

To register for the challenge, first please fill out the [form](https://wenjuan.feishu.cn/m?t=s3fCWQuPlLPi-it3o). Once we receive your information, we will confirm your registration. *Please note that we only accept submissions from registered teams.*


After registration, please download and sign up with Lark and join the [topic group](./mmsys24gc_group.jpeg) for all future updates of the challenge and Q&A. 


# Submission
Please refer to: [MMSys2024 Submission Guidelines](https://github.com/bytedance/E3PO/blob/main/docs/submission_guideline/submission.md)

# Awards (TBD)
The top three teams will be eligible to have their technical papers included in MMSys proceedings providing the paper passes the quality review before the camera-ready deadline and the author pays the full conference registration. Meanwhile, all winning teams will receive a cash prize sponsored by ByteDance (the detailed amount will be announced). 

# Challenge Organizers
- Yongqiang Gui (guiyongqiang@bytedance.com)
- Yanyan Suo (suoyanyan@bytedance.com)
- Tian Zhang (zhangtian.ztzt@bytedance.com)
- Guangbao Xu (xuguangbao@bytedance.com)
- Shu Shi (shishu.1513@bytedance.com)