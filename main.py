#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project：     sonarGUI
@File：        main.py
@Author：      wzj
@Description:  主界面线程
@Created：     2023/7/8
@Modified:
"""

from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMenu
from ui.main_window import Ui_mainWindow
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QImage, QPixmap

import sys
import json
import os
import cv2
import queue

from ui.sonar_win import Window
from modules.detectThread import YoloDetThread
from modules.CustomMessageBox import MessageBox
from modules.logger import Logger
from modules.decodeThread import DecodeThread


# 程序主窗口
class MainWindow(QMainWindow, Ui_mainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.m_flag = False
        self.img_queue = queue.Queue()       # 用于子线程间传输图片；数据解析线程为生产者，目标检测线程为消费者

        # style 1: window can be stretched
        # self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint)

        # style 2: window can not be stretched
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint
                            | Qt.WindowSystemMenuHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        # self.setWindowOpacity(0.85)  # Transparency of window

        self.minButton.clicked.connect(self.showMinimized)
        self.maxButton.clicked.connect(self.max_or_restore)
        # show Maximized window
        self.maxButton.animateClick(10)
        self.closeButton.clicked.connect(self.close)

        self.qtimer = QTimer(self)
        self.qtimer.setSingleShot(True)
        self.qtimer.timeout.connect(lambda: self.statistic_label.clear())

        # search models automatically
        self.modelComboBox.clear()
        self.pt_list = os.listdir('weights')
        self.pt_list = [file for file in self.pt_list if file.endswith('.pt')]
        self.pt_list.sort(key=lambda x: os.path.getsize('./weights/'+x))
        self.modelComboBox.clear()
        self.modelComboBox.addItems(self.pt_list)
        self.qtimer_search = QTimer(self)
        self.qtimer_search.timeout.connect(lambda: self.search_pt())
        self.qtimer_search.start(2000)

        # 单波束探鱼仪数据解析线程
        self.decode_thread = DecodeThread(self.img_queue)
        self.decode_thread.send_msg.connect(lambda x: self.statistic_msg(x))
        self.decode_thread.percent_length = self.progressSlider.maximum()
        self.decode_thread.send_percent.connect(lambda x: self.progressSlider.setValue(x))
        self.progressSlider.sliderReleased.connect(self.change_percent)

        # Logger
        self.log = Logger()

        # yolov5 thread
        self.detect_thread = YoloDetThread(self.img_queue)
        self.model_type = self.modelComboBox.currentText()
        self.detect_thread.weights = "./weights/%s" % self.model_type
        self.detect_thread.source = '0'
        self.detect_thread.send_raw.connect(lambda x: self.show_image(x, self.raw_video))
        self.detect_thread.send_img.connect(lambda x: self.show_image(x, self.out_video))
        self.detect_thread.send_statistic.connect(self.show_statistic)
        self.detect_thread.send_msg.connect(lambda x: self.show_msg(x))

        self.detect_thread.send_fps.connect(lambda x: self.fpsLabel.setText(x))

        self.fileButton.clicked.connect(self.open_file)
        self.sonarButton.clicked.connect(self.chose_sonar)

        self.runButton.clicked.connect(self.run_or_continue)
        self.stopButton.clicked.connect(self.stop)

        self.modelComboBox.currentTextChanged.connect(self.change_model)
        self.confSpinBox.valueChanged.connect(lambda x: self.change_val(x, 'confSpinBox'))
        self.confSlider.valueChanged.connect(lambda x: self.change_val(x, 'confSlider'))
        self.iouSpinBox.valueChanged.connect(lambda x: self.change_val(x, 'iouSpinBox'))
        self.iouSlider.valueChanged.connect(lambda x: self.change_val(x, 'iouSlider'))
        self.gainSpinBox.valueChanged.connect(lambda x: self.change_val(x, 'gainSpinBox'))
        self.gainSlider.valueChanged.connect(lambda x: self.change_val(x, 'gainSlider'))
        self.absorbSpinBox.valueChanged.connect(lambda x: self.change_val(x, 'absorbSpinBox'))
        self.absorbSlider.valueChanged.connect(lambda x: self.change_val(x, 'absorbSlider'))
        self.cutButton.clicked.connect(self.saveOneImg)
        self.speedButton.clicked.connect(self.setSpeed)
        self.load_setting()

    def search_pt(self):
        pt_list = os.listdir('weights')
        pt_list = [file for file in pt_list if file.endswith('.pt')]
        pt_list.sort(key=lambda x: os.path.getsize('./weights/' + x))

        if pt_list != self.pt_list:
            self.pt_list = pt_list
            self.modelComboBox.clear()
            self.modelComboBox.addItems(self.pt_list)

    def saveOneImg(self):  # 每按一次cutButton，保存一张图片到result文件夹
        pass

    def chose_sonar(self):
        self.sonar_window = Window()
        config_file = 'config/ip.json'
        if not os.path.exists(config_file):
            ip = "sonar://admin:admin888@192.168.1.67:555"
            new_config = {"ip": ip}
            new_json = json.dumps(new_config, ensure_ascii=False, indent=2)
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(new_json)
        else:
            config = json.load(open(config_file, 'r', encoding='utf-8'))
            ip = config['ip']
        self.sonar_window.sonarEdit.setText(ip)
        self.sonar_window.show()
        self.sonar_window.sonarButton.clicked.connect(lambda: self.load_sonar(self.sonar_window.sonarEdit.text()))

    def load_sonar(self, ip):
        try:
            self.stop()
            MessageBox(
                self.closeButton, title='提示', text='Loading sonar stream', time=1000, auto=True).exec_()
            self.detect_thread.source = ip
            new_config = {"ip": ip}
            new_json = json.dumps(new_config, ensure_ascii=False, indent=2)
            with open('config/ip.json', 'w', encoding='utf-8') as f:
                f.write(new_json)
            self.statistic_msg('Loading sonar：{}'.format(ip))
            self.sonar_window.close()
        except Exception as e:
            self.statistic_msg('%s' % e)

    def load_setting(self):
        config_file = 'config/setting.json'
        if not os.path.exists(config_file):
            print('config_file not exist.')
            iou = 0.26
            conf = 0.33
            gain = 10
            absorb = 10
            new_config = {"iou": iou,
                          "conf": conf,
                          "gain": gain,
                          "absorb": 1
                          }
            new_json = json.dumps(new_config, ensure_ascii=False, indent=2)
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(new_json)
        else:
            config = json.load(open(config_file, 'r', encoding='utf-8'))
            iou = config['iou']
            conf = config['conf']
            gain = config['gain']
            absorb = config['absorb']
        self.confSpinBox.setValue(conf)
        self.iouSpinBox.setValue(iou)
        self.gainSpinBox.setValue(gain)
        self.absorbSpinBox.setValue(absorb)
        self.saveOneImg()

    def change_val(self, x, flag):
        if flag == 'confSpinBox':
            self.confSlider.setValue(int(x*100))
        elif flag == 'confSlider':
            self.confSpinBox.setValue(x/100)
            self.detect_thread.conf_thres = x/100
        elif flag == 'iouSpinBox':
            self.iouSlider.setValue(int(x*100))
        elif flag == 'iouSlider':
            self.iouSpinBox.setValue(x/100)
            self.detect_thread.iou_thres = x/100
        elif flag == 'gainSpinBox':
            self.gainSlider.setValue(x)
        elif flag == 'gainSlider':
            self.gainSpinBox.setValue(x)
        elif flag == 'absorbSpinBox':
            self.absorbSlider.setValue(x)
        elif flag == 'absorbSlider':
            self.absorbSpinBox.setValue(x)
        elif flag == 'progressSlider':
            self.decode_thread.progress_slider_changed(x)
        else:
            pass

    def change_percent(self):
        self.decode_thread.progress_slider_changed(self.progressSlider.value())

    def statistic_msg(self, msg):
        self.statistic_label.setText(msg)
        self.log.logger.info(msg)
        # self.qtimer.start(3000)

    def show_msg(self, msg):
        self.runButton.setChecked(Qt.Unchecked)
        self.statistic_msg(msg)
        # if msg == "Finished":
        #     self.saveCheckBox.setEnabled(True)

    def change_model(self, x):
        self.model_type = self.modelComboBox.currentText()
        self.detect_thread.weights = "./weights/%s" % self.model_type
        self.statistic_msg('模型变更为 %s' % x)

    def open_file(self):
        config_file = 'config/fold.json'
        # config = json.load(open(config_file, 'r', encoding='utf-8'))
        config = json.load(open(config_file, 'r', encoding='utf-8'))
        open_fold = config['open_fold']
        if not os.path.exists(open_fold):
            open_fold = os.getcwd()
        name, _ = QFileDialog.getOpenFileName(self, '选择文件', open_fold, "数据文件(*.txt *.mp4 *.mkv *.avi *.flv "
                                                                          "*.jpg *.png)")
        if name:
            self.decode_thread.source = name
            self.statistic_msg('已加载文件：{}'.format(os.path.basename(name)))
            self.decode_thread.next_start_line = 0
            self.progressSlider.setValue(0)
            config['open_fold'] = os.path.dirname(name)
            config_json = json.dumps(config, ensure_ascii=False, indent=2)
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(config_json)
            self.stop()

    def max_or_restore(self):
        if self.maxButton.isChecked():
            self.showMaximized()
        else:
            self.showNormal()

    def run_or_continue(self):
        self.decode_thread.jump_out = False
        self.detect_thread.jump_out = False
        if self.runButton.isChecked():
            self.decode_thread.is_continue = True
            if not self.decode_thread.isRunning():
                self.decode_thread.start()

            self.detect_thread.is_continue = True
            if not self.detect_thread.isRunning():
                self.detect_thread.start()

            source = os.path.basename(self.decode_thread.source)
            source = 'sonar' if source.isnumeric() else source
            self.statistic_msg('历史文件回放中 >> 数据源：%s' % source)
        else:
            self.decode_thread.is_continue = False
            self.statistic_msg('已暂停')

    def stop(self):
        self.decode_thread.jump_out = True

    @staticmethod
    def show_image(img_src, label):
        try:
            ih, iw, _ = img_src.shape
            w = label.geometry().width()
            h = label.geometry().height()
            # keep original aspect ratio
            if iw/w > ih/h:
                scal = w / iw
                nw = w
                nh = int(scal * ih)
                img_src_ = cv2.resize(img_src, (nw, nh))

            else:
                scal = h / ih
                nw = int(scal * iw)
                nh = h
                img_src_ = cv2.resize(img_src, (nw, nh))

            frame = cv2.cvtColor(img_src_, cv2.COLOR_BGR2RGB)
            img = QImage(frame.data, frame.shape[1], frame.shape[0], frame.shape[2] * frame.shape[1],
                         QImage.Format_RGB888)
            label.setPixmap(QPixmap.fromImage(img))

        except Exception as e:
            print(repr(e))

    def show_statistic(self, statistic_dic):
        try:
            self.resultWidget.clear()
            statistic_dic = sorted(statistic_dic.items(), key=lambda x: x[1], reverse=True)
            statistic_dic = [i for i in statistic_dic if i[1] > 0]
            results = [' '+str(i[0]) + '：' + str(i[1]) for i in statistic_dic]
            self.resultWidget.addItems(results)

        except Exception as e:
            print(repr(e))

    def setSpeed(self):
        if self.speedButton.isChecked():
            self.decode_thread.speed = 5
        else:
            self.decode_thread.speed = 1

    def closeEvent(self, event):
        self.decode_thread.jump_out = True
        config_file = 'config/setting.json'
        config = dict()
        config['iou'] = self.iouSpinBox.value()
        config['conf'] = self.confSpinBox.value()
        config['gain'] = self.gainSpinBox.value()
        config['absorb'] = self.absorbSpinBox.value()
        config_json = json.dumps(config, ensure_ascii=False, indent=2)
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_json)
        MessageBox(
            self.closeButton, title='提示', text='正在关闭', time=2000, auto=True).exec_()
        sys.exit(0)

    def mousePressEvent(self, event):
        self.m_Position = event.pos()
        if event.button() == Qt.LeftButton:
            if 0 < self.m_Position.x() < self.groupBox.pos().x() + self.groupBox.width() and \
                    0 < self.m_Position.y() < self.groupBox.pos().y() + self.groupBox.height():
                self.m_flag = True

    def mouseMoveEvent(self, QMouseEvent):
        if Qt.LeftButton and self.m_flag:
            self.move(QMouseEvent.globalPos() - self.m_Position)

    def mouseReleaseEvent(self, QMouseEvent):
        self.m_flag = False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWin = MainWindow()
    myWin.show()
    sys.exit(app.exec_())
