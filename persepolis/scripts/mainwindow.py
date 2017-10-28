# -*- coding: utf-8 -*-

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from functools import partial
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication,  QAction, QFileDialog, QSystemTrayIcon, QMenu, QApplication, QInputDialog, QMessageBox
from PyQt5.QtGui import QIcon, QColor, QPalette, QStandardItem, QCursor
from PyQt5.QtCore import QTime, QCoreApplication, QRect, QSize, QPoint, QThread, pyqtSignal, Qt
import os
import time
from time import sleep
import random
from persepolis.scripts.after_download import AfterDownloadWindow
from persepolis.scripts.text_queue import TextQueue
from persepolis.scripts.flashgot_queue import FlashgotQueue
from persepolis.scripts.addlink import AddLinkWindow
from persepolis.scripts.properties import PropertiesWindow
from persepolis.scripts.progress import ProgressWindow
from persepolis.scripts import download
from persepolis.gui.mainwindow_ui import MainWindow_Ui, QTableWidgetItem
from persepolis.scripts.log_window import LogWindow
from persepolis.scripts.newopen import Open, writeList, readList, readDict
from persepolis.scripts.play import playNotification
from persepolis.scripts.bubble import notifySend
from persepolis.scripts.setting import PreferencesWindow
from persepolis.scripts.about import AboutWindow
from persepolis.gui import icons_resource
from persepolis.scripts import spider
from persepolis.scripts import osCommands
from persepolis.scripts import logger
import platform
from copy import deepcopy
from persepolis.scripts.shutdown import shutDown
from persepolis.scripts.update import checkupdate
from persepolis.scripts.data_base import PluginsDB, PersepolisDB

# THIS FILE CREATES MAIN WINDOW

# The GID (or gid) is a key to manage each download. Each download will be assigned a unique GID.
# The GID is stored as 64-bit binary value in aria2. For RPC access,
# it is represented as a hex string of 16 characters (e.g., 2089b05ecca3d829).
# Normally, aria2 generates this GID for each download, but the user can
# specify GIDs manually



# shutdown_notification = 0 >> persepolis is running 
# 1 >> persepolis is ready for closing(closeEvent  is called) 
# 2 >> OK, let's close application!

global shutdown_notification
shutdown_notification = 0

# checking_flag : 0 >> normal situation ;
# 1 >> remove button or delete button pressed or sorting form viewMenu or ... toggled by user ;
# 2 >> check_download_info function is stopping until remove operation done ;
# 3 >> deleteFileAction is done it's job and It is called removeButtonPressed. 

global checking_flag
checking_flag = 0

# when rpc connection between persepolis and aria is disconnected >>
# aria2_disconnected = 1
# aria2_disconnected = 0 >> every thing is ok :)
global aria2_disconnected
aria2_disconnected = 0

global aria_startup_answer
aria_startup_answer = None


global button_pressed_counter
button_pressed_counter = 0

global plugin_links_checked
plugin_links_checked = False

# get home address for this user
home_address = os.path.expanduser("~")

# find os platform
os_type = platform.system()

# persepolis tmp folder (temporary folder)
if os_type != 'Windows':

    user_name_split = home_address.split('/')
    user_name = user_name_split[2]

    persepolis_tmp = '/tmp/persepolis_' + user_name
else:
    persepolis_tmp = os.path.join(
        str(home_address), 'AppData', 'Local', 'persepolis_tmp')


# config_folder
if os_type == 'Linux' or os_type == 'FreeBSD' or os_type == 'OpenBSD':
    config_folder = os.path.join(
        str(home_address), ".config/persepolis_download_manager")
elif os_type == 'Darwin':
    config_folder = os.path.join(
        str(home_address), "Library/Application Support/persepolis_download_manager")
elif os_type == 'Windows':
    config_folder = os.path.join(
        str(home_address), 'AppData', 'Local', 'persepolis_download_manager')


download_info_folder = os.path.join(config_folder, "download_info")


# persepolis temporary download folder
if os_type != 'Windows':
    temp_download_folder = str(home_address) + '/.persepolis'
else:
    temp_download_folder = os.path.join(
        str(home_address), 'AppData', 'Local', 'persepolis')


# see persepolis.py file for show_window_file and plugin_ready 
plugin_ready = os.path.join(persepolis_tmp, 'persepolis-plugin-ready')

show_window_file = os.path.join(persepolis_tmp, 'show-window')

# start aria2 when Persepolis starts
class StartAria2Thread(QThread):
    ARIA2RESPONDSIGNAL = pyqtSignal(str)

    def __init__(self):
        QThread.__init__(self)

    def run(self):
        # aria_startup_answer is None when Persepolis starts! and after
        # ARIA2RESPONDSIGNAL emitting yes , then startAriaMessage function
        # changing aria_startup_answer to 'Ready'
        # ARIA2RESPONDSIGNAL have 3 conditions >>> 
        # 1. no (aria didn't respond) 2. yes(aria is respond) 3.try again(Persepolis retry to connecting aria2)
        global aria_startup_answer

        # check that aria2 is running or not!
        answer = download.aria2Version()

        # if Aria2 wasn't started before, so start it!
        if answer == 'did not respond':
            print('Starting Aria2')

            # write in log file.
            logger.sendToLog(
                            "Starting Aria2", "INFO")
 
            # try 5 time if aria2 doesn't respond!
            for i in range(5):
                answer = download.startAria()
                if answer == 'did not respond' and i != 4:
                    signal_str = 'try again'
                    self.ARIA2RESPONDSIGNAL.emit(signal_str)
                    sleep(2)
                else:
                    break

        # if Aria2 doesn't respond to Persepolis ,ARIA2RESPONDSIGNAL is
        # emitting no
        if answer == 'did not respond':
            signal_str = 'no'
        else:
            # Aria2 is responding :)
            signal_str = 'yes'
            print('Aria2 is running')
            logger.sendToLog(
                            "Aria2 is running", "INFO")
 
        # emit the signal
        # ARIA2RESPONDSIGNAL have 3 conditions >>> 
        # 1. no (aria didn't respond) 2. yes(aria is respond) 3.try again(Persepolis retry to connecting aria2)
        self.ARIA2RESPONDSIGNAL.emit(signal_str)


# This thread checking that which row in download_table highlited by user
class CheckSelectedRowThread(QThread):
    CHECKSELECTEDROWSIGNAL = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)

    def run(self):
        while shutdown_notification == 0 and aria_startup_answer != 'ready':
            sleep(1)
        while shutdown_notification == 0:
            sleep(0.2)
            self.CHECKSELECTEDROWSIGNAL.emit()


# This thread is getting download information from aria2 and updating database
# this class is checking aria2 rpc connection! if aria rpc is not
# available , this class restarts aria!
class CheckDownloadInfoThread(QThread):
    DOWNLOAD_INFO_SIGNAL = pyqtSignal(list)
    RECONNECTARIASIGNAL = pyqtSignal(str)

    def __init__(self, parent):
        QThread.__init__(self)
        self.parent = parent

    def run(self):
        global checking_flag
        global shutdown_notification
        while True:

# shutdown_notification = 0 >> persepolis is running 
# 1 >> persepolis is ready for closing(closeEvent called) 
# 2 >> OK, let's close application!


# checking_flag : 0 >> normal situation ;
# 1 >> remove button or delete button pressed or sorting form viewMenu selected by user ;
# 2 >> check_download_info function is stopping until remove operation done ;
# 3 >> deleteFileAction is done it's job and It is called removeButtonPressed. 


            # whait until aria gets ready!(see StartAria2Thread for more information) 
            while shutdown_notification == 0 and aria_startup_answer != 'ready':
                sleep(1)

            while shutdown_notification != 1:
                sleep(0.2)
                # if checking_flag is equal to 1, it means that user pressed
                # remove or delete button . so checking download information
                # must stop until removing is done! It avoids possiblity of crashing!
                if checking_flag == 1:
                    # Ok loop is stoped!
                    checking_flag = 2

                    # check that when job is done!
                    while checking_flag != 0:
                        sleep(0.2)

                # lets getting downloads information from aria and putting them in download_status_list!

                # find gid of active downloads first! (get them from data base)
                # output of this method is a list of tuples
                active_gid_list = self.parent.persepolis_db.findActiveDownloads()

                # get download status of active downloads from aria2
                # download_status_list is a list that contains some dictionaries.  
                # every dictionary contains download information. 
                # gid_list is a list that contains gid of downloads in download_status_list. 
                # see download.py file for more information. 
                gid_list, download_status_list = download.tellActive()

                if download_status_list:
                    for gid in active_gid_list:

                        # if gid not in gid_list, so download is completed or stopped or error occured!
                        # because aria2 returns active downloads status with tellActive function in download.py file. 
                        # and compelete or stopped or errored downloads are not active downloads. 
                        # so we must get download information with tellStatus function.  
                        # see download.py file (tellStatus and tellActive functions) for more information. 
                        # if aria do not return download information with tellStatus and tellActive,
                        # then perhaps some error occured.so download information must be in data_base. 
                        if gid not in gid_list:  
                            returned_dict = download.tellStatus(gid, self.parent)
                            if returned_dict:
                                download_status_list.append(returned_dict)
                            else:
                                # check data_base
                                returned_dict = self.parent.persepolis_db.searchGidInDownloadTable(gid)
                                download_status_list.append(returned_dict)

                            # if returned_dict in None, check for availability of RPC connection.
                            else:
                                self.reconnectAria()
                                continue

                # if download_status_list in None, check for availability of RPC connection.
                else:                 
                    self.reconnectAria()
                    continue


                # now we have a list that contains download information (download_status_list)
                # lets update download table in main window and update data base!
                # first emit a signal for updating MainWindow. 
                self.DOWNLOAD_INFO_SIGNAL.emit(download_status_list)

                # updat data base!
                self.parent.persepolis_db.updateDownloadTable(download_status_list)

            # Ok exit loop! get ready for shutting down!
            shutdown_notification = 2
            break

# when rpc connection between persepolis and aria is 
# disconnected then aria2_disconnected = 1
    def reconnectAria(self):
        global aria2_disconnected
        # TODO check that aria2_disconnected is needed or must eliminated
        aria2_disconnected = 0
        # check aria2 availability by aria2Version function(see download.py file fore more information)
        answer = download.aria2Version()

        if answer == 'did not respond':
            # so aria2 connection in disconnected!
            # lets try to reconnect aria 5 times!
            for i in range(5):
                answer = download.startAria()  # start aria2
                if answer == 'did not respond' and i != 4:  # check answer
                    sleep(2)
                else:
                    break
                    # emit answer. 
                    # if answer is 'did not respond', it means that reconnecting aria was not successful
                    self.RECONNECTARIASIGNAL.emit(str(answer))



# SpiderThread calls spider in spider.py .
# spider finds file size and file name of download file .
# spider works similiar to spider in wget.
class SpiderThread(QThread):
    SPIDERSIGNAL = pyqtSignal()
    def __init__(self, add_link_dictionary, parent):
        QThread.__init__(self)
        self.add_link_dictionary = add_link_dictionary
        self.parent = parent

    def run(self):
        try:
            # get file_name and file size with spider
            file_name, size = spider.spider(self.add_link_dictionary)

            # update data base
            dict = {'file_name': file_name, 'size': size, 'gid': self.add_link_dictionary['gid']}
            self.parent.persepolis_db.updateDownloadTable([dict])

        except:
            # write ERROR message
            print("Spider couldn't find download information")
            logger.sendToLog(
                "Spider couldn't find download information", "ERROR")

# this thread sending download request to aria2


class DownloadLink(QThread):
    ARIA2NOTRESPOND = pyqtSignal()

    def __init__(self, gid, parent):
        QThread.__init__(self)
        self.gid = gid
        self.parent = parent

    def run(self):
        # if request is not successful then persepolis is checking rpc
        # connection whith download.aria2Version() function
        answer = download.downloadAria(self.gid, self.parent)
        if not(answer):
            version_answer = download.aria2Version()

            # TODO version_answer must be changed to True or false or None and version number
            if version_answer == 'did not respond':
                self.ARIA2NOTRESPOND.emit()


# this thread is managing queue and sending download request to aria2
class Queue(QThread):
    # this signal emited when download status of queue changes to stop
    REFRESHTOOLBARSIGNAL = pyqtSignal(str)

    def __init__(self, category, start_time, end_time, parent):
        QThread.__init__(self)
        self.category = str(category)
        self.parent = parent
        self.start_time = start_time
        self.end_time = end_time

    def run(self):
        self.start = True
        self.stop = False
        self.limit = False
        self.limit_changed = False
        self.after = False
        self.break_for_loop = False

        queue_counter = 0 

        # queue repeats 5 times!
        # and everty time loads queue list again!
        # It is helps for checking new downloads in queue
        # and retrying failed downloads.
        for counter in range(5): 
            # read downloads information from data base
            download_table_dict = self.parent.persepolis_db.returnItemsInDownloadTable(self.category)
            category_table_dict = self.parent.persepolis_db.searchCategoryInCategoryTable(self.category)

            gid_list = category_table_dict['gid_list']

            # sort downloads top to the bottom of the list OR bottom to the top
            if not(self.parent.reverse_checkBox.isChecked()):
                gid_list.reverse()

            # check that if user set start time
            if self.start_time and counter == 0:  
                # find first download
                # set start time for first download in queue
                # status of first download must not be compelete
                for gid in gid_list:

                    # get download information dictionary
                    dict = download_table_dict[gid]

                    # find status of download
                    status = dict['status']

                    if status != 'complete':  
                        # We find first item! GREAT!
                        add_link_dict = {'gid': gid}
                            
                        # set start_time for this download
                        add_link_dict['start_time'] = self.start_time

                        # write changes in data base
                        self.parent.persepolis_db.updateAddLinkTable([new_dict])

                        # delete add_link_dict
                        del add_link_dict

                        # job is done! break the loop
                        break

            
            for gid in gid_list:

                add_link_dict = {'gid': gid}

                # find download information
                dict = download_table_dict[gid]

                # if download was completed, continue the loop
                # with the next iteration of the loop!
                # We don't want to download it two times :)
                if dict['status'] == 'complete':
                    continue
                
                queue_counter = queue_counter + 1

                # change status of download to waiting
                status = 'waiting'
                dict['status'] = status

                if self.end_time:  
                    # it means user was set end time for download
                    # set end_hour and end_minute
                    add_link_dict['end_time'] = self.end_time

                # user can set sleep time between download items in queue.
                #see preferences window!
                # find wait_queue value
                wait_queue_list = self.parent.persepolis_setting.value('settings/wait-queue') 
                wait_queue_hour = int(wait_queue_list[0])
                wait_queue_minute = int(wait_queue_list[1])

                # check if user set sleep time between downloads in queue in setting window.
                # if queue_counter is 1 , it means we are in the first download item in queue.
                # and no need to wait for first item.
                if (wait_queue_hour != 0 or wait_queue_minute != 0) and queue_counter != 1:  
                    now_time_hour = int(time.strftime("%H"))
                    now_time_minute = int(time.strftime("%M"))
                    now_time_second = int(time.strftime("%S"))
                        
                    # add extra minute if we are in seond half of minute
                    if now_time_second > 30:
                        now_time_minute = now_time_minute + 1

                    # hour value can not be more than 23 and minute value can not be more than 59.
                    sigma_minute = wait_queue_minute + now_time_minute
                    sigma_hour = wait_queue_hour + now_time_hour
                    if sigma_minute > 59:
                        sigma_minute = sigma_minute - 60
                        sigma_hour = sigma_hour + 1

                    if sigma_hour > 23:
                        sigma_hour = sigma_hour - 24

                    # setting sigma_hour and sigma_minute for download's start time!
                    add_link_dict['start_time'] = str(sigma_hour + ':' + sigma_minute)

                # write changes in data base 
                self.parent.persepolis_db.updateAddLinkTable([add_link_dict])

                # delete add_link_dict
                del add_link_dict

                # start new thread for download
                new_download = DownloadLink(gid, self.parent)
                self.parent.threadPool.append(new_download)
                self.parent.threadPool[len(self.parent.threadPool) - 1].start()
                self.parent.threadPool[len(
                    self.parent.threadPool) - 1].ARIA2NOTRESPOND.connect(self.parent.aria2NotRespond)
                sleep(3)

                # limit download speed if user limited speed for previous download
                if self.limit:  
                    self.limit_changed = True

                # continue loop until download has finished
                while status == 'downloading' or status == 'waiting' or status == 'paused' or status == 'scheduled':

                    sleep(1)
                    dict = self.parent.persepolis_db.searchGidInDownloadTable(gid)

                    status = dict['status'] 

                    if status == 'error':
                        if 'error' in dict.keys():
                            error = str(dict['error'])
                        else:
                            error = 'error'

                        # write error_message in log file
                        error_message = 'Download failed - GID : '\
                                    + str(gid)\
                                    + '/nMessage : '\
                                    + error
                            
                        logger.sendToLog(error_message, 'ERROR')

                    elif status == 'complete':
                        compelete_message = 'Download complete - GID : '\
                                    + str(gid)

                        # write in log the compelete_message
                        logger.sendToLog(compelete_message, 'INFO')


                    if self.stop:  
                        # it means user stopped queue
                        answer = download.downloadStop(gid, self.parent)

                        # if aria2 did not respond , then this function is checking
                        # for aria2 availability , and if aria2 disconnected then
                        # aria2Disconnected is executed
                        if answer == 'None':
                            version_answer = download.aria2Version()
                            if version_answer == 'did not respond':
                                self.parent.aria2Disconnected()
                        status = 'stopped'
                    
                    if self.limit and status == 'downloading' and self.limit_changed:
                        # It means user want to limit download speed
                        # get limitation value
                        self.limit_comboBox_value = self.parent.limit_comboBox.currentText()
                        self.limit_spinBox_value = self.parent.limit_spinBox.value()
                        if self.limit_comboBox_value == "KB/S":
                            limit = str(self.limit_spinBox_value) + str("K")
                        else:
                            limit = str(self.limit_spinBox_value) + str("M")

                        # apply limitation
                        download.limitSpeed(gid, limit)

                        # done!
                        self.limit_changed = False

                    if not(self.limit) and status == 'downloading' and self.limit_changed:
                        # speed limitation is canceled by user!
                        # cancel limitation
                        download.limitSpeed(gid, "0")

                        # done!
                        self.limit_changed = False

                if status == 'stopped':  
                    # it means queue stopped at end time or user stopped queue

                    if self.stop and self.after:
                        # It means user activated shutdown before and now user
                        # stopped queue . so after download must be canceled
                        self.parent.after_checkBox.setChecked(False)

                    self.stop = True
                    self.limit = False
                    self.limit_changed = False

                    # it means that break outer "for" loop
                    self.break_for_loop = True  

                    if str(self.parent.category_tree.currentIndex().data()) == str(self.category):
                        self.REFRESHTOOLBARSIGNAL.emit(self.category)

                    # show notification
                    notifySend("Persepolis", "Queue Stopped!", 10000,
                               'no', systemtray=self.parent.system_tray_icon)

                    # write message in log
                    logger.sendToLog('Queue stopped', 'INFO')

                    break

            if self.break_for_loop:
                break

        if self.start:  
            # if queue finished :
            self.start = False

            # this section is sending shutdown signal to the shutdown script(if user
            # select shutdown for after download)
            if self.after:
                # shutdown aria2c
                answer = download.shutDown()

                # KILL aria2c if didn't respond. R.I.P :))
                if not(answer) and (os_type != 'Windows'):
                    os.system('killall aria2c')

                shutdown_file = os.path.join(
                    persepolis_tmp, 'shutdown', self.category)

                # write 'shutdown' word in shutdown file
                # see shutdown.py for more information.
                f = Open(shutdown_file, 'w')
                f.writelines('shutdown')
                f.close()

                # show a notification about system is shutting down now!
                notifySend('Persepolis is shutting down', 'your system in 20 seconds',
                           15000, 'warning', systemtray=self.parent.system_tray_icon)

            # show notification for queue completion
            notifySend("Persepolis", 'Queue completed!', 10000,
                       'queue', systemtray=self.parent.system_tray_icon)

            # write a message in log
            logger.sendToLog('Queue completed', 'INFO')

            self.stop = True
            self.limit = False
            self.limit_changed = False
            self.after = False

            if str(self.parent.category_tree.currentIndex().data()) == str(self.category):
                self.REFRESHTOOLBARSIGNAL.emit(self.category)


