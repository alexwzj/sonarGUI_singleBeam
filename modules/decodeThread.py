#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project：     sonarGUI 
@File：        decodeThread.py
@Author：      wzj
@Description:  数据解析线程，当数据源选择为raw_data或探鱼仪实时数据时，此线程启动；选择其它数据源时，此线程终止。
@Created：     2023/7/18
@Modified:     
"""

from PyQt5.QtCore import Qt, QPoint, QTimer, QThread, pyqtSignal


class DecodeThread(QThread):
    pass
