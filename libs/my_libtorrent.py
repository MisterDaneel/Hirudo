#!/usr/bin/python2.7

from threading import Thread, activeCount
import libtorrent as lt
from time import sleep, time
import sys
import os

sys.dont_write_bytecode = True

state_str = ['queued', 'checking', 'downloading metadata', 'downloading',
             'finished', 'seeding', 'allocating', 'checking fastresume']


#
# TORRENT THREAD
#
class TORRENTTHREAD(Thread):
    toStop = False

    #
    # Init
    # param: torrent_file: string
    #
    def __init__(self, torrentFile):
        super(TORRENTTHREAD, self).__init__()
        self.output = os.path.dirname(torrentFile)
        self.torrentFile = torrentFile
        self.info = lt.torrent_info(torrentFile)
        # GUI
        self.EditGui = None
        self.ItemGui = None
        self.PrintStatus = False
        # Replace tracker parameters
        self.replacePasskey = False
        self.userPasskey = ''
        self.leechPasskey = ''
        # Limits
        self.downloadLimit = 9000000
        self.uploadLimit = 500000

    #
    # Print a message
    # param: message: string
    #
    def Print(self, message):
        if self.EditGui:
            self.EditGui(self.ItemGui, message)
        if self.PrintStatus:
            print self.info.name() + ' - ' + message
            self.PrintStatus = False

    #
    # Get Torrent name
    #
    def GetTorrentName(self):
        return self.info.name()

    #
    # Print torrent status
    #
    def GetStatus(self):
        self.PrintStatus = True

    #
    # Set Gui Function
    # param: EditGui, type: Function
    #
    def SetEditGui(self, EditGui):
        self.EditGui = EditGui

    #
    # Set Edit Gui item
    # param: item, type: string
    #
    def SetItem(self, item):
        self.ItemGui = item

    #
    # Set download limit
    # param: downloadLimit, type: int
    #
    def SetDownloadLimit(self, downloadLimit):
        self.downloadLimit = downloadLimit

    #
    # Set upload limit
    # param: uploadLimite, type: int
    #
    def SetUploadLimit(self, uploadLimit):
        self.uploadLimit = uploadLimit

    #
    # Set output path
    # param: output, type: string
    #
    def SetOutput(self, output):
        self.output = output

    #
    # Set undesirable and new trackersi
    # param userPasskey, type: string
    # param leechPasskey, type: string
    #
    def SetPasskey(self, userPasskey, leechPasskey):
        if userPasskey and leechPasskey:
            self.userPasskey = userPasskey
            self.leechPasskey = leechPasskey
            self.replacePasskey = True

    #
    # Start
    #
    def run(self):
        # New Session
        # fingerprint = lt.fingerprint("AZ", 3, 0, 5, 0)
        # settings = lt.session_settings()
        # settings.user_agent = "Azerus 3.0.5.0"
        # ses = lt.session(fingerprint)
        ses = lt.session()
        ses.listen_on(6881, 6891)
        self.torrentHandle = ses.add_torrent({
            'ti': self.info,
            'save_path': self.output,
        })
        self.torrentHandle.set_download_limit(10000)
        self.torrentHandle.set_upload_limit(self.uploadLimit)
        self.torrentHandle.set_sequential_download(True)
        # New Torrent
        torrentName = self.torrentHandle.name()
        self.Print('INITIALISATION')
        # Replace Tracker
        if self.replacePasskey:
            self.trHack()
        # Downloading
        if(not self.torrentHandle.is_seed()):
            self.Downloading()
        del ses
        # Stop if needed
        if self.toStop:
            return
        # Complete
        self.PrintStatus = True
        self.Print('COMPLETED')
        os.remove(self.torrentFile)

    #
    # Replace a user passkey after peering and download with a new one
    #
    def trHack(self):
        newTorrentTrackers = []
        for tracker in self.torrentHandle.trackers():
            if self.userPasskey in tracker['url']:
                tracker['url'] = self.leechPasskey
            newTorrentTrackers.append(tracker)
        # Peering
        if len(newTorrentTrackers) > 0:
            if (self.torrentHandle.status().num_peers < 1) and\
               not self.torrentHandle.is_seed():
                self.Peering()
            self.torrentHandle.replace_trackers(newTorrentTrackers)

    #
    # Get peers list
    #
    def Peering(self):
        torrentStatus = self.torrentHandle.status()
        start = time()
        while (not self.toStop and (torrentStatus.num_peers < 1) and
               not self.torrentHandle.is_seed() and
               not torrentStatus.paused):
            if (torrentStatus.state == 1):
                infosSTR = '%.2f%% %s' % (torrentStatus.progress * 100,
                                          state_str[torrentStatus.state])
            else:
                infosSTR = 'Checking for peers: %d' %\
                           (torrentStatus.num_peers)
            now = time()
            if now-start > 60:
                self.toStop = True
                self.PrintStatus = True
                infoSTR = 'NO PEERS FOUND'
                break
            self.Print(infosSTR)
            sleep(.5)
            torrentStatus = self.torrentHandle.status()
        if torrentStatus.paused and torrentStatus.error:
            self.toStop = True
            self.PrintStatus = True
            self.Print(torrentStatus.error)

    #
    # Downloading
    #
    def Downloading(self):
        torrentStatus = self.torrentHandle.status()
        while (not self.toStop and not self.torrentHandle.is_seed()):
            if (torrentStatus.state == 1):
                infosSTR = '%.2f%% %s' % (torrentStatus.progress * 100,
                                          state_str[torrentStatus.state])
            else:
                infosSTR = ('%.2f%% (down: %.1f kb/s up:' +
                            '%.1f kB/s peers: %d)) %s') %\
                           (torrentStatus.progress * 100,
                            torrentStatus.download_rate / 1000,
                            torrentStatus.upload_rate / 1000,
                            torrentStatus.num_peers,
                            state_str[torrentStatus.state])
            self.Print(infosSTR)
            sleep(.1)
            torrentStatus = self.torrentHandle.status()
            self.torrentHandle.set_download_limit(self.downloadLimit)

    #
    # Stop
    #
    def Stop(self):
        self.toStop = True
        self.Print('STOPPED')
        return