# CheckingThread have 2 duty!
# 1-this class is checking that if user add a link with browsers plugin.
# 2-assume that user executed program before .
# if user is clicking on persepolis icon in menu this tread emits SHOWMAINWINDOWSIGNAL
class CheckingThread(QThread):
    CHECKPLUGINDBSIGNAL = pyqtSignal()
    SHOWMAINWINDOWSIGNAL = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)

    def run(self):
        global shutdown_notification
        global plugin_links_checked

# shutdown_notification = 0 >> persepolis is running 
# 1 >> persepolis is ready for closing(closeEvent called) 
# 2 >> OK, let's close application!

        while shutdown_notification == 0 and aria_startup_answer != 'ready':
            sleep(2)

        while shutdown_notification == 0:

            # it means , user clicked on persepolis icon and persepolis is
            # still running. see persepolis file for more details.
            if os.path.isfile(show_window_file):
                # OK! we catch notification! remove show_window_file now!
                osCommands.remove(show_window_file)

                # emit a singnal to notify MainWindow for showing itself!
                self.SHOWMAINWINDOWSIGNAL.emit()

            # It means new browser plugin call is available!
            if os.path.isfile(plugin_ready):

                # OK! We catch notification! remove plugin_ready file
                osCommands.remove(plugin_ready)

                # When checkPluginCall method considered request , then
                # plugin_links_checked is changed to True
                plugin_links_checked = False
                self.CHECKPLUGINDBSIGNAL.emit()  # notifiying that we have flashgot request
                while plugin_links_checked != True:  # wait for persepolis consideration!
                    sleep(0.5)


# if checking_flag is equal to 1, it means that user pressed remove or delete button or ... . so checking download information must be stopped until job is done!
# this thread checks checking_flag and when checking_flag changes to 2
# QTABLEREADY signal is emmited
class WaitThread(QThread):
    QTABLEREADY = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)

    def run(self):
        global checking_flag
        checking_flag = 1
        while checking_flag != 2:
            sleep(0.05)
        self.QTABLEREADY.emit()

# button_pressed_counter changed if user pressed move up and move down and ... actions
# this thread is changing checking_flag to zero if button_pressed_counter
# don't change for 2 seconds


class ButtonPressedThread(QThread):
    def __init__(self):
        QThread.__init__(self)

    def run(self):
        global checking_flag
        current_button_pressed_value = deepcopy(button_pressed_counter) + 1
        while current_button_pressed_value != button_pressed_counter:
            current_button_pressed_value = deepcopy(button_pressed_counter)
            sleep(2)
# job is done!
        checking_flag = 0


class ShutDownThread(QThread):
    def __init__(self, gid, password=None):
        QThread.__init__(self)
        self.gid = gid
        self.password = password

    def run(self):
        shutDown(self.gid, self.password)


# this thread is keeping system awake! because if system sleeps , then internet connection is disconnected!
# stxariategy is simple! a loop is checking mouse position every 20 seconds. 
# if mouse position didn't change, cursor is moved by QCursor.setPos() (see keepAwake method) ! so this is keeping system awake! 
# 
class KeepAwakeThread(QThread):

    KEEPSYSTEMAWAKESIGNAL = pyqtSignal(bool)

    def __init__(self):
        QThread.__init__(self)

    def run(self):
        while True:

            while shutdown_notification == 0 and aria_startup_answer != 'ready':
                sleep(1)

            old_cursor_array = [0, 0]
            add = True

            while shutdown_notification != 1:
                sleep(20)

                # finding cursor position
                cursor_position = QCursor.pos()
                new_cursor_array = [int(cursor_position.x()) , int(cursor_position.y())]

                if new_cursor_array == old_cursor_array : 
                # So cursor position didn't change for 60 second.
                    if add : # Moving mouse position one time +10 pixel and one time -10 pixel! 
                        self.KEEPSYSTEMAWAKESIGNAL.emit(add)
                        add = False
                    else:
                        self.KEEPSYSTEMAWAKESIGNAL.emit(add)
                        add = True

                old_cursor_array = new_cursor_array

 

class MainWindow(MainWindow_Ui):
    def __init__(self, start_in_tray, persepolis_main, persepolis_setting):
        super().__init__(persepolis_setting)
        self.persepolis_setting = persepolis_setting
        self.persepolis_main = persepolis_main
        global icons
        icons = ':/' + \
            str(self.persepolis_setting.value('settings/icons')) + '/'


# system_tray_icon
        self.system_tray_icon = QSystemTrayIcon()
        self.system_tray_icon.setIcon(
            QIcon.fromTheme('persepolis', QIcon(':/persepolis.svg')))

        # menu of system tray icon
        system_tray_menu = QMenu()
        system_tray_menu.addAction(self.addlinkAction)
        system_tray_menu.addAction(self.stopAllAction)
        system_tray_menu.addAction(self.minimizeAction)
        system_tray_menu.addAction(self.exitAction)
        self.system_tray_icon.setContextMenu(system_tray_menu)

        # if system tray icon pressed: 
        self.system_tray_icon.activated.connect(self.systemTrayPressed)

        # show system_tray_icon
        self.system_tray_icon.show()

        # check trayAction
        self.trayAction.setChecked(True)

        # set tooltip for system_tray_icon
        self.system_tray_icon.setToolTip('Persepolis Download Manager')

        # check user preference for showing or hiding system_tray_icon
        if self.persepolis_setting.value('settings/tray-icon') != 'yes' and start_in_tray == 'no':
            self.minimizeAction.setEnabled(False)
            self.trayAction.setChecked(False)
            self.system_tray_icon.hide()

        # hide MainWindow if start_in_tray is equal to "yes"
        if start_in_tray == 'yes':
            self.minimizeAction.setText('Show main Window')
            self.minimizeAction.setIcon(QIcon(icons + 'window'))

        # check user preference for showing or hiding menubar.
        # (It's not for mac osx or DE that have global menu like kde plasma)
        if self.persepolis_setting.value('settings/show-menubar') == 'yes':
            self.menubar.show()
            self.showMenuBarAction.setChecked(True)
            self.toolBar2.hide()
        else:
            self.menubar.hide()
            self.showMenuBarAction.setChecked(False)
            self.toolBar2.show()

        if platform.system() == 'Darwin':
            self.showMenuBarAction.setEnabled(False)

        # check user preferences for showing or hiding sidepanel. 
        if self.persepolis_setting.value('settings/show-sidepanel') == 'yes':
            self.category_tree_qwidget.show()
            self.showSidePanelAction.setChecked(True)
        else:
            self.category_tree_qwidget.hide()
            self.showSidePanelAction.setChecked(False)


# set message for statusbar
        self.statusbar.showMessage('Please Wait ...')

        self.checkSelectedRow()


# list of threads
        self.threadPool = []

# start aria2 
        start_aria = StartAria2Thread()
        self.threadPool.append(start_aria)
        self.threadPool[0].start()
        self.threadPool[0].ARIA2RESPONDSIGNAL.connect(self.startAriaMessage)

# initializing
        # create an object for PluginsDB
        self.plugins_db = PluginsDB()

        # create an object for PersepolisDB
        self.persepolis_db = PersepolisDB()

        # check tables in data_base, and change required values to default value.
        # see data_base.py for more information.
        self.persepolis_db.setDBTablesToDefaultValue()

        # get queues name from data base
        queues_list = self.persepolis_db.categoriesList()

        #TODO adding 'Single Downloads' to category_db_table in data base
        # add queues to category_tree(left side panel)
        for category_name in queues_list:
            new_queue_category = QStandardItem(category_name)
            font = QtGui.QFont()
            font.setBold(True)
            new_queue_category.setFont(font)
            new_queue_category.setEditable(False)
            self.category_tree_model.appendRow(new_queue_category)

        
        # add download items to the download_table
        # read download items from data base
        download_table_dict = self.persepolis_db.returnItemsInDownloadTable()

        # read gid_list from date base
        category_dict = self.persepolis_db.searchCategoryInCategoryTable('All Downloads')
        gid_list = category_dict['gid_list']

        keys_list = ['file_name',
                    'status',
                    'size',
                    'downloaded_size',
                    'percent',
                    'connections',
                    'rate',
                    'estimate_time_left',
                    'gid',
                    'link',
                    'firs_try_date',
                    'last_try_date',
                    'category'
                    ]

        # insert items in download_table 
        for gid in gid_list:
            dict = download_table_dict[gid]
            i = 0
            for key in keys_list: 
                item = QTableWidgetItem(str(dict[key]))
                self.download_table.setItem(0, i, item)
                i = i + 1


# defining some lists and dictionaries for running addlinkwindows and
# propertieswindows and propertieswindows , ...
        self.addlinkwindows_list = []
        self.propertieswindows_list = []
        self.progress_window_list = []
        self.afterdownload_list = []
        self.text_queue_window_list = []
        self.about_window_list = []
        self.plugin_queue_window_list = []
        self.checkupdatewindow_list = []
        self.logwindow_list = []
        self.progress_window_list_dict = {}

# queue_list_dict contains queue threads >> queue_list_dict[name of queue]
        self.queue_list_dict = {}

# CheckDownloadInfoThread
        check_download_info = CheckDownloadInfoThread(self)
        self.threadPool.append(check_download_info)
        self.threadPool[1].start()
        self.threadPool[1].DOWNLOAD_INFO_SIGNAL.connect(self.checkDownloadInfo)
        self.threadPool[1].RECONNECTARIASIGNAL.connect(self.reconnectAria)

# CheckSelectedRowThread
        check_selected_row = CheckSelectedRowThread()
        self.threadPool.append(check_selected_row)
        self.threadPool[2].start()
        self.threadPool[2].CHECKSELECTEDROWSIGNAL.connect(
                                    self.checkSelectedRow)

# CheckingThread
        check_flashgot = CheckingThread()
        self.threadPool.append(check_flashgot)
        self.threadPool[3].start()
        self.threadPool[3].CHECKPLUGINDBSIGNAL.connect(self.checkPluginCall)
        self.threadPool[3].SHOWMAINWINDOWSIGNAL.connect(self.showMainWindow)

#######################################
# keepAwake
        keep_awake = KeepAwakeThread()
        self.threadPool.append(keep_awake)
        self.threadPool[len(self.threadPool) - 1].start()
        self.threadPool[len(self.threadPool) - 1].KEEPSYSTEMAWAKESIGNAL.connect(self.keepAwake)


# finding number or row that user selected!
        self.download_table.itemSelectionChanged.connect(self.selectedRow)


# if user  doubleclicks on an item in download_table , then openFile
# function  executes
        self.download_table.itemDoubleClicked.connect(self.openFile)

# connecting queue_panel_show_button to showQueuePanelOptions
        self.queue_panel_show_button.clicked.connect(
            self.showQueuePanelOptions)

# connecting start_checkBox to startFrame
        self.start_checkBox.toggled.connect(self.startFrame)
#         self.startFrame('menu')
        self.start_checkBox.setChecked(False)

# connecting end_checkBox to endFrame
        self.end_checkBox.toggled.connect(self.endFrame)
#         self.endFrame('menu')
        self.end_checkBox.setChecked(False)

# connecting after_checkBox to afterFrame
        self.after_checkBox.toggled.connect(self.afterFrame)
        self.after_checkBox.setChecked(False)

# connecting limit_checkBox to limitFrame
        self.limit_checkBox.toggled.connect(self.limitFrame)

# connecting limit_pushButton to limitPushButtonPressed
        self.limit_pushButton.clicked.connect(self.limitPushButtonPressed)

# connecting limit_comboBox and limit_spinBox to limitComboBoxChanged
        self.limit_comboBox.currentIndexChanged.connect(
            self.limitComboBoxChanged)
        self.limit_spinBox.valueChanged.connect(self.limitComboBoxChanged)

# connecting after_pushButton to afterPushButtonPressed
        self.after_pushButton.clicked.connect(self.afterPushButtonPressed)

# setting index of all downloads for category_tree
        global current_category_tree_index
        current_category_tree_index = self.category_tree_model.index(0, 0)
        self.category_tree.setCurrentIndex(current_category_tree_index)

# this line set toolBar And Context Menu Items
        self.toolBarAndContextMenuItems('All Downloads')

        # It will be enabled after aria2 startup!(see startAriaMessage method)
        # .This line added for solving crash problems on startup
        self.category_tree_qwidget.setEnabled(False)

# keep_awake_checkBox
        if str(self.persepolis_setting.value('settings/awake')) == 'yes':
            self.keep_awake_checkBox.setChecked(True)
        else:
            self.keep_awake_checkBox.setChecked(False)

        self.keep_awake_checkBox.toggled.connect(self.keepAwakeCheckBoxToggled)


# finding windows_size
        size = self.persepolis_setting.value(
            'MainWindow/size', QSize(900, 500))
        position = self.persepolis_setting.value(
            'MainWindow/position', QPoint(300, 300))

# setting window size
        self.resize(size)
        self.move(position)


# download_table column size
# column 0
        size = self.persepolis_setting.value(
            'MainWindow/column0', '300')
        self.download_table.setColumnWidth(0, int(size))
#column 1
        size = self.persepolis_setting.value(
            'MainWindow/column1', '100')
        self.download_table.setColumnWidth(1, int(size))
#column 2
        size = self.persepolis_setting.value(
            'MainWindow/column2', '100')
        self.download_table.setColumnWidth(2, int(size))
#column 3
        size = self.persepolis_setting.value(
            'MainWindow/column3', '120')
        self.download_table.setColumnWidth(3, int(size))
#column 4
        size = self.persepolis_setting.value(
            'MainWindow/column4', '100')
        self.download_table.setColumnWidth(4, int(size))
#column 5
        size = self.persepolis_setting.value(
            'MainWindow/column5', '120')
        self.download_table.setColumnWidth(5, int(size))
#column 6
        size = self.persepolis_setting.value(
            'MainWindow/column6', '100')
        self.download_table.setColumnWidth(6, int(size))
#column 7
        size = self.persepolis_setting.value(
            'MainWindow/column7', '100')
        self.download_table.setColumnWidth(7, int(size))
#column 10
        size = self.persepolis_setting.value(
            'MainWindow/column10', '200')
        self.download_table.setColumnWidth(10, int(size))
#column 11
        size = self.persepolis_setting.value(
            'MainWindow/column11', '200')
        self.download_table.setColumnWidth(11, int(size))
#column 12
        size = self.persepolis_setting.value(
            'MainWindow/column11', '200')
        self.download_table.setColumnWidth(12, int(size))


        if str(self.persepolis_setting.value('settings/column0')) == 'yes':
            self.download_table.setColumnHidden(0, False)
        else:
            self.download_table.setColumnHidden(0, True)

        if str(self.persepolis_setting.value('settings/column1')) == 'yes':
            self.download_table.setColumnHidden(1, False)
        else:
            self.download_table.setColumnHidden(1, True)

        if str(self.persepolis_setting.value('settings/column2')) == 'yes':
            self.download_table.setColumnHidden(2, False)
        else:
            self.download_table.setColumnHidden(2, True)

        if str(self.persepolis_setting.value('settings/column3')) == 'yes':
            self.download_table.setColumnHidden(3, False)
        else:
            self.download_table.setColumnHidden(3, True)

        if str(self.persepolis_setting.value('settings/column4')) == 'yes':
            self.download_table.setColumnHidden(4, False)
        else:
            self.download_table.setColumnHidden(4, True)

        if str(self.persepolis_setting.value('settings/column5')) == 'yes':
            self.download_table.setColumnHidden(5, False)
        else:
            self.download_table.setColumnHidden(5, True)

        if str(self.persepolis_setting.value('settings/column6')) == 'yes':
            self.download_table.setColumnHidden(6, False)
        else:
            self.download_table.setColumnHidden(6, True)

        if str(self.persepolis_setting.value('settings/column7')) == 'yes':
            self.download_table.setColumnHidden(7, False)
        else:
            self.download_table.setColumnHidden(7, True)

        if str(self.persepolis_setting.value('settings/column10')) == 'yes':
            self.download_table.setColumnHidden(10, False)
        else:
            self.download_table.setColumnHidden(10, True)

        if str(self.persepolis_setting.value('settings/column11')) == 'yes':
            self.download_table.setColumnHidden(11, False)
        else:
            self.download_table.setColumnHidden(11, True)

        if str(self.persepolis_setting.value('settings/column12')) == 'yes':
            self.download_table.setColumnHidden(12, False)
        else:
            self.download_table.setColumnHidden(12, True)


# check reverse_checkBox
        self.reverse_checkBox.setChecked(False)

# startAriaMessage function is showing some message on statusbar and
# sending notification when aria failed to start! see StartAria2Thread for
# more details
    def startAriaMessage(self, message):
        global aria_startup_answer
        if message == 'yes':
            sleep(0.5)
            self.statusbar.showMessage('Ready...')
            aria_startup_answer = 'ready'

            self.category_tree_qwidget.setEnabled(True)

        elif message == 'try again':
            self.statusbar.showMessage(
                "Aria2 didn't respond! be patient!Persepolis tries again in 2 seconds!")
            logger.sendToLog(
                "Aria2 didn't respond! be patient!Persepolis tries again in 2 seconds!",
                "WARNING") 

        else:
            self.statusbar.showMessage('Error...')
            notifySend('Persepolis can not connect to Aria2', 'Check your network & Restart Persepolis',
                       10000, 'critical', systemtray=self.system_tray_icon)
            logger.sendToLog('Persepolis can not connect to Aria2', 'ERROR')

            self.propertiesAction.setEnabled(True)
            self.category_tree_qwidget.setEnabled(True)

    def reconnectAria(self, message):
        # this function is executing if RECONNECTARIASIGNAL is emitted by CheckingThread .
        # if message is 'did not respond' then a message(Persepolis can not connect to Aria2) shown
        # if message is not 'did not respond' , it means that reconnecting
        # Aria2 was successful.
        if message == 'did not respond':
            self.statusbar.showMessage('Error...')
            notifySend('Persepolis can not connect to Aria2', 'Restart Persepolis',
                       10000, 'critical', systemtray=self.system_tray_icon)
            logger.sendToLog('Persepolis can not connect to Aria2', 'ERROR')
        else:
            self.statusbar.showMessage('Reconnecting aria2...')
            logger.sendToLog('Reconnecting Aria2 ...', 'INFO')

            #this section is checking download status of items in download table , if status is downloading then restarts this download.
            for row in range(self.download_table.rowCount()):
                status_download_table = str(self.download_table.item( row , 1 ).text())
                gid = self.download_table.item( row , 8).text()

                if status_download_table == 'downloading':
                    new_download = DownloadLink(gid, self)
                    self.threadPool.append(new_download)
                    self.threadPool[len(self.threadPool) - 1].start()
                    self.threadPool[len(
                        self.threadPool) - 1].ARIA2NOTRESPOND.connect(self.aria2NotRespond)

            # if status is paused , then this section is stopping download.
                if status_download_table == 'paused':
                    download.downloadStop(gid, self)

            self.statusbar.showMessage(
                'Persepolis reconnected aria2 successfully')
            logger.sendToLog('Persepolis reconnected aria2 successfully', 'INFO')

# when this function is called , aria2_disconnected value is changing to
# 1! and it means that aria2 rpc connection disconnected.so CheckingThread
# is trying to fix it .
    def aria2Disconnected(self):
        global aria2_disconnected
        aria2_disconnected = 1


# read KeepAwakeThread for more information
    def keepAwake(self, add):
        # finding cursor position
        cursor_position = QCursor.pos()
        cursor_array = [int(cursor_position.x()) , int(cursor_position.y())]

        print(self.persepolis_setting.value('settings/awake'))
        if self.persepolis_setting.value('settings/awake') == 'yes':
            if add == True and self.keep_awake_checkBox.isChecked() == True: # Moving mouse position one time +1 pixel and one time -1 pixel! 
                QCursor.setPos(cursor_array[0] + 1, cursor_array[1] + 1)
            else:
                QCursor.setPos(cursor_array[0] - 1, cursor_array[1] - 1)

# if keep_awake_checkBox toggled by user , this method is called.
    def keepAwakeCheckBoxToggled(self, checkbox):
        if self.keep_awake_checkBox.isChecked():
            self.persepolis_setting.setValue('settings/awake', 'yes')
            self.keep_awake_checkBox.setChecked(True)
        else:
            self.persepolis_setting.setValue('settings/awake', 'no')
            self.keep_awake_checkBox.setChecked(False)

        self.persepolis_setting.sync()


# this method updates download_table in MainWindow
#
# download_table_header = ['File Name', 'Status', 'Size', 'Downloaded', 'Percentage', 'Connections',
#                       'Transfer rate', 'Estimate time left', 'Gid', 'Link', 'First try date', 'Last try date', 'Category']

    def checkDownloadInfo(self, list):
    for dict in list:
        gid = dict['gid']


# find row of this gid in download_table!
        row = None
        for i in range(self.download_table.rowCount()):
            row_gid = self.download_table.item(i, 8).text()
            if gid == row_gid:
                row = i
                break

# check that if user checked selection mode from edit menu
        if self.selectAction.isChecked():
            selection = 'actived'
        else:
            selection = None

# updat download_table items
        if row != None:
            update_list = [dict['file_name'], dict['status'], dict['size'], dict['downloaded_size'], dict['percent'], 
                            dict['connections'], dict['rate'], dict['estimate_time_left'], dict['gid'], None, None, None, None]
            for i in range(12):

                # update download_table cell if update_list item in not None
                if update_list[i]:
                    text = update_list[i]
                else:
                    text = self.download_table.item(row, i).text()

                # create a QTableWidgetItem
                item = QTableWidgetItem(text)

                # add checkbox to first cell in row , if user checked selection mode
                if i == 0 and selection != None:
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                              QtCore.Qt.ItemIsEnabled)
                    # 2 means that user checked item before
                if self.download_table.item(row, i).checkState() == 2:
                    # if user checked row before , check it again
                    item.setCheckState(QtCore.Qt.Checked)
                else:
                    # if user didn't checked row then don't check it!
                    item.setCheckState(QtCore.Qt.Unchecked)
# set item
                try:
                    self.download_table.setItem(row, i, item)
                except Exception as problem:
                    print('updating download_table was unsuccessful\nError is :')
                    print(problem)
                    logger.sendToLog(
                        "Error occured while updating download table", "INFO")
                    logger.sendToLog(problem, "ERROR")

# update download_table (refreshing!)
            self.download_table.viewport().update()


# update progresswindow labels
            # check that any progress_window is available for this gid or not!
        if gid in self.progress_window_list_dict.keys():

            # find progress_window for this gid
            member_number = self.progress_window_list_dict[gid]
            progress_window = self.progress_window_list[member_number]

            # link
            link = "<b>Link</b> : " + str(dict['link'])
            progress_window.link_label.setText(link)
            progress_window.link_label.setToolTip(link)

            # downloaded
            downloaded = "<b>Downloaded</b> : " \
                        + str(dict['downloaded']) \
                        + "/" \
                        + str(dict['size'])

            progress_window.downloaded_label.setText(downloaded)

            # Transfer rate
            rate = "<b>Transfer rate</b> : " \
                    + str(dict['rate'])

            progress_window.rate_label.setText(rate)

            # Estimate time left
            estimate_time_left = "<b>Estimate time left</b> : " \
                                + str(dict['estimate_time_left'])

            progress_window.time_label.setText(estimate_time_left)

            # Connections
            connections = "<b>Connections</b> : " \
                            + str(dict['connections'])

            progress_window.connections_label.setText(connections)

            # progressbar
            value = dict['percent']
            file_name = str(dict['file_name'])

            if file_name != "***":
                windows_title = '(' + str(value) + ')' + str(file_name)
                progress_window.setWindowTitle(windows_title)
            try:
                value = int(value[:-1])
            except:
                value = 0
            progress_window.download_progressBar.setValue(value)


            # status
            progress_window.status = str(dict['status'])
            status = "<b>Status</b> : " + progress_window.status
            progress_window.status_label.setText(status)

            # active/deactive progress_window buttons according to status
            if progress_window.status == "downloading":
                progress_window.resume_pushButton.setEnabled(False)
                progress_window.stop_pushButton.setEnabled(True)
                progress_window.pause_pushButton.setEnabled(True)

            elif progress_window.status == "paused":
                progress_window.resume_pushButton.setEnabled(True)
                progress_window.stop_pushButton.setEnabled(True)
                progress_window.pause_pushButton.setEnabled(False)

            elif progress_window.status == "waiting":
                progress_window.resume_pushButton.setEnabled(False)
                progress_window.stop_pushButton.setEnabled(True)
                progress_window.pause_pushButton.setEnabled(False)

            elif progress_window.status == "scheduled":
                progress_window.resume_pushButton.setEnabled(False)
                progress_window.stop_pushButton.setEnabled(True)
                progress_window.pause_pushButton.setEnabled(False)

            # it means download has finished!
            # lets do finishing jobs!
            elif progress_window.status == "stopped" or progress_window.status == "error" or progress_window.status == "complete":

                # close progress_window if download status is stopped or
                # completed or error
                progress_window.destroy()  # close window!

                # eliminate window information! in progress_window_list
                # and progress_window_list_dict
                self.progress_window_list[member_number] = []
                del self.progress_window_list_dict[gid]

                # if download stopped:
                if progress_window.status == "stopped":
                    # write message in log
                    stop_message = 'Download stoped - GID : '\
                                    + str(gid)

                    logger.sendToLog(stop_message, 'INFO')

                    # show notification
                    notifySend("Download Stopped",
                            str(dict['file_name']), 10000, 'no', systemtray=self.system_tray_icon)


                # if download status is error!
                elif progress_window.status == "error":

                    # get error message from dict
                    if 'error' in dict.keys():
                        error = dict['error']
                    else:
                        error = 'Error'

                    # write error_message in log file
                    error_message = 'Download failed - GID : '\
                                + str(gid)\
                                + '/nMessage : '\
                                + error)

                    logger.sendToLog(error_message, 'ERROR')

                    # show notification
                    notifySend("Error - " + error, str(dict['file_name'],
                                10000, 'fail', systemtray=self.system_tray_icon)

                # set "None" for start_time and end_time and after_download value 
                # in data_base, because download has finished
                self.persepolis_db.setDefaultGidInAddlinkTable(gid, start_time = True, end_time = True, after_download = True)


                # if user selectes shutdown option after download progress 
                # a file(shutdown_file) will be created with the name of gid in
                # this folder "persepolis_tmp/shutdown/"
                # and "wait" word will be written in this file.
                # (see ShutDownThread and shutdown.py for more information)
                # shutDown methode is checking that file every second .
                # when "wait" changes to "shutdown" in that file then script is
                # shutting down system
                shutdown_file = os.path.join(
                        persepolis_tmp, 'shutdown', gid)

                # if status is complete or error, and user selected "shutdown after downoad" option:
                if os.path.isfile(shutdown_file) and progress_window.status != 'stopped':

                    # shutdown aria!
                    answer = download.shutDown()

                    # KILL aria2c in Unix like systems, if didn't respond. R.I.P :))
                    if not(answer) and (os_type != 'Windows'):
                        os.system('killall aria2c')

                    # send notification
                    notifySend('Persepolis is shutting down', 'your system in 20 seconds',
                               15000, 'warning', systemtray=self.system_tray_icon)

                    # write "shutdown" message in shutdown_file >> Shutdown system!
                    # send shutdown signal to the shutdown script(if user
                    # selected shutdown for after download)
                    f = Open(shutdown_file, 'w')
                    f.writelines('shutdown')
                    f.close()

                # if download stopped and user selected "shutdown after download" option:
                elif os.path.isfile(shutdown_file) == True and progress_window.status == 'stopped':
                    # write "canceled" message in shutdown_file >> cancel shutdown operation!
                    f = Open(shutdown_file, 'w')
                    f.writelines('canceled')
                    f.close()

                # sync persepolis_setting before checking!
                self.persepolis_setting.sync()
                if progress_window.status == "complete":
                    # write message in log file
                    compelete_message = 'Download compelete - GID : '\
                                        + str(gid)

                    logger.sendToLog(compelete_message, 'INFO')

                    # play notification
                    notifySend("Download Complete", dict['file_name'],
                                        10000, 'ok', systemtray=self.system_tray_icon)

                    # check user's Preferences
                    if self.persepolis_setting.value('settings/after-dialog') == 'yes':

                        # show download compelete dialog
                        afterdownloadwindow = AfterDownloadWindow(
                                download_info_file_list, self.persepolis_setting)
                        self.afterdownload_list.append(afterdownloadwindow)
                        self.afterdownload_list[len(
                            self.afterdownload_list) - 1].show()

                        # bringing AfterDownloadWindow on top
                        self.afterdownload_list[len(
                            self.afterdownload_list) - 1].raise_()
                        self.afterdownload_list[len(
                            self.afterdownload_list) - 1].activateWindow()



# drag and drop for links
    def dragEnterEvent(self, droplink):

        text = str(droplink.mimeData().text())

        if ("tp:/" in text[2:6]) or ("tps:/" in text[2:7]):
            droplink.accept()
        else:
            droplink.ignore()

    def dropEvent(self, droplink):
        link_clipborad = QApplication.clipboard()
        link_clipborad.clear(mode=link_clipborad.Clipboard)
        link_string = droplink.mimeData().text()
        link_clipborad.setText(str(link_string), mode=link_clipborad.Clipboard)
        self.addLinkButtonPressed(button=link_clipborad)

# aria2 identifies each download by the ID called GID.
# The GID must be hex string of 16 characters,
# thus [0-9a-zA-Z] are allowed and leading zeros must 
# not be stripped. The GID all 0 is reserved and must
# not be used. The GID must be unique, otherwise error 
# is reported and the download is not added.
# gidGenerator generates GID for downloads
    def gidGenerator(self):
        return_list = True
        # this loop repeats until we have a unique GID
        while return_list:

        # generate a random hex value between 1152921504606846976 and 18446744073709551615
        # for download GID
            my_gid = hex(random.randint(1152921504606846976, 18446744073709551615))
            my_gid = my_gid[2:18]
            my_gid = str(my_gid)

        # check my_gid used before or not!
            return_list = self.persepolis_db.searchGidInDownloadTable(my_gid)

        return my_gid

# this method returns number of selected row
# and shows download link on statusbar.
    def selectedRow(self):
        try:
            # find selected item
            item = self.download_table.selectedItems()

            selected_row_return = self.download_table.row(item[1])

            # show link on statusbar
            link = self.download_table.item(
                selected_row_return, 9).text()
            self.statusbar.showMessage(str(link))

        except:
            selected_row_return = None

        return selected_row_return

# this method actives/deactives QActions according to selected row!
    def checkSelectedRow(self):
        try:
            # find row number
            item = self.download_table.selectedItems()
            selected_row_return = self.download_table.row(item[1])
        except:
            selected_row_return = None

        if selected_row_return:
            status = self.download_table.item(selected_row_return, 1).text()
            category = self.download_table.item(selected_row_return, 12).text()

            if category == 'Single Downloads':
                if status == "scheduled":
                    self.resumeAction.setEnabled(False)
                    self.pauseAction.setEnabled(False)
                    self.stopAction.setEnabled(True)
                    self.removeAction.setEnabled(False)
                    self.propertiesAction.setEnabled(False)
                    self.progressAction.setEnabled(True)
                    self.openDownloadFolderAction.setEnabled(False)
                    self.openFileAction.setEnabled(False)
                    self.deleteFileAction.setEnabled(False)

                elif status == "stopped" or status == "error":
                    self.stopAction.setEnabled(False)
                    self.pauseAction.setEnabled(False)
                    self.resumeAction.setEnabled(True)
                    self.removeAction.setEnabled(True)
                    self.propertiesAction.setEnabled(True)
                    self.progressAction.setEnabled(False)
                    self.openDownloadFolderAction.setEnabled(False)
                    self.openFileAction.setEnabled(False)
                    self.deleteFileAction.setEnabled(False)

                elif status == "downloading":
                    self.resumeAction.setEnabled(False)
                    self.pauseAction.setEnabled(True)
                    self.stopAction.setEnabled(True)
                    self.removeAction.setEnabled(False)
                    self.propertiesAction.setEnabled(False)
                    self.progressAction.setEnabled(True)
                    self.openDownloadFolderAction.setEnabled(False)
                    self.openFileAction.setEnabled(False)
                    self.deleteFileAction.setEnabled(False)

                elif status == "waiting":
                    self.stopAction.setEnabled(True)
                    self.resumeAction.setEnabled(False)
                    self.pauseAction.setEnabled(False)
                    self.removeAction.setEnabled(False)
                    self.propertiesAction.setEnabled(False)
                    self.progressAction.setEnabled(True)
                    self.openDownloadFolderAction.setEnabled(False)
                    self.openFileAction.setEnabled(False)
                    self.deleteFileAction.setEnabled(False)

                elif status == "complete":
                    self.stopAction.setEnabled(False)
                    self.resumeAction.setEnabled(False)
                    self.pauseAction.setEnabled(False)
                    self.removeAction.setEnabled(True)
                    self.propertiesAction.setEnabled(True)
                    self.progressAction.setEnabled(False)
                    self.openDownloadFolderAction.setEnabled(True)
                    self.openFileAction.setEnabled(True)
                    self.deleteFileAction.setEnabled(True)

                elif status == "paused":
                    self.stopAction.setEnabled(True)
                    self.resumeAction.setEnabled(True)
                    self.pauseAction.setEnabled(False)
                    self.removeAction.setEnabled(False)
                    self.propertiesAction.setEnabled(False)
                    self.progressAction.setEnabled(True)
                    self.openDownloadFolderAction.setEnabled(False)
                    self.openFileAction.setEnabled(False)
                    self.deleteFileAction.setEnabled(False)

                else:
                    self.progressAction.setEnabled(False)
                    self.resumeAction.setEnabled(False)
                    self.stopAction.setEnabled(False)
                    self.pauseAction.setEnabled(False)
                    self.removeAction.setEnabled(False)
                    self.propertiesAction.setEnabled(False)
                    self.openDownloadFolderAction.setEnabled(False)
                    self.openFileAction.setEnabled(False)
                    self.deleteFileAction.setEnabled(False)

            else:

                if status == 'complete':
                    self.stopAction.setEnabled(False)
                    self.resumeAction.setEnabled(False)
                    self.pauseAction.setEnabled(False)
                    self.removeAction.setEnabled(True)
                    self.propertiesAction.setEnabled(True)
                    self.progressAction.setEnabled(False)
                    self.openDownloadFolderAction.setEnabled(True)
                    self.openFileAction.setEnabled(True)
                    self.deleteFileAction.setEnabled(True)

                elif status == "stopped" or status == "error":
                    self.stopAction.setEnabled(False)
                    self.pauseAction.setEnabled(False)
                    self.resumeAction.setEnabled(False)
                    self.removeAction.setEnabled(True)
                    self.propertiesAction.setEnabled(True)
                    self.progressAction.setEnabled(False)
                    self.openDownloadFolderAction.setEnabled(False)
                    self.openFileAction.setEnabled(False)
                    self.deleteFileAction.setEnabled(False)

                elif status == "scheduled" or status == "downloading" or status == "paused" or status == "waiting":
                    self.resumeAction.setEnabled(False)
                    self.pauseAction.setEnabled(False)
                    self.stopAction.setEnabled(False)
                    self.removeAction.setEnabled(False)
                    self.propertiesAction.setEnabled(False)
                    self.progressAction.setEnabled(False)
                    self.openDownloadFolderAction.setEnabled(False)
                    self.openFileAction.setEnabled(False)
                    self.deleteFileAction.setEnabled(False)

        else:
            self.progressAction.setEnabled(False)
            self.resumeAction.setEnabled(False)
            self.stopAction.setEnabled(False)
            self.pauseAction.setEnabled(False)
            self.removeAction.setEnabled(False)
            self.propertiesAction.setEnabled(False)
            self.openDownloadFolderAction.setEnabled(False)
            self.openFileAction.setEnabled(False)
            self.deleteFileAction.setEnabled(False)


# when user requests calls persepolis with browser plugin,
# this method is called by CheckingThread.
    def checkPluginCall(self):
        global plugin_links_checked

        # get new links from plugins_db
        list_of_links = self.plugins_db.returnNewLinks() 

        # notify that job is done!and new links can be received form plugins_db 
        plugin_links_checked = True

        if len(list_of_links) == 1:  # It means we have only one link in list_of_links

            # this line calls pluginAddLink method and send a dictionary that contains
            # link information
            self.pluginAddLink(list_of_links[0])

        else:  # we have queue request from browser plugin
            self.pluginQueue(list_of_links)


# this method creates an addlinkwindow when user calls Persepolis whith
# browsers plugin (Single Download)
    def pluginAddLink(self, add_link_dictionary):
        # create an object for AddLinkWindow and add it to addlinkwindows_list. 
        addlinkwindow = AddLinkWindow(
            self, self.callBack, self.persepolis_setting, add_link_dictionary)
        self.addlinkwindows_list.append(addlinkwindow)
        self.addlinkwindows_list[len(self.addlinkwindows_list) - 1].show()

        # bring addlinkwindow on top
        self.addlinkwindows_list[len(self.addlinkwindows_list) - 1].raise_()
        self.addlinkwindows_list[len(self.addlinkwindows_list) - 1].activateWindow()


# This method creates addlinkwindow when user presses plus button in MainWindow
    def addLinkButtonPressed(self, button):
        addlinkwindow = AddLinkWindow(self, self.callBack, self.persepolis_setting)
        self.addlinkwindows_list.append(addlinkwindow)
        self.addlinkwindows_list[len(self.addlinkwindows_list) - 1].show()

# callback of AddLinkWindow
    def callBack(self, add_link_dictionary, download_later, category):
        category = str(category)
        # aria2 identifies each download by the ID called GID. The GID must be
        # hex string of 16 characters.
        # if user presses ok button on add link window , a gid generates for download. 
        gid = self.gidGenerator()

        # add gid to add_link_dictionary
        add_link_dictionary['gid'] = gid

        # download_info_file_list is a list that contains ['file_name' ,
        # 'status' , 'size' , 'downloaded size' ,'download percentage' ,
        # 'number of connections' ,'Transfer rate' , 'estimate_time_left' ,
        # 'gid' , 'link' , 'firs_try_date' , 'last_try_date', 'category']

        # if user or flashgot defined filename then file_name is valid in
        # add_link_dictionary['out']
        if add_link_dictionary['out']:
            file_name = add_link_dictionary['out']
        else:
            file_name = '***'

        # If user selected a queue in add_link window , then download must be
        # added to queue and and download must be started with queue so >>
        # download_later = True
        if str(category) != 'Single Downloads':
            download_later = True 

        if not(download_later):
            status = 'waiting'
        else:
            status = 'stopped'

        # get now time and date
        date = download.nowDate()

        list = [file_name, status, '***', '***', '***',
                '***', '***', '***', gid, add_link_dictionary['link'], date, date, category]

        dict = {'file_name': file_name,
                'status': status,
                'size': '***',
                'downloaded_size': '***',
                'percent': '***',
                'connections': '***',
                'rate': '***',
                'estimate_time_left': '***',
                'gid': gid,
                'link': add_link_dictionary['link'],
                'firs_try_date': date, 
                'last_try_date': date,
                'category': category}

        # write information in data_base
        self.persepolis_db.insertInDownloadTable(dict)
        self.persepolis_db.insertInAddLinkTable(add_link_dictionary)
        

        # find selected category in left side panel
        for i in range(self.category_tree_model.rowCount()):
            category_tree_item_text = str(
                self.category_tree_model.index(i, 0).data())
            if category_tree_item_text == category:
                category_index = i
                break

        # highlight selected category in category_tree
        category_tree_model_index = self.category_tree_model.index(
            category_index, 0)
        self.category_tree.setCurrentIndex(category_tree_model_index)
        self.categoryTreeSelected(category_tree_model_index)

        # create a row in download_table for new download
        self.download_table.insertRow(0)
        j = 0
        # add item in list to the row
        for i in list:
            item = QTableWidgetItem(i)
            self.download_table.setItem(0, j, item)
            j = j + 1

        # add checkBox to the row , if user selected selectAction
        if self.selectAction.isChecked() == True:
            item = self.download_table.item(0, 0)
            item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                          QtCore.Qt.ItemIsEnabled)
            item.setCheckState(QtCore.Qt.Unchecked)

        # if user didn't press download_later_pushButton in add_link window
        # then create new qthread for new download!
        if not(download_later):
            new_download = DownloadLink(gid, self)
            self.threadPool.append(new_download)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].ARIA2NOTRESPOND.connect(self.aria2NotRespond)

        # open progress window for download.
            self.progressBarOpen(gid)

        # notifiy user 
            # check that download scheduled or not
            if not(add_link_dictionary['start_time']):
                message = "Download Starts"
            else:
                new_spider = SpiderThread(add_link_dictionary, self)
                self.threadPool.append(new_spider)
                self.threadPool[len(self.threadPool) - 1].start()
                message = "Download Scheduled"
            notifySend(message, '', 10000, 'no',
                       systemtray=self.system_tray_icon)

        else:
            new_spider = SpiderThread(add_link_dictionary, self)
            self.threadPool.append(new_spider)
            self.threadPool[len(self.threadPool) - 1].start()


# when user presses resume button this method is called
    def resumeButtonPressed(self, button):
        self.resumeAction.setEnabled(False)

        # find user's selected row
        selected_row_return = self.selectedRow()  

        if selected_row_return:
            # find download gid
            gid = self.download_table.item(selected_row_return, 8).text()
            download_status = self.download_table.item(
                selected_row_return, 1).text()

# this 'if' checks status of download before resuming! If download status
# is 'paused' then download must be resumed and if status isn't 'paused' new
# download thread must be created !
            if download_status == "paused":
                answer = download.downloadUnpause(gid)
# if aria2 did not respond , then this function checks for aria2
# availability , and if aria2 disconnected then aria2Disconnected is
# called. 
                if not(answer):
                    version_answer = download.aria2Version()
                    if version_answer == 'did not respond':
                        self.aria2Disconnected()
                        notifySend("Aria2 disconnected!", "Persepolis is trying to connect!be patient!",
                                   10000, 'warning', systemtray=self.system_tray_icon)
                    else:
                        notifySend("Aria2 did not respond!", "Try agian!",
                                   10000, 'warning', systemtray=self.system_tray_icon)

            else:
                # create new download thread
                new_download = DownloadLink(gid, self)
                self.threadPool.append(new_download)
                self.threadPool[len(self.threadPool) - 1].start()
                self.threadPool[len(self.threadPool) - 1].ARIA2NOTRESPOND.connect(self.aria2NotRespond)

                # create new progress_window
                self.progressBarOpen(gid)


# this method called if aria2 crashed or disconnected!
    def aria2NotRespond(self):
        self.aria2Disconnected()
        notifySend('Aria2 did not respond', 'Try again', 5000,
                   'critical', systemtray=self.system_tray_icon)

# this method called if user presses stop button in MainWindow
    def stopButtonPressed(self, button):
        self.stopAction.setEnabled(False)
        selected_row_return = self.selectedRow()  # finding user's selected row

        if selected_row_return:
            gid = self.download_table.item(selected_row_return, 8).text()
            answer = download.downloadStop(gid, self)
# if aria2 did not respond , then this function is checking for aria2
# availability , and if aria2 disconnected then aria2Disconnected is
# executed
            if answer == 'None':
                version_answer = download.aria2Version()
                if version_answer == 'did not respond':
                    self.aria2Disconnected()
                    notifySend("Aria2 disconnected!", "Persepolis is trying to connect!be patient!",
                               10000, 'warning', systemtray=self.system_tray_icon)


# this method called if user presses pause button in MainWindow
    def pauseButtonPressed(self, button):
        self.pauseAction.setEnabled(False)

        # find selected row
        selected_row_return = self.selectedRow()  

        if selected_row_return:
            # find download gid
            gid = self.download_table.item(selected_row_return, 8).text()

            # send pause request to aria2
            answer = download.downloadPause(gid)

            # if aria2 did not respond , then check aria2 availability!
            # and if aria2 disconnected then call aria2Disconnected
            if not(answer):
                version_answer = download.aria2Version()
                if version_answer == 'did not respond':
                    self.aria2Disconnected()
                    download.downloadStop(gid, self)
                    notifySend("Aria2 disconnected!", "Persepolis is trying to connect!be patient!",
                               10000, 'warning', systemtray=self.system_tray_icon)
                else:
                    notifySend("Aria2 did not respond!", "Try agian!",
                               10000, 'critical', systemtray=self.system_tray_icon)

# This method called if properties button pressed by user in MainWindow
    def propertiesButtonPressed(self, button):
        self.propertiesAction.setEnabled(False)
        selected_row_return = self.selectedRow()  # finding user's selected row

        if selected_row_return:
            # find gid of download
            gid = self.download_table.item(selected_row_return, 8).text()

            # creating propertieswindow
            propertieswindow = PropertiesWindow(
                self.propertiesCallback, gid, self.persepolis_setting, self)
            self.propertieswindows_list.append(propertieswindow)
            self.propertieswindows_list[len(
                self.propertieswindows_list) - 1].show()

# callBack of PropertiesWindow
    def propertiesCallback(self, add_link_dictionary, gid, category):

        # if checking_flag is equal to 1, it means that user pressed remove or
        # delete button or ... . so checking download information must be
        # stopped until job is done!
        if checking_flag != 2:
            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) - 1].QTABLEREADY.connect(
                partial(self.propertiesCallback2, add_link_dictionary, gid, category))
        else:
            self.propertiesCallback2(self, add_link_dictionary, gid, category)

    def propertiesCallback2(self, add_link_dictionary, gid, category):
        # current_category_tree_text is current category that highlited by user
        # in the left side panel
        current_category_tree_text = str(
            self.category_tree.currentIndex().data())

        selected_row_return = self.selectedRow()  # find user's selected row

        # find current category before changing
        current_category = self.download_table.item(
            selected_row_return, 12).text()


# find row of this gid!
        row = None
        for i in range(self.download_table.rowCount()):
            row_gid = self.download_table.item(i, 8).text()
            if gid == row_gid:
                row = i
                break

        if row:
            if current_category_tree_text == 'All Downloads':
                # update category in download_table
                item = QTableWidgetItem(str(category))
                self.download_table.setItem(row, 12, item)

            elif (str(current_category) != str(category)):
                # remove row from download_table
                self.download_table.removeRow(row)


# tell the CheckDownloadInfoThread that job is done!
        global checking_flag
        checking_flag = 0


# This method is called if user presses "show/hide progress window" button in
# MainWindow
    def progressButtonPressed(self, button):
    # find user's selected row
        selected_row_return = self.selectedRow()  
        if selected_row_return:
            gid = self.download_table.item(selected_row_return, 8).text()

        # if gid is in self.progress_window_list_dict , it means that progress
        # window  for this gid (for this download) is created before and it's
        # available! See progressBarOpen method for more information.
            if gid in self.progress_window_list_dict:
                # find member_number of window in progress_window_list_dict
                member_number = self.progress_window_list_dict[gid]

                # if window is visible >> hide it ,
                # and if window is hide >> make it visible!
                if self.progress_window_list[member_number].isVisible():
                    self.progress_window_list[member_number].hide()
                else:
                    self.progress_window_list[member_number].show()

            else:
                # if window is not availabile in progress_window_list_dict
                # so let's create it!
                self.progressBarOpen(gid)



# This method creates new ProgressWindow
    def progressBarOpen(self, gid):

        # create a progress_window
        progress_window = ProgressWindow(
            parent=self, gid=gid, persepolis_setting=self.persepolis_setting)  

        # add progress window to progress_window_list
        self.progress_window_list.append(progress_window)
        member_number = len(self.progress_window_list) - 1

        # in progress_window_list_dict , key is gid and value is member's
        # rank(number) in progress_window_list
        self.progress_window_list_dict[gid] = member_number

        # check user preferences
        # user can hide progress window in settings window.
        if str(self.persepolis_setting.value('settings/show-progress')) == 'yes':
            # show progress window
            self.progress_window_list[member_number].show()
        else:
            # hide progress window
            self.progress_window_list[member_number].hide()



# close event
# when user closes application then this method is called
    def closeEvent(self, event):
        # save window size  and position
        self.persepolis_setting.setValue('MainWindow/size', self.size())
        self.persepolis_setting.setValue('MainWindow/position', self.pos())

        # save columns size
        self.persepolis_setting.setValue('MainWindow/column0', self.download_table.columnWidth(0))
        self.persepolis_setting.setValue('MainWindow/column1', self.download_table.columnWidth(1))
        self.persepolis_setting.setValue('MainWindow/column2', self.download_table.columnWidth(2))
        self.persepolis_setting.setValue('MainWindow/column3', self.download_table.columnWidth(3))
        self.persepolis_setting.setValue('MainWindow/column4', self.download_table.columnWidth(4))
        self.persepolis_setting.setValue('MainWindow/column5', self.download_table.columnWidth(5))
        self.persepolis_setting.setValue('MainWindow/column6', self.download_table.columnWidth(6))
        self.persepolis_setting.setValue('MainWindow/column7', self.download_table.columnWidth(7))
        self.persepolis_setting.setValue('MainWindow/column10', self.download_table.columnWidth(10))
        self.persepolis_setting.setValue('MainWindow/column11', self.download_table.columnWidth(11))
        self.persepolis_setting.setValue('MainWindow/column12', self.download_table.columnWidth(12))


        # sync persepolis_setting
        # make sure all settings is saved.
        self.persepolis_setting.sync()

        # hide MainWindow
        self.hide()

        # write message in log and console
        print("Please Wait...")
        logger.sendToLog("Please wait ...", "INFO")

        # stop all downloads
        self.stopAllDownloads(event)  

        # hide system_tray_icon
        self.system_tray_icon.hide()  

        download.shutDown()  # shutting down Aria2
        sleep(0.5)
        global shutdown_notification  # see start of this script and see inherited QThreads
# shutdown_notification = 0 >> persepolis running , 1 >> persepolis is
# ready for close(closeEvent called) , 2 >> OK, let's close application!
        shutdown_notification = 1
        while shutdown_notification != 2:
            sleep(0.1)

        QCoreApplication.instance().quit
        print("Persepolis Closed")
        logger.sendToLog("Persepolis closed!", "INFO")
        sys.exit(0)


# showTray method shows/hides persepolis's icon in system tray icon
    def showTray(self, menu):
        # check if user checed trayAction in menu or not
        if self.trayAction.isChecked():
            # show system_tray_icon
            self.system_tray_icon.show()  

            # enabe minimizeAction in menu
            self.minimizeAction.setEnabled(True)

            tray_icon = 'yes'
        else:
            # hide system_tray_icon
            self.system_tray_icon.hide()  

            # disabaling minimizeAction in menu
            self.minimizeAction.setEnabled(False)

            tray_icon = 'no'

        # write changes in persepolis_setting
        self.persepolis_setting.setValue('settings/tray-icon', tray_icon)
        self.persepolis_setting.sync()


# this method shows/hides menubar and 
# it's called when user toggles showMenuBarAction in view menu
    def showMenuBar(self, menu):
        # persepolis has 2 menu bar
        # 1. menubar in main window
        # 2. qmenu(see mainwindow_ui.py file for more information)
        # qmenu is in toolBar2
        # user can toggle between viewing menu1 or menu2 with showMenuBarAction

        # check if showMenuBarAction is checked or unchecked
        if self.showMenuBarAction.isChecked():
            # show menubar and hide toolBar2
            self.menubar.show()
            self.toolBar2.hide()
            show_menubar = 'yes'
        else:
            # hide menubar and show toolBar2
            self.menubar.hide()
            self.toolBar2.show()
            show_menubar = 'no'

        # writing changes to persepolis_setting
        self.persepolis_setting.setValue('settings/show-menubar', show_menubar)
        self.persepolis_setting.sync()


# this method shows/hides left side panel 
# this method is called if user toggles showSidePanelAction in view menu
    def showSidePanel(self, menu):
        if self.showSidePanelAction.isChecked():
            self.category_tree_qwidget.show()
            show_sidepanel = 'yes'
        else:
            self.category_tree_qwidget.hide()
            show_sidepanel = 'no'

        # write changes to persepolis_setting
        self.persepolis_setting.setValue(
            'settings/show-sidepanel', show_sidepanel)
        self.persepolis_setting.sync()


# when user left clicks on persepolis's system tray icon,then
# this method is called
    def systemTrayPressed(self, click):
        if click == 3:
            self.minMaxTray(click)

# when minMaxTray method called ,this method shows/hides main window
    def minMaxTray(self, menu):
        # hide MainWindow if it's visible
        # Show MainWindow if it's hided
        if self.isVisible():
            self.minimizeAction.setText('Show main Window')
            self.minimizeAction.setIcon(QIcon(icons + 'window'))
            self.hide()
        else:
            self.show()
            self.minimizeAction.setText('Minimize to system tray')
            self.minimizeAction.setIcon(QIcon(icons + 'minimize'))

# showMainWindow shows main window in normal mode , see CheckingThread
    def showMainWindow(self):
        self.showNormal()
        self.minimizeAction.setText('Minimize to system tray')
        self.minimizeAction.setIcon(QIcon(icons + 'minimize'))

# stopAllDownloads stops all downloads
    def stopAllDownloads(self, menu):

        # stop all queues
        for queue in self.queue_list_dict.values():
            queue.stop = True
            queue.start = False

        # stop single downloads
        # get active download list from data base
        active_gid_list = self.persepolis_db.findActiveDownloads('Single Downloads')

        for gid in active_gid_list:
                answer = download.downloadStop(gid, self)
                # if aria2 did not respond , then this function is checking for
                # aria2 availability , and if aria2 disconnected then
                # aria2Disconnected is executed
                if answer == 'None':
                    version_answer = download.aria2Version()
                    if version_answer == 'did not respond':
                        self.aria2Disconnected()


# this method creats Preferences window
    def openPreferences(self, menu):
        self.preferenceswindow = PreferencesWindow(
            self, self.persepolis_setting)

        # show Preferences Window
        self.preferenceswindow.show()  


# this method is creating AboutWindow
    def openAbout(self, menu):
        about_window = AboutWindow(self.persepolis_setting)
        self.about_window_list.append(about_window)
        self.about_window_list[len(self.about_window_list) - 1].show()


# This method opens user's default download folder
    def openDefaultDownloadFolder(self, menu):
        # find user's default download folder from persepolis_setting
        self.persepolis_setting.sync()
        download_path = self.persepolis_setting.value('settings/download_path')

        # check that if download folder is availabile or not
        if os.path.isdir(download_path):
            # open folder
            osCommands.xdgOpen(download_path)  
        else:
            # show error message if folder didn't existed
            notifySend(str(download_path), 'Not Found', 5000,
                       'warning', systemtray=self.system_tray_icon)


# this method opens download folder , if download was finished
    def openDownloadFolder(self, menu):

        # find user's selected row
        selected_row_return = self.selectedRow()  

        if selected_row_return:
            # find gid
            gid = self.download_table.item(
                selected_row_return, 8).text()  
        
            # find status
            download_status = self.download_table.item(
                selected_row_return, 1).text()  

            if download_status == 'complete':
                # find download path
                dict = self.persepolis_db.searchGidInAddLinkTable(gid)
                file_path = dict['download_path']

                file_name = os.path.basename(str(file_path))

                file_path_split = file_path.split(file_name)

                del file_path_split[-1]

                download_path = file_name.join(file_path_split)

                # check that if download_path existed
                if os.path.isdir(download_path):
                    # open file
                    osCommands.xdgOpen(download_path)  
                else:
                    # showing error message , if folder did't existed
                    notifySend(str(download_path), 'Not Found', 5000,
                                'warning', systemtray=self.system_tray_icon)


# this method executes(opens) download file if download's progress was finished
    def openFile(self, menu):
        # find user's selected row
        selected_row_return = self.selectedRow()  

        if selected_row_return:
            # find gid
            gid = self.download_table.item(
                selected_row_return, 8).text() 

            # find status
            download_status = self.download_table.item(
                selected_row_return, 1).text() 

            if download_status == 'complete':
                # find download path
                dict = self.persepolis_db.searchGidInAddLinkTable(gid)
                file_path = dict['download_path']

                if os.path.isfile(file_path):
                    # open file
                    osCommands.xdgOpen(file_path)

                else:
                    # show error message , if file was deleted or moved
                    notifySend(str(file_path), 'Not Found', 5000,
                               'warning', systemtray=self.system_tray_icon)


# This method is called when user presses remove button in main window .
# removeButtonPressed removes download item
    def removeButtonPressed(self, button):
        self.removeAction.setEnabled(False)
        global checking_flag
# if checking_flag is equal to 1, it means that user pressed remove or
# delete button or ... . so checking download information must be stopped
# until job is done!
        if checking_flag != 2:
            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.removeButtonPressed2)
        else:
            self.removeButtonPressed2()

    def removeButtonPressed2(self):
        selected_row_return = self.selectedRow()  # finding selected row

        if selected_row_return:

            # find gid, file_name, category and download status
            gid = self.download_table.item(selected_row_return, 8).text()
            file_name = self.download_table.item(selected_row_return, 0).text()
            status = self.download_table.item(selected_row_return, 1).text()
            category = self.download_table.item(selected_row_return, 12).text()

            # remove item from download table
            self.download_table.removeRow(selected_row_return)

            # remove download item from data base
            self.persepolis_db.deleteItemInDownloadTable(gid, category)

            # remove file of download from download temp folder
            if file_name != '***' and status != 'complete':
                file_name_path = os.path.join(
                    temp_download_folder,  str(file_name))
                osCommands.remove(file_name_path)  # remove file

                file_name_aria = file_name_path + str('.aria2')
                osCommands.remove(file_name_aria)  # remove file.aria
        else:
            self.statusbar.showMessage("Please select an item first!")

        # tell the CheckDownloadInfoThread that job is done!
        global checking_flag
        checking_flag = 0

        self.selectedRow()


# this method is called when user presses delete button in MainWindow .
# this method deletes download file from hard disk and removs
# download item
    def deleteFile(self, menu):
        # show Warning message to the user.
        # check persepolis_setting first!
        # perhaps user checked "do not show this message again"
        delete_warning_message = self.persepolis_setting.value(
            'MainWindow/delete-warning', 'yes')

        if delete_warning_message == 'yes':
            self.msgBox = QMessageBox()
            self.msgBox.setText("<b><center>This operation will delete \
                    downloaded files from your hard disk<br>PERMANENTLY!</center></b>")
            self.msgBox.setInformativeText("<center>Do you want to continue?</center>")
            self.msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            self.msgBox.setIcon(QMessageBox.Warning)
            dont_show_checkBox = QtWidgets.QCheckBox("don't show this message again")
            self.msgBox.setCheckBox(dont_show_checkBox)
            reply = self.msgBox.exec_()

            # if user checks "do not show this message again!", change persepolis_setting!
            if self.msgBox.checkBox().isChecked():
                self.persepolis_setting.setValue(
                        'MainWindow/delete-warning', 'no')

            # do nothing if user clicks NO
            if reply != QMessageBox.Yes:
                return

        # if checking_flag is equal to 1, it means that user pressed remove or
        # delete button or ... . so checking download information must be
        # stopped until job is done!
        if checking_flag != 2:
            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.deleteFile2)
        else:
            self.deleteFile2()

    def deleteFile2(self):
        # find user's selected item
        selected_row_return = self.selectedRow()  

        if selected_row_return:
            # find gid , category and download_status
            gid = self.download_table.item(selected_row_return, 8).text()
            download_status = self.download_table.item(selected_row_return, 1).text()
            category = self.download_table.item(selected_row_return, 12).text()

            # remove file if download_status is complete
            if download_status == 'complete':
                # find download path
                dict = self.persepolis_db.searchGidInAddLinkTable(gid)
                file_path = dict['download_path']

                remove_answer = osCommands.remove(file_path)  

                if remove_answer == 'no':  # notifiy user if file_path is not valid
                    notifySend(str(file_path), 'Not Found', 5000,
                               'warning', systemtray=self.system_tray_icon)

            # remove item from download table
            self.download_table.removeRow(selected_row_return)

            # remove download item from data base
            self.persepolis_db.deleteItemInDownloadTable(gid, category)




# this method is called when user checkes selection mode in edit menu!
    def selectDownloads(self, menu):
        # if selectAllAction is checked >> activating actions and adding removeSelectedAction and deleteSelectedAction to the toolBar
        # if selectAction is unchecked deactivate actions and adding removeAction and deleteFileAction to the toolBar
        # if checking_flag is equal to 1, it means that user pressed remove or
        # delete button or ... . so checking download information must be
        # stopped until job is done!
        if checking_flag != 2:
            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.selectDownloads2)
        else:
            self.selectDownloads2()

    def selectDownloads2(self):
        # find highlited item in category_tree
        current_category_tree_text = str(current_category_tree_index.data())
        self.toolBarAndContextMenuItems(current_category_tree_text)

        if self.selectAction.isChecked():
            # add checkbox to items
            for i in range(self.download_table.rowCount()):
                item = self.download_table.item(i, 0)
                item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                              QtCore.Qt.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.Unchecked)

                # activate selectAllAction and removeSelectedAction and
                # deleteSelectedAction
                self.selectAllAction.setEnabled(True)
                self.removeSelectedAction.setEnabled(True)
                self.deleteSelectedAction.setEnabled(True)

        else:
            # remove checkbox from items
            for i in range(self.download_table.rowCount()):
                item_text = self.download_table.item(i, 0).text()
                item = QTableWidgetItem(item_text)
                self.download_table.setItem(i, 0, item)

                # deactivate selectAllAction and removeSelectedAction and
                # deleteSelectedAction
                self.selectAllAction.setEnabled(False)
                self.removeSelectedAction.setEnabled(False)
                self.deleteSelectedAction.setEnabled(False)


        # tell the CheckDownloadInfoThread that job is done!
        global checking_flag
        checking_flag = 0


# this method s called when user selects "select all items" form edit menu
    def selectAll(self, menu):
        for i in range(self.download_table.rowCount()):
            item = self.download_table.item(i, 0)
            item.setCheckState(QtCore.Qt.Checked)


# this method is called when user presses 'remove selected items' button
    def removeSelected(self, menu):

        # if checking_flag is equal to 1, it means that user pressed remove or
        # delete button or ... . so checking download information must be
        # stopped until job is done!
        if checking_flag != 2:
            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.removeSelected2)
        else:
            self.removeSelected2()

    def removeSelected2(self):

        # find checked rows! and append gid of checked rows to gid_list
        gid_list = []
        for row in range(self.download_table.rowCount()):
            # get download status
            status = self.download_table.item(row, 1).text()

            # get first column
            item = self.download_table.item(row, 0)

            # if checkState is 2, it means item is checked
            if (item.checkState() == 2) and (status == 'complete' or status == 'error' or status == 'stopped'):
                # find gid
                gid = self.download_table.item(row, 8).text()

                # append gid to gid_list
                gid_list.append(gid)

        # remove checked rows
        # find row number for specific gid
        for gid in gid_list:
            for i in range(self.download_table.rowCount()):
                row_gid = self.download_table.item(i, 8).text()
                if gid == row_gid:
                    row = i
                    break

            # find filename
            file_name = self.download_table.item(row, 0).text()
            
            # find category
            category = self.download_table.item(row, 12).text()

            # remove row from download_table
            self.download_table.removeRow(row)


            # remove download item from data base
            self.persepolis_db.deleteItemInDownloadTable(gid, category)

            # remove file of download from download temp folder
            if file_name != '***' and status != 'complete':
                file_name_path = os.path.join(
                    temp_download_folder,  str(file_name))
                osCommands.remove(file_name_path)  # remove file

                file_name_aria = file_name_path + str('.aria2')
                osCommands.remove(file_name_aria)  # remove file.aria
 
        # tell the CheckDownloadInfoThread that job is done!
        global checking_flag
        checking_flag = 0



# this method is called when user presses 'delete selected items'
    def deleteSelected(self, menu):
        # showing Warning message to the user.
        # checking persepolis_setting first!
        # perhaps user was checking "do not show this message again"
        delete_warning_message = self.persepolis_setting.value(
            'MainWindow/delete-warning', 'yes')

        if delete_warning_message == 'yes':
            self.msgBox = QMessageBox()
            self.msgBox.setText("<b><center>This operation will delete \
                    downloaded files from your hard disk<br>PERMANENTLY!</center></b>")
            self.msgBox.setInformativeText("<center>Do you want to continue?</center>")
            self.msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            self.msgBox.setIcon(QMessageBox.Warning)
            dont_show_checkBox = QtWidgets.QCheckBox("don't show this message again")
            self.msgBox.setCheckBox(dont_show_checkBox)
            reply = self.msgBox.exec_()

            # if user checks "do not show this message again!", change persepolis_setting!
            if self.msgBox.checkBox().isChecked():
                self.persepolis_setting.setValue(
                        'MainWindow/delete-warning', 'no')

            # do nothing if user clicks NO
            if reply != QMessageBox.Yes:
                return


        # if checking_flag is equal to 1, it means that user pressed remove or
        # delete button or ... . so checking download information must be
        # stopped until job is done!
        if checking_flag != 2:
            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.deleteSelected2)
        else:
            self.deleteSelected2()

    def deleteSelected2(self):

        # find checked rows! and append gid of checked rows to gid_list
        gid_list = []
        for row in range(self.download_table.rowCount()):
            # get download status
            status = self.download_table.item(row, 1).text()

            # get first column
            item = self.download_table.item(row, 0)

            # if checkState is 2, it means item is checked
            if (item.checkState() == 2) and (status == 'complete' or status == 'error' or status == 'stopped'):
                # find gid
                gid = self.download_table.item(row, 8).text()

                # append gid to gid_list
                gid_list.append(gid)


        # remove checked rows

        # find row number for specific gid
        for gid in gid_list:
            for i in range(self.download_table.rowCount()):
                row_gid = self.download_table.item(i, 8).text()
                if gid == row_gid:
                    row = i
                    break

            # find file_name
            file_name = self.download_table.item(row, 0).text()

            # find category
            category = self.download_table.item(row, 12).text()


            # if download is not completed,
            # remove downloaded file form download temp folder
            if file_name != '***' and status != 'complete':
                file_name_path = os.path.join(
                    temp_download_folder, str(file_name))

                # remove file : file_name_path
                osCommands.remove(file_name_path)

                # remove aria2 download information file : file_name_aria
                file_name_aria = file_name_path + str('.aria2')
                osCommands.remove(file_name_aria)

            # remove downloaded file, if download is completed
            if status == 'complete':

                # find download path
                dict = self.persepolis_db.searchGidInAddLinkTable(gid)
                file_path = dict['download_path']

                remove_answer = osCommands.remove(file_path)  


                if remove_answer == 'no':
                    notifySend(str(file_path), 'Not Found', 5000,
                               'warning', systemtray=self.system_tray_icon)

            # remove row from download_table
            self.download_table.removeRow(row)


            # remove download item from data base
            self.persepolis_db.deleteItemInDownloadTable(gid, category)


        # telling the CheckDownloadInfoThread that job is done!
        global checking_flag
        checking_flag = 0


# this method sorts download table by name 
    def sortByName(self, menu_item):

        # if checking_flag is equal to 1, it means that user pressed remove or
        # delete button or ... . so checking download information must be
        # stopped until job is done!
        if checking_flag != 2:
            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.sortByName2)
        else:
            self.sortByName2()

    def sortByName2(self):
        # find names and gid of downloads and save them in name_gid_dict
        # gid is key and name is value.
        gid_name_dict = {}
        for row in range(self.download_table.rowCount()):
            name = self.download_table.item(row, 0).text()
            gid = self.download_table.item(row, 8).text()
            gid_name_dict[gid] = name

        # sort names
        gid_sorted_list = sorted(gid_name_dict, key=gid_name_dict.get)

        # clear download_table and add sorted items
        self.download_table.clearContents()

        # find name of selected category
        current_category_tree_text = str(current_category_tree_index.data())

        # get download information from data base
        if current_category_tree_text == 'All Downloads':
            downloads_dict = self.persepolis_db.returnItemsInDownloadTable()
        else:
            downloads_dict = self.persepolis_db.returnItemsInDownloadTable(current_category_tree_text)

        j = 0 

        for gid in gid_sorted_list:
            #enter download rows according to gid_sorted_list
            download_info = downloads_dict[gid]

            keys_list = ['file_name',
                        'status',
                        'size',
                        'downloaded_size',
                        'percent',
                        'connections',
                        'rate',
                        'estimate_time_left',
                        'gid',
                        'link',
                        'firs_try_date',
                        'last_try_date',
                        'category'
                        ]

            i = 0
            for key in keys_list:
                item = QTableWidgetItem(download_info[key])

                # adding checkbox to download rows if selectAction is checked
                # in edit menu
                if self.selectAction.isChecked() and i == 0:
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                  QtCore.Qt.ItemIsEnabled)
                    item.setCheckState(QtCore.Qt.Unchecked)

                # insert item in download_table
                self.download_table.setItem(j, i, item)

                i = i+1

            j = j + 1

        # save sorted list (gid_sorted_list) in data base
        category_dict = {'category': current_category_tree_text} 

        # update gid_list
        category_dict['gid_list'] = gid_sorted_list


        # update category_db_table
        self.updateCategoryTable([category_dict])

        # tell the CheckDownloadInfoThread that job is done!
        global checking_flag
        checking_flag = 0



# this method sorts items in download_table by size
    def sortBySize(self, menu_item):

        # if checking_flag is equal to 1, it means that user pressed remove or
        # delete button or ... . so checking download information must be
        # stopped until job is done!
        if checking_flag != 2:
            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.sortBySize2)
        else:
            self.sortBySize2()

    def sortBySize2(self):

        # find name of selected category
        current_category_tree_text = str(current_category_tree_index.data())


        # find gid and size of downloads
        gid_size_dict = {}
        for row in range(self.download_table.rowCount()):
            size_str = self.download_table.item(row, 2).text()
            gid = self.download_table.item(row, 8).text()

            # convert file size to the Byte
            try:
                size_int = float(size_str[:-3])
                size_symbol = str(size_str[-2])
                if size_symbol == 'G':  # Giga Byte
                    size = size_int * 1073741824
                elif size_symbol == 'M':  # Mega Byte
                    size = size_int * 1048576
                elif size_symbol == 'K':  # Kilo Byte
                    size = size_int * 1024
                else:  # Byte
                    size = size_int
            except:
                size = 0

            # create a dictionary from gid and size of files in Bytes
            # gid as key and size as value
            gid_size_dict[gid] = size

        # sort gid_size_dict
        gid_sorted_list = sorted(
            gid_size_dict, key=gid_size_dict.get, reverse=True)

        # clear download_table by size
        self.download_table.clearContents()

        # get download information from data base
        if current_category_tree_text == 'All Downloads':
            downloads_dict = self.persepolis_db.returnItemsInDownloadTable()
        else:
            downloads_dict = self.persepolis_db.returnItemsInDownloadTable(current_category_tree_text)

        j = 0 

        for gid in gid_sorted_list:
            #enter download rows according to gid_sorted_list
            download_info = downloads_dict[gid]

            keys_list = ['file_name',
                        'status',
                        'size',
                        'downloaded_size',
                        'percent',
                        'connections',
                        'rate',
                        'estimate_time_left',
                        'gid',
                        'link',
                        'firs_try_date',
                        'last_try_date',
                        'category'
                        ]

            i = 0
            for key in keys_list:
                item = QTableWidgetItem(download_info[key])

                # adding checkbox to download rows if selectAction is checked
                # in edit menu
                if self.selectAction.isChecked() and i == 0:
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                  QtCore.Qt.ItemIsEnabled)
                    item.setCheckState(QtCore.Qt.Unchecked)

                # insert item in download_table
                self.download_table.setItem(j, i, item)

                i = i+1

            j = j + 1

        # save sorted list (gid_sorted_list) in data base
        category_dict = {'category': current_category_tree_text} 

        # update gid_list
        category_dict['gid_list'] = gid_sorted_list


        # update category_db_table
        self.updateCategoryTable([category_dict])

        # tell the CheckDownloadInfoThread that job is done!
        global checking_flag
        checking_flag = 0



# this method sorts download_table items with status
    def sortByStatus(self, item):

        # if checking_flag is equal to 1, it means that user pressed remove or
        # delete button or ... . so checking download information must be
        # stopped until job is done!
        if checking_flag != 2:
            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.sortByStatus2)
        else:
            self.sortByStatus2()

    def sortByStatus2(self):

        # find name of selected category
        current_category_tree_text = str(current_category_tree_index.data())

        # find gid and status of downloads
        gid_status_dict = {}
        for row in range(self.download_table.rowCount()):
            status = self.download_table.item(row, 1).text()
            gid = self.download_table.item(row, 8).text()
            # assign a number to every status
            if status == 'complete':
                status_int = 1
            elif status == 'stopped':
                status_int = 2
            elif status == 'error':
                status_int = 3
            elif status == 'downloading':
                status_int = 4
            elif status == 'waiting':
                status_int = 5
            else:
                status_int = 6

            # create a dictionary from gid and size_int of files in Bytes
            gid_status_dict[gid] = status_int

        # sort gid_status_dict
        gid_sorted_list = sorted(gid_status_dict, key=gid_status_dict.get)

        # get download information from data base
        if current_category_tree_text == 'All Downloads':
            downloads_dict = self.persepolis_db.returnItemsInDownloadTable()
        else:
            downloads_dict = self.persepolis_db.returnItemsInDownloadTable(current_category_tree_text)

        # clear download_table
        self.download_table.clearContents()

        j = 0 

        for gid in gid_sorted_list:
            #enter download rows according to gid_sorted_list
            download_info = downloads_dict[gid]

            keys_list = ['file_name',
                        'status',
                        'size',
                        'downloaded_size',
                        'percent',
                        'connections',
                        'rate',
                        'estimate_time_left',
                        'gid',
                        'link',
                        'firs_try_date',
                        'last_try_date',
                        'category'
                        ]

            i = 0
            for key in keys_list:
                item = QTableWidgetItem(download_info[key])

                # adding checkbox to download rows if selectAction is checked
                # in edit menu
                if self.selectAction.isChecked() and i == 0:
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                  QtCore.Qt.ItemIsEnabled)
                    item.setCheckState(QtCore.Qt.Unchecked)

                # insert item in download_table
                self.download_table.setItem(j, i, item)

                i = i+1

            j = j + 1

        # save sorted list (gid_sorted_list) in data base
        category_dict = {'category': current_category_tree_text} 

        # update gid_list
        category_dict['gid_list'] = gid_sorted_list


        # update category_db_table
        self.updateCategoryTable([category_dict])

        # tell the CheckDownloadInfoThread that job is done!
        global checking_flag
        checking_flag = 0



    # this method sorts download table with date added information
    def sortByFirstTry(self, item):

        # if checking_flag is equal to 1, it means that user pressed remove or
        # delete button or ... . so checking download information must be
        # stopped until job is done!
        if checking_flag != 2:
            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.sortByFirstTry2)
        else:
            self.sortByFirstTry2()

    def sortByFirstTry2(self):
        # find gid and first try date
        gid_try_dict = {}
        for row in range(self.download_table.rowCount()):
            first_try_date = self.download_table.item(row, 10).text()
            gid = self.download_table.item(row, 8).text()

            # convert date and hour in first_try_date to a number
            # for example , first_try_date = '2016/11/05 , 07:45:38'
            # must be converted to 20161105074538
            first_try_date_splited = first_try_date.split(' , ')
            date_list = first_try_date_splited[0].split('/')
            hour_list = first_try_date_splited[1].split(':')
            date_joind = "".join(date_list)
            hour_joind = "".join(hour_list)
            date_hour_str = date_joind + hour_joind
            date_hour = int(date_hour_str)

            # create a dictionary
            # gid as key and date_hour as value
            gid_try_dict[gid] = date_hour

        # sort
        gid_sorted_list = sorted(
            gid_try_dict, key=gid_try_dict.get, reverse=True)

        # clear download_table
        self.download_table.clearContents()

        # find name of selected category
        current_category_tree_text = str(current_category_tree_index.data())

        # get download information from data base
        if current_category_tree_text == 'All Downloads':
            downloads_dict = self.persepolis_db.returnItemsInDownloadTable()
        else:
            downloads_dict = self.persepolis_db.returnItemsInDownloadTable(current_category_tree_text)

        j = 0 

        for gid in gid_sorted_list:
            #enter download rows according to gid_sorted_list
            download_info = downloads_dict[gid]

            keys_list = ['file_name',
                        'status',
                        'size',
                        'downloaded_size',
                        'percent',
                        'connections',
                        'rate',
                        'estimate_time_left',
                        'gid',
                        'link',
                        'firs_try_date',
                        'last_try_date',
                        'category'
                        ]

            i = 0
            for key in keys_list:
                item = QTableWidgetItem(download_info[key])

                # adding checkbox to download rows if selectAction is checked
                # in edit menu
                if self.selectAction.isChecked() and i == 0:
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                  QtCore.Qt.ItemIsEnabled)
                    item.setCheckState(QtCore.Qt.Unchecked)

                # insert item in download_table
                self.download_table.setItem(j, i, item)

                i = i+1

            j = j + 1

        # save sorted list (gid_list) in data base
        category_dict = {'category': current_category_tree_text} 

        # update gid_sorted_list
        category_dict['gid_list'] = gid_sorted_list


        # update category_db_table
        self.updateCategoryTable([category_dict])

        # tell the CheckDownloadInfoThread that job is done!
        global checking_flag
        checking_flag = 0



# this method sorts download_table with order of last modify date
    def sortByLastTry(self, item):
        # if checking_flag is equal to 1, it means that user pressed remove or
        # delete button or ... . so checking download information must be
        # stopped until job is done!
        if checking_flag != 2:
            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.sortByLastTry2)
        else:
            self.sortByLastTry2()

    def sortByLastTry2(self):

        # create a dictionary
        # gid as key and date_hour as value
        gid_try_dict = {}

        # find gid and last try date for download items in download_table
        for row in range(self.download_table.rowCount()):
            last_try_date = self.download_table.item(row, 11).text()
            gid = self.download_table.item(row, 8).text()

            # convert date and hour in last_try_date to a number
            # for example , last_try_date = '2016/11/05 , 07:45:38'
            # must be converted to 20161105074538
            last_try_date_splited = last_try_date.split(' , ')
            date_list = last_try_date_splited[0].split('/')
            hour_list = last_try_date_splited[1].split(':')
            date_joind = "".join(date_list)
            hour_joind = "".join(hour_list)
            date_hour_str = date_joind + hour_joind
            date_hour = int(date_hour_str)

            # add gid and date_hour to gid_try_dict
            gid_try_dict[gid] = date_hour

        # sort
        gid_sorted_list = sorted(
            gid_try_dict, key=gid_try_dict.get, reverse=True)

        # clear download_table
        self.download_table.clearContents()

        # find name of selected category
        current_category_tree_text = str(current_category_tree_index.data())

        # get download information from data base
        if current_category_tree_text == 'All Downloads':
            downloads_dict = self.persepolis_db.returnItemsInDownloadTable()
        else:
            downloads_dict = self.persepolis_db.returnItemsInDownloadTable(current_category_tree_text)

        j = 0 

        for gid in gid_sorted_list:
            #enter download rows according to gid_sorted_list
            download_info = downloads_dict[gid]

            keys_list = ['file_name',
                        'status',
                        'size',
                        'downloaded_size',
                        'percent',
                        'connections',
                        'rate',
                        'estimate_time_left',
                        'gid',
                        'link',
                        'firs_try_date',
                        'last_try_date',
                        'category'
                        ]

            i = 0
            for key in keys_list:
                item = QTableWidgetItem(download_info[key])

                # adding checkbox to download rows if selectAction is checked
                # in edit menu
                if self.selectAction.isChecked() and i == 0:
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                  QtCore.Qt.ItemIsEnabled)
                    item.setCheckState(QtCore.Qt.Unchecked)

                # insert item in download_table
                self.download_table.setItem(j, i, item)

                i = i+1

            j = j + 1

        # save sorted list (gid_list) in data base
        category_dict = {'category': current_category_tree_text} 

        # update gid_sorted_list
        category_dict['gid_list'] = gid_sorted_list


        # update category_db_table
        self.updateCategoryTable([category_dict])

        # tell the CheckDownloadInfoThread that job is done!
        global checking_flag
        checking_flag = 0

###########

# this method called , when user clicks on 'create new queue' button in
# main window.
    def createQueue(self, item):
        text, ok = QInputDialog.getText(
            self, 'Queue', 'Enter queue name:', text='queue')

        if not(ok):
            return None

        queue_name = str(text)
        if ok and queue_name != '' and queue_name != 'Single Downloads':
            # check queue_name if existed!
            answer = self.persepolis_db.searchCategoryInCategoryTable(queue_name)

            # show Error window if queue existed before
            if answer:  
                error_messageBox = QMessageBox()
                error_messageBox.setText(
                    '<b>"' + queue_name + '</b>" is already existed!')
                error_messageBox.setWindowTitle('Error!')
                error_messageBox.exec_()
                return None

         # insert new item in category_tree
            new_queue_category = QStandardItem(queue_name)
            font = QtGui.QFont()
            font.setBold(True)
            new_queue_category.setFont(font)
            new_queue_category.setEditable(False)
            self.category_tree_model.appendRow(new_queue_category)

            dict = {'category': queue_name,
                    'start_time_enable': 'no',
                    'start_time': '0:0',
                    'end_time_enable': 'no',
                    'end_time': '0:0',
                    'reverse': 'no',
                    'limit_enable': 'no',
                    'limit_value': '0K',
                    'after_download': 'no'
                    'gid_list': '[]'
                    }

            # insert new category in data base
            self.persepolis_db.insertInCategoryTable(dict)

        # highlight new category in category_tree
        # find item
            for i in range(self.category_tree_model.rowCount()):
                category_tree_item_text = str(
                    self.category_tree_model.index(i, 0).data())
                if category_tree_item_text == queue_name:
                    category_index = i
                    break
        # highliting
            category_tree_model_index = self.category_tree_model.index(
                category_index, 0)
            self.category_tree.setCurrentIndex(category_tree_model_index)
            self.categoryTreeSelected(category_tree_model_index)

            # return queue_name
            return queue_name


# this method creates a FlashgotQueue window for list of links.
    def pluginQueue(self, list_of_links):
        # create window
        plugin_queue_window = FlashgotQueue(
            self, list_of_links, self.queueCallback, self.persepolis_setting)
        self.plugin_queue_window_list.append(plugin_queue_window)
        self.plugin_queue_window_list[len(
            self.plugin_queue_window_list) - 1].show()

        # bring plugin_queue_window on top
        self.plugin_queue_window_list[len(
            self.plugin_queue_window_list) - 1].raise_()
        self.plugin_queue_window_list[len(
            self.plugin_queue_window_list) - 1].activateWindow()
# TODO FlashgotQueue file must be checked and callbacks must be checked


# this method is importing a text file for creating queue .
# text file must contain links . 1 link per line!
    def importText(self, item):
        # get file path
        f_path, filters = QFileDialog.getOpenFileName(
            self, 'Select the text file that contains links')

        # if path is correct:
        if os.path.isfile(str(f_path)):
            # create a text_queue_window for getting information.
            text_queue_window = TextQueue(
                self, f_path, self.queueCallback, self.persepolis_setting)

            self.text_queue_window_list.append(text_queue_window)
            self.text_queue_window_list[len(
                self.text_queue_window_list) - 1].show()



# callback of text_queue_window and plugin_queue_window.AboutWindowi
# See importText and pluginQueue method for more information.
    def queueCallback(self, add_link_dictionary_list, category):
        # defining path of category_file
        selected_category = str(category)

        # highlight selected category in category_tree
        # first of all find category_index of item!
        for i in range(self.category_tree_model.rowCount()):
            category_tree_item_text = str(
                self.category_tree_model.index(i, 0).data())
            if category_tree_item_text == selected_category:
                category_index = i
                break
            
        # second: find category_tree_model_index 
        category_tree_model_index = self.category_tree_model.index(
            category_index, 0)

        # third: highlight item
        self.category_tree.setCurrentIndex(category_tree_model_index)
        self.categoryTreeSelected(category_tree_model_index)

        download_table_list = []

        # get now time and date
        date = download.nowDate()

        # add dictionary of downloads to data base
        for add_link_dictionary in add_link_dictionary_list:

            # aria2 identifies each download by the ID called GID. The GID must
            # be hex string of 16 characters.
            gid = self.gidGenerator()

            add_link_dictionary['gid'] = gid

            # download_info_file_list is a list that contains ['file_name' ,
            # 'status' , 'size' , 'downloaded size' ,'download percentage' ,
            # 'number of connections' ,'Transfer rate' , 'estimate_time_left' ,
            # 'gid' , 'link' , 'firs_try_date' , 'last_try_date', 'category']

            # if user or flashgot defined filename then file_name is valid in
            # add_link_dictionary['out']
            if add_link_dictionary['out']:
                file_name = add_link_dictionary['out']
            else:
                file_name = '***'

            list = [file_name, 'stopped', '***', '***', '***',
                    '***', '***', '***', gid, add_link_dictionary['link'],
                    date, date, category]

            dict = {'file_name': file_name,
                    'status': 'stopped',
                    'size': '***',
                    'downloaded_size': '***',
                    'percent': '***',
                    'connections': '***',
                    'rate': '***',
                    'estimate_time_left': '***',
                    'gid': gid,
                    'link': add_link_dictionary['link'],
                    'firs_try_date': date,
                    'last_try_date': date,
                    'category': category}

            # add dict to download_table_list
            download_table_list.append(dict)

            # create a row in download_table
            self.download_table.insertRow(0)
            j = 0
            for i in list:
                item = QTableWidgetItem(i)
                self.download_table.setItem(0, j, item)
                j = j + 1

            # this section adds checkBox to the row , if user's selected
            # selectAction
            if self.selectAction.isChecked():
                item = self.download_table.item(0, 0)
                item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                              QtCore.Qt.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.Unchecked)

            # spider is finding file size and file name
            new_spider = SpiderThread(add_link_dictionary, self)
            self.threadPool.append(new_spider)
            self.threadPool[len(self.threadPool) - 1].start()



        # write information in data_base
        self.persepolis_db.insertInDownloadTable(download_table_list)
        self.persepolis_db.insertInAddLinkTable(add_link_dictionary_list)
 


# this method is called , when user clicks on an item in
# category_tree (left side panel)
    def categoryTreeSelected(self, item):
        new_selection = item
        if current_category_tree_index != new_selection:
            # if checking_flag is equal to 1, it means that user pressed remove
            # or delete button or ... . so checking download information must
            # be stopped until job is done!
            if checking_flag != 2:

                wait_check = WaitThread()
                self.threadPool.append(wait_check)
                self.threadPool[len(self.threadPool) - 1].start()
                self.threadPool[len(self.threadPool) - 1].QTABLEREADY.connect(
                    partial(self.categoryTreeSelected2, new_selection))
            else:
                self.categoryTreeSelected2(new_selection)

    def categoryTreeSelected2(self, new_selection):
        global current_category_tree_index

        # clear download_table
        self.download_table.setRowCount(0)


        # old_selection_index
        old_selection_index = current_category_tree_index

        # finding name of old_selection_index
        old_category_tree_item_text = str(old_selection_index.data())

        queue_dict = {'category': old_category_tree_item_text}

        # start_checkBox
        if self.start_checkBox.isChecked():
            queue_dict['start_time_enable'] = 'yes'
        else:
            queue_dict['start_time_enable'] = 'no'

        # end_checkBox
        if self.end_checkBox.isChecked():
            queue_dict['end_time_enable'] = 'yes'
        else:
            queue_dict['end_time_enable'] = 'no'

        # start_time_qDataTimeEdit
        start_time = self.start_time_qDataTimeEdit.text()
        queue_dict['start_time'] = str(start_time)

        # end_time_qDateTimeEdit
        end_time = self.end_time_qDateTimeEdit.text()
        queue_dict['end_time'] = str(end_time)

        # reverse_checkBox
        if self.reverse_checkBox.isChecked():
            queue_dict['reverse'] = 'yes'
        else:
            queue_dict['reverse'] = 'no'

        # limit_checkBox
        if self.limit_checkBox.isChecked():
            queue_dict['limit_enable'] = 'yes'
        else:
            queue_dict['limit_enable'] = 'no'

        # limit_comboBox and limit_spinBox
        if self.limit_comboBox.currentText() == "KB/S":
            limit = str(self.limit_spinBox.value()) + str("K")
        else:
            limit = str(self.limit_spinBox.value()) + str("M")

        queue_dict['limit_value'] = str(limit)

        # after_checkBox
        if self.after_checkBox.isChecked():
            queue_dict['after_download'] = 'yes'
        else:
            queue_dict['after_download'] = 'no'

        # if old_selection_index.data() is equal to None >> It means queue is 
        # deleted! and no text (data) available for it
        if old_selection_index.data():  

            # update data base
            self.persepolis_db.updateCategoryTable([queue_dict])
    
        # update download_table
        current_category_tree_index = new_selection

        # find category
        # TODO must be checked
        current_category_tree_text = str(
            self.category_tree.currentIndex().data())

        # read download items from data base
        if current_category_tree_text == 'All Downloads':
            download_table_dict = self.persepolis_db.returnItemsInDownloadTable()
        else:
            download_table_dict = self.persepolis_db.returnItemsInDownloadTable(current_category_tree_text)

        # get gid_list
        gid_list = self.persepolis_db.searchCategoryInCategoryTable(current_category_tree_text)


        keys_list = ['file_name',
                    'status',
                    'size',
                    'downloaded_size',
                    'percent',
                    'connections',
                    'rate',
                    'estimate_time_left',
                    'gid',
                    'link',
                    'firs_try_date',
                    'last_try_date',
                    'category'
                    ]

        # insert items in download_table 
        for gid in gid_list:
            dict = download_table_dict[gid]
            i = 0
            for key in keys_list: 
                item = QTableWidgetItem(str(dict[key]))
                
                # add checkbox to download rows if selectAction is checked
                # in edit menu
                if self.selectAction.isChecked() and i == 0:
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                  QtCore.Qt.ItemIsEnabled)
                    item.setCheckState(QtCore.Qt.Unchecked)

                self.download_table.setItem(0, i, item)

                i = i + 1

        # tell the CheckDownloadInfoThread that job is done!
        global checking_flag
        checking_flag = 0

        # update toolBar and tablewidget_menu items
        self.toolBarAndContextMenuItems(str(current_category_tree_text))


# this method changes toolabr and context menu items when new item
# highlited by user in category_tree
    def toolBarAndContextMenuItems(self, category):
        # clear toolBar and context menus. 
        # it makes them ready for adding 
        # new items that suitable with new selected category.

        # clear toolBar
        self.toolBar.clear()

        # clear context menu of download_table
        self.download_table.tablewidget_menu.clear()

        # clear context menu of category_tree
        self.category_tree.category_tree_menu.clear()

        # add selectAction to context menu
        self.download_table.tablewidget_menu.addAction(self.selectAction)

        queueAction = QAction(QIcon(icons + 'add'), 'Single Downloads', self,
                              statusTip="Add to Single Downloads", triggered=partial(self.addToQueue, 'Single Downloads'))

        # check if user checked selection mode
        if self.selectAction.isChecked():
            selection_mode = True 
            self.download_table.sendMenu = self.download_table.tablewidget_menu.addMenu(
                'Send selected downloads to')
        else:
            selection_mode = False
            self.download_table.sendMenu = self.download_table.tablewidget_menu.addMenu(
                'Send to')

        if category != 'Single Downloads':
            self.download_table.sendMenu.addAction(queueAction)

        # get categories list from data base
        categories_list = self.persepolis_db.categoriesList()

        # add categories name to sendMenu
        for category_name in categories_list:
            if category_name != category:
                queueAction = QAction(QIcon(icons + 'add_queue'), category_name, self, statusTip="Add to" + category_name,
                        triggered=partial(self.addToQueue, category_name))

                self.download_table.sendMenu.addAction(queueAction)

        if category == 'All Downloads' and not(selection_mode):

            # hide queue_panel_widget(left side down panel)
            self.queue_panel_widget.hide()

            # update toolBar
            list = [self.addlinkAction, self.resumeAction, self.pauseAction,
                    self.stopAction, self.removeAction, self.deleteFileAction,
                    self.propertiesAction, self.progressAction, self.minimizeAction,
                    self.exitAction]

            for i in list:
                self.toolBar.addAction(i)

            self.toolBar.insertSeparator(self.addlinkAction)
            self.toolBar.insertSeparator(self.resumeAction)
            self.toolBar.insertSeparator(self.removeSelectedAction)
            self.toolBar.insertSeparator(self.exitAction)

# add actions to download_table's context menu
            list = [self.openFileAction, self.openDownloadFolderAction, self.resumeAction,
                    self.pauseAction, self.stopAction, self.removeAction, self.deleteFileAction,
                    self.propertiesAction, self.progressAction]

            for action in list :
                self.download_table.tablewidget_menu.addAction(action)

        elif category == 'All Downloads' and selection_mode:

            # hide queue_panel_widget(lef side down panel)
            self.queue_panel_widget.hide()

            # update toolBar
            list = [self.addlinkAction, self.resumeAction, self.pauseAction,
                    self.stopAction, self.removeSelectedAction, self.deleteSelectedAction,
                    self.propertiesAction, self.progressAction, self.minimizeAction, self.exitAction]

            for i in list:
                self.toolBar.addAction(i)

            self.toolBar.insertSeparator(self.addlinkAction)
            self.toolBar.insertSeparator(self.resumeAction)
            self.toolBar.insertSeparator(self.removeSelectedAction)
            self.toolBar.insertSeparator(self.exitAction)
            self.toolBar.addSeparator()


            # add actions to download_table's context menu
            list = [self.openFileAction, self.openDownloadFolderAction, self.resumeAction,
                    self.pauseAction, self.stopAction, self.removeSelectedAction,
                    self.deleteSelectedAction, self.propertiesAction, self.progressAction]

            for action in list:
                self.download_table.tablewidget_menu.addAction(action)

        if category == 'Single Downloads' and not(selection_mode):

            # hide queue_panel_widget
            self.queue_panel_widget.hide()

            # update toolBar
            list = [self.addlinkAction, self.resumeAction, self.pauseAction, self.stopAction,
                    self.removeAction, self.deleteFileAction, self.propertiesAction,
                    self.progressAction, self.minimizeAction, self.exitAction]

            for i in list:
                self.toolBar.addAction(i)

            self.toolBar.insertSeparator(self.addlinkAction)
            self.toolBar.insertSeparator(self.resumeAction)
            self.toolBar.insertSeparator(self.removeSelectedAction)
            self.toolBar.insertSeparator(self.exitAction)


            # add actions to download_table's context menu
            list = [self.openFileAction, self.openDownloadFolderAction, self.resumeAction,
                    self.pauseAction, self.stopAction, self.removeAction,
                    self.deleteFileAction, self.propertiesAction, self.progressAction]

            for action in list:
                self.download_table.tablewidget_menu.addAction(action)

        elif category == 'Single Downloads' and selection_mode:

            # hide queue_panel_widget
            self.queue_panel_widget.hide()
            self.queuePanelWidget(category)

            # update toolBar
            list = [self.addlinkAction, self.resumeAction, self.pauseAction,
                    self.stopAction, self.removeSelectedAction, self.deleteSelectedAction,
                    self.propertiesAction, self.progressAction, self.minimizeAction,
                    self.exitAction]

            for i in list:
                self.toolBar.addAction(i)

            self.toolBar.insertSeparator(self.addlinkAction)
            self.toolBar.insertSeparator(self.removeSelectedAction)
            self.toolBar.insertSeparator(self.exitAction)
            self.toolBar.addSeparator()

            # add actions to download_table's context menu
            list = [self.openFileAction, self.openDownloadFolderAction, self.resumeAction,
                    self.pauseAction, self.stopAction, self.removeSelectedAction,
                    self.deleteSelectedAction, self.propertiesAction, self.progressAction]

            for action in list:
                self.download_table.tablewidget_menu.addAction(action)

        elif (category != 'All Downloads' and category != 'Single Downloads') and not(selection_mode):

            # show queue_panel_widget
            self.queue_panel_widget.show()
            self.queuePanelWidget(category)

            # update toolBar
            list = [self.addlinkAction, self.removeAction, self.deleteFileAction,
                    self.propertiesAction, self.startQueueAction, self.stopQueueAction,
                    self.removeQueueAction, self.moveUpAction, self.moveDownAction,
                    self.minimizeAction, self.exitAction]

            for i in list:
                self.toolBar.addAction(i)

            self.toolBar.insertSeparator(self.addlinkAction)
            self.toolBar.insertSeparator(self.startQueueAction)
            self.toolBar.insertSeparator(self.minimizeAction)
            self.toolBar.insertSeparator(self.exitAction)
            self.toolBar.addSeparator()

            # add actions to download_table's context menu
            for action in [self.openFileAction, self.openDownloadFolderAction, self.removeAction, self.deleteFileAction, self.propertiesAction]:
                self.download_table.tablewidget_menu.addAction(action)

            # update category_tree_menu
            for i in self.startQueueAction, self.stopQueueAction, self.removeQueueAction:
                self.category_tree.category_tree_menu.addAction(i)

            # check queue condition
            if str(category) in self.queue_list_dict.keys():
                queue_status = self.queue_list_dict[str(category)].start
            else:
                queue_status = False

            if queue_status:  # if queue started before
                self.stopQueueAction.setEnabled(True)
                self.startQueueAction.setEnabled(False)
                self.removeQueueAction.setEnabled(False)
            else:            #if queue didn't start
                self.stopQueueAction.setEnabled(False)
                self.startQueueAction.setEnabled(True)
                self.removeQueueAction.setEnabled(True)

        elif (category != 'All Downloads' and category != 'Single Downloads') and selection_mode:

            # show queue_panel_widget
            self.queue_panel_widget.show()
            self.queuePanelWidget(category)

            # update toolBar
            list = [self.addlinkAction, self.removeSelectedAction, self.deleteSelectedAction,
                    self.propertiesAction, self.startQueueAction, self.stopQueueAction,
                    self.removeQueueAction, self.moveUpSelectedAction, self.moveDownSelectedAction,
                    self.minimizeAction, self.exitAction]

            for i in list:
                self.toolBar.addAction(i)

            self.toolBar.insertSeparator(self.addlinkAction)
            self.toolBar.insertSeparator(self.startQueueAction)
            self.toolBar.insertSeparator(self.minimizeAction)
            self.toolBar.insertSeparator(self.exitAction)
            self.toolBar.addSeparator()

            # add actions to download_table's context menu
            for action in [self.openFileAction, self.openDownloadFolderAction, self.removeAction, self.deleteFileAction, self.propertiesAction]:
                self.download_table.tablewidget_menu.addAction(action)

            # update category_tree_menu(right click menu for category_tree items)
            for i in self.startQueueAction, self.stopQueueAction, self.removeQueueAction:
                self.category_tree.category_tree_menu.addAction(i)

        # check queue condition
        if category != 'All Downloads' and category != 'Single Downloads':
            if str(category) in self.queue_list_dict.keys():
                queue_status = self.queue_list_dict[str(category)].start
            else:
                queue_status = False

            if queue_status:  
                # if queue started befor
                self.stopQueueAction.setEnabled(True)
                self.startQueueAction.setEnabled(False)
                self.removeQueueAction.setEnabled(False)
                self.moveUpAction.setEnabled(False)
                self.moveDownAction.setEnabled(False)
                self.moveUpSelectedAction.setEnabled(False)
                self.moveDownSelectedAction.setEnabled(False)
            else:
                # if queue didn't start
                self.stopQueueAction.setEnabled(False)
                self.startQueueAction.setEnabled(True)
                self.removeQueueAction.setEnabled(True)

                if selection_mode:
                    self.moveUpAction.setEnabled(False)
                    self.moveDownAction.setEnabled(False)
                    self.moveUpSelectedAction.setEnabled(True)
                    self.moveDownSelectedAction.setEnabled(True)

                else:
                    self.moveUpAction.setEnabled(True)
                    self.moveDownAction.setEnabled(True)
                    self.moveUpSelectedAction.setEnabled(False)
                    self.moveDownSelectedAction.setEnabled(False)

        else:  
            # if category is All Downloads  or Single Downloads
            self.stopQueueAction.setEnabled(False)
            self.startQueueAction.setEnabled(False)
            self.removeQueueAction.setEnabled(False)
            self.moveUpAction.setEnabled(False)
            self.moveDownAction.setEnabled(False)
            self.moveUpSelectedAction.setEnabled(False)
            self.moveDownSelectedAction.setEnabled(False)

        # add sortMenu to download_table context menu
        sortMenu = self.download_table.tablewidget_menu.addMenu('Sort by')
        sortMenu.addAction(self.sort_file_name_Action)

        sortMenu.addAction(self.sort_file_size_Action)

        sortMenu.addAction(self.sort_first_try_date_Action)

        sortMenu.addAction(self.sort_last_try_date_Action)

        sortMenu.addAction(self.sort_download_status_Action)


# this method removes the queue that is selected in category_tree
    def removeQueue(self, menu):
        # show Warning message to user.
        # checks persepolis_setting first!
        # perhaps user was checking "do not show this message again"
        remove_warning_message = self.persepolis_setting.value(
            'MainWindow/remove-queue-warning', 'yes')

        if remove_warning_message == 'yes':
            self.remove_queue_msgBox = QMessageBox()
            self.remove_queue_msgBox.setText('<b><center>This operation will remove \
                    all download items in this queue<br>from "All Downloads" list!</center></b>')

            self.remove_queue_msgBox.setInformativeText("<center>Do you want to continue?</center>")
            self.remove_queue_msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            self.remove_queue_msgBox.setIcon(QMessageBox.Warning)
            dont_show_checkBox = QtWidgets.QCheckBox("don't show this message again")
            self.remove_queue_msgBox.setCheckBox(dont_show_checkBox)
            reply = self.remove_queue_msgBox.exec_()

            # if user checks "do not show this message again!", change persepolis_setting!
            if self.remove_queue_msgBox.checkBox().isChecked():
                self.persepolis_setting.setValue(
                        'MainWindow/remove-queue-warning', 'no')

            # do nothing if user clicks NO
            if reply != QMessageBox.Yes:
                return


        # find name of queue
        current_category_tree_text = str(current_category_tree_index.data())

        if current_category_tree_text != 'All Downloads' and current_category_tree_text != 'Single Downloads':

            # remove queue from category_tree
            row_number = current_category_tree_index.row()
            self.category_tree_model.removeRow(row_number)

            # delete category from data base
            self.persepolis_db.deleteCategory(current_category_tree_text)


# highlight "All Downloads" in category_tree
        all_download_index = self.category_tree_model.index(0, 0)
        self.category_tree.setCurrentIndex(all_download_index)
        self.categoryTreeSelected(all_download_index)


    # this method starts the queue that is selected in category_tree
    def startQueue(self, menu):
        self.startQueueAction.setEnabled(False)

        # current_category_tree_text is the name of queue that is selected by user
        current_category_tree_text = str(current_category_tree_index.data())

        # check that if user checks start_checkBox or not.
        if self.start_checkBox.isChecked() :
            queue_info_dict['start_time_enable'] = 'yes'

            # read start_time value
            start_time = self.start_time_qDataTimeEdit.text()
        else:
            queue_info_dict['start_time_enable'] = 'no'
            start_time = None


        # check that if user checked end_checkBox or not.
        if self.end_checkBox.isChecked():
            queue_info_dict['end_time_enable'] = 'yes'

            # read end_time value
            end_time = self.end_time_qDateTimeEdit.text()
        else:
            queue_info_dict['end_time_enable'] = 'no'
            end_time = None


        # reverse_checkBox
        if self.reverse_checkBox.isChecked():
            queue_info_dict['reverse'] = 'yes'
        else:
            queue_info_dict['reverse'] = 'no'

        # update data base
        self.persepolis_db.updateCategoryTable([queue_info_dict])


        # create new Queue thread
        new_queue = Queue(current_category_tree_text, start_time,
                          end_time, self)

        self.queue_list_dict[current_category_tree_text] = new_queue
        self.queue_list_dict[current_category_tree_text].start()
        self.queue_list_dict[current_category_tree_text].REFRESHTOOLBARSIGNAL.connect(
            self.toolBarAndContextMenuItems)

        self.toolBarAndContextMenuItems(current_category_tree_text)

    # this method stops the queue that is selected 
    # by user in the left side panel 
    def stopQueue(self, menu):
        self.stopQueueAction.setEnabled(False)

        # current_category_tree_text is the name of queue that is selected by user
        current_category_tree_text = str(current_category_tree_index.data())

        queue = self.queue_list_dict[current_category_tree_text]
        queue.start = False
        queue.stop = True

        self.startQueueAction.setEnabled(True)


# this method is called , when user want to add a download to a queue with
# context menu. see also toolBarAndContextMenuItems() method
    def addToQueue(self, data, menu):
        # if checking_flag is equal to 1, it means that user pressed remove or
        # delete button or ... . so checking download information must be
        # stopped until job is done!

        if checking_flag != 2:
            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(
                self.threadPool) - 1].QTABLEREADY.connect(partial(self.addToQueue2, data))
        else:
            self.addToQueue2(data)

    def addToQueue2(self, data):

        send_message = False

        # new selected category
        new_category = str(data)  

        gid_list = []

        # gid_list contains gid of downloads that user wants to add them to a new category
        # check if user checked selectAction in edit menu
        if self.selectAction.isChecked():
            # finding checked rows! and append gid of checked rows to
            # gid_list
            for row in range(self.download_table.rowCount()):
                status = self.download_table.item(row, 1).text()
                item = self.download_table.item(row, 0)
                category = self.download_table.item(row, 12).text()

                # check status of old category
                if category in self.queue_list_dict.keys():
                    if self.queue_list_dict[category].start:
                        # It means queue is in download progress
                        status = 'downloading'  

                # checkState 2 means item is checked by user.
                # download must be in stopped situation.
                if (status == 'error' or status == 'stopped' or status == 'complete'):
                    if (item.checkState() == 2): 
                        gid = self.download_table.item(row, 8).text()
                        gid_list.append(gid)
                else:
                    send_message = True

        else:
            # find selected_row
            selected_row_return = self.selectedRow() 

            # append gid of selected_row to gid_list
            if selected_row_return:
                gid = self.download_table.item(selected_row_return, 8).text()
                status = self.download_table.item(selected_row_return, 1).text()
                category = self.download_table.item(selected_row_return, 12).text()

                if category in self.queue_list_dict.keys():
                    if self.queue_list_dict[category].start:
                        # It means queue is in download progress
                        status = 'downloading'  

                # download must be in stopped situation
                if (status == 'error' or status == 'stopped' or status == 'complete'):
                    gid_list.append(gid)
                else:
                    send_message = True

        # gid_list is ready now!

        for gid in gid_list:

            # find row number for specific gid
            for i in range(self.download_table.rowCount()):
                row_gid = self.download_table.item(i, 8).text()
                if gid == row_gid:
                    row = i
                    break

            # current_category = former selected category
            current_category = self.download_table.item(row, 12).text()

            if current_category != new_category:

                # write changes in data base
                dict = {'gid': gid, 'category': new_category}
                self.persepolis_db.updateDownloadTable([dict])
                self.persepolis_db.updateAddLinkTable([dict]) 
                self.persepolis_db.setDefaultGidInAddlinkTable(gid, start_time=True, end_time=True, after_download=True)
                
                # update category in download_table
                current_category_tree_text = str(
                    current_category_tree_index.data())
                if current_category_tree_text == 'All Downloads':
                    item = QTableWidgetItem(new_category)
                    # if user checked selectAction , then a checkbox added to
                    # item
                    if self.selectAction.isChecked() == True:
                        item = self.download_table.item(0, 0)
                        item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                      QtCore.Qt.ItemIsEnabled)
                        item.setCheckState(QtCore.Qt.Unchecked)

                    self.download_table.setItem(row, 12, item)
                else:
                    self.download_table.removeRow(row)

        if send_message:
            # notify user that transfer was unsuccessful
            notifySend("item transferation was unsuccessful for some items!", "Please stop download progress first",
                       '5000', 'no', systemtray=self.system_tray_icon)

        global checking_flag
        checking_flag = 0



# this method activates or deactivates start_frame according to situation
    def startFrame(self, checkBox):

        if self.start_checkBox.isChecked():
            self.start_frame.setEnabled(True)
        else:
            self.start_frame.setEnabled(False)

# this method activates or deactivates end_frame according to situation
    def endFrame(self, checkBox):

        if self.end_checkBox.isChecked():
            self.end_frame.setEnabled(True)
        else:
            self.end_frame.setEnabled(False)


# this method showing/hiding queue_panel_widget according to
# queue_panel_show_button text
    def showQueuePanelOptions(self, button):
        if (self.queue_panel_show_button.text() == 'Show options') or (self.queue_panel_show_button.text() == '&Show options'):
            self.queue_panel_widget_frame.show()
            self.queue_panel_show_button.setText('Hide options')
        else:
            self.queue_panel_widget_frame.hide()
            self.queue_panel_show_button.setText('Show options')

# this metode is activating after_pushButton whith limit_comboBox changing
    def limitComboBoxChanged(self, connect):
        self.limit_pushButton.setEnabled(True)


# this method activates or deactivates limit_frame according to
# limit_checkBox situation
    def limitFrame(self, checkBox):
        if self.limit_checkBox.isChecked():
            self.limit_frame.setEnabled(True)
            self.limit_pushButton.setEnabled(True)
        else:
            self.limit_frame.setEnabled(False)

        # current_category_tree_text is the name of queue that selected by user
            current_category_tree_text = str(
                current_category_tree_index.data())

        # inform queue about changes
            if current_category_tree_text in self.queue_list_dict.keys():
                self.queue_list_dict[current_category_tree_text].limit = False
                self.queue_list_dict[current_category_tree_text].limit_changed = True


# this method limits download speed in queue
    def limitPushButtonPressed(self, button):
        self.limit_pushButton.setEnabled(False)

        #current_category_tree_text is the name of queue that selected by user
        current_category_tree_text = str(current_category_tree_index.data())

        # informing queue about changes
        self.queue_list_dict[current_category_tree_text].limit = True
        self.queue_list_dict[current_category_tree_text].limit_changed = True

# this method handles user's shutdown request 
def afterPushButtonPressed(self, button):
        # current_category_tree_text is the name of queue that selected by user
        current_category_tree_text = str(current_category_tree_index.data())

        self.after_pushButton.setEnabled(False)

        if os_type != 'Windows':  # For Linux and Mac OSX

            # get root password from user
            passwd, ok = QInputDialog.getText(
                self, 'PassWord', 'Please enter root password:', QtWidgets.QLineEdit.Password)
            if ok:
                answer = os.system("echo '" + passwd +
                                   "' |sudo -S echo 'checking passwd'  ")
                while answer != 0:
                    passwd, ok = QInputDialog.getText(
                        self, 'PassWord', 'Wrong Password!\nTry again!', QtWidgets.QLineEdit.Password)
                    if ok:
                        # checking password
                        answer = os.system(
                            "echo '" + passwd + "' |sudo -S echo 'checking passwd'  ")
                    else:
                        ok = False
                        break

                if ok:
                    self.queue_list_dict[current_category_tree_text].after = True

                    # send password and queue name to ShutDownThread
                    # this script creates a file with the name of queue in  this folder "persepolis_tmp/shutdown/" 
                    # and writing a "wait" word in this file
                    # shutdown_script_root is checking that file every second .
                    # when "wait" changes to "shutdown" in that file then
                    # script shuts down system
                    shutdown_enable = ShutDownThread(
                        current_category_tree_text, passwd)
                    self.threadPool.append(shutdown_enable)
                    self.threadPool[len(self.threadPool) - 1].start()

                else:
                    self.after_checkBox.setChecked(False)
                    self.queue_list_dict[current_category_tree_text].after = False

            else:
                self.after_checkBox.setChecked(False)
                self.queue_list_dict[current_category_tree_text].after = False

        else:  # for windows

            shutdown_enable = ShutDownThread(current_category_tree_text)
            self.threadPool.append(shutdown_enable)
            self.threadPool[len(self.threadPool) - 1].start()


# this method activates or deactivates after_frame according to
# after_checkBox situation
    def afterFrame(self, checkBox):
        # current_category_tree_text is the name of queue that selected by user
        current_category_tree_text = str(current_category_tree_index.data())

        if self.after_checkBox.isChecked():  # enable after_frame
            self.after_frame.setEnabled(True)
            self.after_pushButton.setEnabled(True)
        else:
            self.after_frame.setEnabled(False)  # disable after_frame

            # write 'canceled' word in persepolis_tmp/shutdown/queue_name .
            # this is informing shutdown_script_root for canceling shutdown
            # operation after download
            if current_category_tree_text in self.queue_list_dict.keys():
                if self.queue_list_dict[current_category_tree_text].after:
                    shutdown_file = os.path.join(
                        persepolis_tmp, 'shutdown', current_category_tree_text)

                    f = Open(shutdown_file, 'w')
                    f.writelines('canceled')
                    f.close()

                    self.queue_list_dict[current_category_tree_text].after = False


# queue_panel_widget
# this method checks that queue started or not,
# and it shows or hides widgets in queue_panel_widget
# according to situation and set widgets in panel.

    def queuePanelWidget(self, category):
        # update queue_panel_widget items

        # read queue_info_dict from data base
        queue_info_dict = self.persepolis_db.searchCategoryInCategoryTable(category) 

        # check queue condition
        if str(category) in self.queue_list_dict.keys():
            queue_status = self.queue_list_dict[str(category)].start
        else:
            queue_status = False

        if queue_status:  # queue started
            self.start_end_frame.hide()
            self.limit_after_frame.show()

            # check that if user set limit speed
            limit_status = self.queue_list_dict[str(category)].limit

            # check that if user selected 'shutdown after download'
            after_status = self.queue_list_dict[str(category)].after

            if limit_status:  # It means queue's download speed limited by user
                # get limit_spinBox value and limit_comboBox value
                limit_number = self.queue_list_dict[str(
                    category)].limit_spinBox_value
                limit_unit = self.queue_list_dict[str(
                    category)].limit_comboBox_value

                # set limit_spinBox value
                self.limit_spinBox.setValue(limit_number)

                # set limit_comboBox value
                if limit_unit == 'K':
                    self.after_comboBox.setCurrentIndex(0)
                else:
                    self.after_comboBox.setCurrentIndex(1)

                # enable limit_frame
                self.limit_checkBox.setChecked(True)

            else:
                # disabale limit_frame
                self.limit_checkBox.setChecked(False)

            # limit speed
                limit = str(queue_info_dict['limit_value'])

            # limit values
                limit_number = limit[0:-1]
                limit_unit = limit[-1]

            # limit_spinBox
                self.limit_spinBox.setValue(float(limit_number))

            # limit_comboBox
                if limit_unit == 'K':
                    self.limit_comboBox.setCurrentIndex(0)
                else:
                    self.limit_comboBox.setCurrentIndex(1)

            # if after_status is True,
            # it means that user was selected
            # shutdown option, after queue completed.
            if after_status:
                self.after_checkBox.setChecked(True)
            else:
                self.after_checkBox.setChecked(False)

        else:  
            # so queue is stopped

            self.start_end_frame.show()
            self.limit_after_frame.hide()

            # start time
            # start_checkBox
            if queue_info_dict['start_time_enable'] == 'yes':
                self.start_checkBox.setChecked(True)
            else:
                self.start_checkBox.setChecked(False)

            hour, minute = queue_info_dict['start_time'].split(':')

            q_time = QTime(int(hour), int(minute))
            self.start_time_qDataTimeEdit.setTime(q_time)

            # end time
            # end_checkBox
            if queue_info_dict['end_time_enable'] == 'yes':
                self.end_checkBox.setChecked(True)
            else:
                self.end_checkBox.setChecked(False)

            hour, minute = queue_info_dict['end_time'].split(':')
            # set time
            q_time = QTime(int(hour), int(minute))
            self.end_time_qDateTimeEdit(q_time)

            # reverse_checkBox
            if queue_info_dict['reverse'] == 'yes':
                self.reverse_checkBox.setChecked(True)
            else:
                self.reverse_checkBox.setChecked(False)

        self.limitFrame(category)
        self.afterFrame(category)
        self.startFrame(category)
        self.endFrame(category)

# this method opens issues page in github
    def reportIssue(self, menu):
        osCommands.xdgOpen('https://github.com/persepolisdm/persepolis/issues')

# this method opens persepolis wiki page in github
    def persepolisHelp(self, menu):
        osCommands.xdgOpen('https://github.com/persepolisdm/persepolis/wiki')


# this method opens update menu
    def newUpdate(self, menu):
        checkupdatewindow = checkupdate(
            self.persepolis_setting)
        self.checkupdatewindow_list.append(checkupdatewindow)
        self.checkupdatewindow_list[len(
            self.checkupdatewindow_list) - 1].show()


# this method opens LogWindow 
    def showLog(self, menu):
        logwindow = LogWindow(
            self.persepolis_setting)
        self.logwindow_list.append(logwindow)
        self.logwindow_list[len(
            self.logwindow_list) - 1].show()


# this method is called when user pressed moveUpAction
# this method subtituts selected download item with upper one
    def moveUp(self, menu):
        global button_pressed_counter
        button_pressed_counter = button_pressed_counter + 1
# if checking_flag is equal to 1, it means that user pressed remove or
# delete button or ... . so checking download information must be stopped
# until job is done!

        if checking_flag != 2:
            button_pressed_thread = ButtonPressedThread()
            self.threadPool.append(button_pressed_thread)
            self.threadPool[len(self.threadPool) - 1].start()

            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.moveUp2)
        else:
            self.moveUp2()

    def moveUp2(self):
        # find user's selected row
        old_row = self.selectedRow()  

        # current_category_tree_text is the name of queue that selected by user
        current_category_tree_text = str(current_category_tree_index.data())

        # an old row and new row must replaced  by each other
        if old_row:
            new_row = int(old_row) - 1
            if new_row >= 0:

                # get gid_list from data base
                category_dict = self.persepolis_db.searchCategoryInCategoryTable(
                        current_category_tree_text)

                gid_list = category_dict['gid_list']

                # old index and new index of item in gid_list
                old_index = len(gid_list) - old_row - 1
                new_index = old_index + 1

                # subtitute two gid with each other
                gid_list[old_index], gid_list[new_index] = gid_list[new_index], gid_list[old_index]

                # save changes in data base
                self.persepolis_db.updateCategoryTable([category_dict])

                # subtitute items in download_table
                old_row_items_list = []
                new_row_items_list = []

                # read current items in download_table
                for i in range(13):
                    old_row_items_list.append(
                        self.download_table.item(old_row, i).text())
                    new_row_items_list.append(
                        self.download_table.item(new_row, i).text())

                # replacing
                for i in range(13):
                    # old row
                    item = QTableWidgetItem(new_row_items_list[i])

                    self.download_table.setItem(old_row, i, item)

                    # new row
                    item = QTableWidgetItem(old_row_items_list[i])
                    self.download_table.setItem(new_row, i, item)

                self.download_table.selectRow(new_row)



# this method is called when user pressed moveUpSelectedAction
# this method subtituts selected  items with upper one

    def moveUpSelected(self, menu):
        global button_pressed_counter
        button_pressed_counter = button_pressed_counter + 1
# if checking_flag is equal to 1, it means that user pressed remove or
# delete button or ... . so checking download information must be stopped
# until job is done!

        if checking_flag != 2:
            button_pressed_thread = ButtonPressedThread()
            self.threadPool.append(button_pressed_thread)
            self.threadPool[len(self.threadPool) - 1].start()

            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.moveUpSelected2)
        else:
            self.moveUpSelected2()

    def moveUpSelected2(self):
        index_list = []

        # current_category_tree_text is the name of queue that selected by user
        current_category_tree_text = str(current_category_tree_index.data())

        # get gid_list from data base
        category_dict = self.persepolis_db.searchCategoryInCategoryTable(
                        current_category_tree_text)

        gid_list = category_dict['gid_list']

        # find checked rows
        for row in range(self.download_table.rowCount()):
            item = self.download_table.item(row, 0)
            if (item.checkState() == 2):
                # append index of checked rows to index_list
                index_list.append(row)

        # move up selected rows
        for old_row in index_list:
            new_row = int(old_row) - 1
            if new_row >= 0:

                # old index and new index of item in gid_list
                old_index = len(gid_list) - old_row - 1
                new_index = old_index + 1

                # subtitute items in gid_list
                gid_list[old_index], gid_list[new_index] = gid_list[new_index], gid_list[old_index]

                # subtitute items in download_table
                # read current items in download_table
                for i in range(13):
                    old_row_items_list.append(
                        self.download_table.item(old_row, i).text())

                    new_row_items_list.append(
                        self.download_table.item(new_row, i).text())

                # subtituting
                for i in range(13):
                    # old row
                    item = QTableWidgetItem(new_row_items_list[i])
                    # add checkbox
                    if i == 0:
                        item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                      QtCore.Qt.ItemIsEnabled)
                        # set Unchecked
                        item.setCheckState(QtCore.Qt.Unchecked)

                    self.download_table.setItem(old_row, i, item)

                    # new row
                    item = QTableWidgetItem(old_row_items_list[i])
                    # add checkbox
                    if i == 0:
                        item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                      QtCore.Qt.ItemIsEnabled)
                        # set Checked
                        item.setCheckState(QtCore.Qt.Checked)

                    self.download_table.setItem(new_row, i, item)

        # update data base
        self.persepolis_db.updateCategoryTable([category_dict])



# this method is called if user pressed moveDown action
# this method is subtituting selected download item with lower download item
    def moveDown(self, menu):
        global button_pressed_counter
        button_pressed_counter = button_pressed_counter + 1
# if checking_flag is equal to 1, it means that user pressed remove or
# delete button or ... . so checking download information must be stopped
# until job is done!
        if checking_flag != 2:
            button_pressed_thread = ButtonPressedThread()
            self.threadPool.append(button_pressed_thread)
            self.threadPool[len(self.threadPool) - 1].start()

            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.moveDown2)
        else:
            self.moveDown2()

    def moveDown2(self):
        # find user's selected row
        old_row = self.selectedRow()  

        # current_category_tree_text is the name of queue that selected by user
        current_category_tree_text = str(current_category_tree_index.data())

        # an old row and new row must be subtituted by each other
        if old_row:
            new_row = int(old_row) + 1
            if new_row < self.download_table.rowCount():

                # get gid_list from data base
                category_dict = self.persepolis_db.searchCategoryInCategoryTable(
                        current_category_tree_text)

                gid_list = category_dict['gid_list']

                # old index and new index of item in gid_list
                old_index = len(gid_list) - old_row - 1
                new_index = old_index - 1

                # subtitute two gids in gid_list 
                gid_list[old_index], gid_list[new_index] = gid_list[new_index], gid_list[old_index]

                # update data base
                self.persepolis_db.updateCategoryTable([category_dict])
            
                # subtitute items in download_table
                old_row_items_list = []
                new_row_items_list = []

                # read current items in download_table
                for i in range(13):
                    old_row_items_list.append(
                        self.download_table.item(old_row, i).text())

                    new_row_items_list.append(
                        self.download_table.item(new_row, i).text())

                # subtituting
                for i in range(13):
                    # old_row
                    item = QTableWidgetItem(new_row_items_list[i])
                    self.download_table.setItem(old_row, i, item)

                    # new_row
                    item = QTableWidgetItem(old_row_items_list[i])
                    self.download_table.setItem(new_row, i, item)
                self.download_table.selectRow(new_row)


# this method is called if user pressed moveDownSelected action
# this method is subtituting selected download item with lower download item
    def moveDownSelected(self, menu):
        global button_pressed_counter
        button_pressed_counter = button_pressed_counter + 1
# if checking_flag is equal to 1, it means that user pressed remove or
# delete button or ... . so checking download information must be stopped
# until job is done!
        if checking_flag != 2:
            button_pressed_thread = ButtonPressedThread()
            self.threadPool.append(button_pressed_thread)
            self.threadPool[len(self.threadPool) - 1].start()

            wait_check = WaitThread()
            self.threadPool.append(wait_check)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) -
                            1].QTABLEREADY.connect(self.moveDownSelected2)
        else:
            self.moveDownSelected2()

    def moveDownSelected2(self):

        # an old row and new row must be subtituted by each other
        index_list = []

        # current_category_tree_text is the name of queue that selected by user
        current_category_tree_text = str(current_category_tree_index.data())

        # get gid_list from data base
        category_dict = self.persepolis_db.searchCategoryInCategoryTable(
                current_category_tree_text)

        gid_list = category_dict['gid_list']

        # find checked rows
        for row in range(self.download_table.rowCount()):
            item = self.download_table.item(row, 0)
            if (item.checkState() == 2):
                # append index of checked rows to index_list
                index_list.append(row)

        index_list.reverse()

        # move up selected rows
        for old_row in index_list:

            new_row = int(old_row) + 1
            if new_row < self.download_table.rowCount():

                # old index and new index in gid_list
                old_index = len(gid_list) - old_row - 1
                new_index = old_index - 1

                # subtitute gids in gid_list
                gid_list[old_inde], gid_list[new_index] = gid_list[new_index], gid_list[old_index]

                # subtitute items in download_table
                old_row_items_list = []
                new_row_items_list = []

                # read current items in download_table
                for i in range(13):
                    old_row_items_list.append(
                        self.download_table.item(old_row, i).text())

                    new_row_items_list.append(
                        self.download_table.item(new_row, i).text())

                # subtituting
                for i in range(13):
                    # old row
                    item = QTableWidgetItem(new_row_items_list[i])

                    # add checkbox
                    if i == 0:
                        item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                      QtCore.Qt.ItemIsEnabled)
                        # set Unchecked
                        item.setCheckState(QtCore.Qt.Unchecked)

                    self.download_table.setItem(old_row, i, item)

                    # new_row
                    item = QTableWidgetItem(old_row_items_list[i])

                    # add checkbox
                    if i == 0:
                        item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                      QtCore.Qt.ItemIsEnabled)
                        # set Checked
                        item.setCheckState(QtCore.Qt.Checked)

                    self.download_table.setItem(new_row, i, item)

        # update data base
        self.persepolis_db.updateCategoryTable([category_dict])
            
        

#######
# see flashgot_queue.py file
    def queueSpiderCallBack(self, filename, child, row_number):
        item = QTableWidgetItem(str(filename))

        # add checkbox to the item
        item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        if child.links_table.item(int(row_number), 0).checkState() == 2:
            item.setCheckState(QtCore.Qt.Checked)
        else:
            item.setCheckState(QtCore.Qt.Unchecked)

        child.links_table.setItem(int(row_number), 0, item)

# see addlink.py file
    def addLinkSpiderCallBack(self, filesize, child):

        if str(filesize) != '***':
            filesize = 'Size: ' + str(filesize)
            child.size_label.setText(filesize)


