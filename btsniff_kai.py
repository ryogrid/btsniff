#!/usr/bin/env python

import os
import sys
import time
from base64 import b32encode
from os import path

sys.path.append(path.dirname("/usr/lib/python2.7/dist-packages/"))

import libtorrent as lt
import threading
import socket
import traceback

threading.stack_size(200*1024)
socket.setdefaulttimeout(30)

class Btsniff:
    def __init__(self):
        self.ses = None
        self.serial = 0L
        self.info_hashes = {}

    def fetch_torrent(self, session, ih, timeout):
        name = ih.upper()
        url = 'magnet:?xt=urn:btih:%s' % (name,)
        print("fetch_torrent: url = " + url)
        data = ''
        params = {
            'save_path': './torrents/',
            'storage_mode': lt.storage_mode_t(2),
            'paused': False,
            'auto_managed': False,
            'duplicate_is_error': True}
        try:
            handle = lt.add_magnet_uri(session, url, params)
        except:
            return None
        status = session.status()
        handle.queue_position_top()        
        handle.set_sequential_download(1)
        meta = None
        #down_time = time.time()
        #down_path = None
        for i in xrange(0, timeout):
            if handle.has_metadata():
                info = handle.get_torrent_info()
                #down_path = './torrents/%s' % info.name()
                meta = info.metadata()
                print("got torrent!")
                break
            time.sleep(1)
            s = handle.status()
            print("fetching metadata [%s]..." % (s.state))
            print("target => " + str(s.name))
        # if down_path and os.path.exists(down_path):
        #     os.system('rm -rf "%s"' % down_path)
        #     session.remove_torrent(handle)
        return meta


#    def download_metadata(self, address, binhash, metadata_queue, timeout=40):
    def download_metadata(self, binhash, timeout=40):
        metadata = None
        start_time = time.time()
        try:
            #session = lt.session()
            #r = random.randrange(10000, 50000)
            # session.listen_on(r, r+10)
            # session.add_dht_router('router.bittorrent.com',6881)
            # session.add_dht_router('router.utorrent.com',6881)
            # session.add_dht_router('dht.transmission.com',6881)
            # session.add_dht_router('127.0.0.1',6881)
            # session.start_dht()
            metadata = self.fetch_torrent(self.ses, binhash.encode('hex'), timeout)
            #session = None
        except:
            traceback.print_exc()
        # finally:
        #     metadata_queue.put((binhash, address, metadata, 'lt', start_time))

    def start(self, torrent_file, port=6881):
        if not os.path.isdir('log'):
            os.mkdir('log')

        print("libtorrent version: " + lt.version)
        self.ses = lt.session()
        #self.ses.set_alert_mask(lt.alert.category_t.status_notification | 0x400) # lt.alert.category_t.dh
        self.ses.set_alert_mask(lt.alert.category_t.all_categories)
        self.ses.start_dht()
        self.ses.add_dht_router("router.bittorrent.com", 6881)
        self.ses.add_dht_router("router.utorrent.com", 6881)
        self.ses.add_dht_router("router.bitcomet.com", 6881)
        self.ses.add_dht_router('dht.transmission.com',6881) #added rkan
        self.ses.add_dht_router('127.0.0.1',6881) # added rkan

        info = lt.torrent_info(torrent_file)
        h = self.ses.add_torrent({'ti': info, 'save_path': './'})

        s = h.status()
        print('starting', s.name)

        while not h.is_seed():
            alert = self.ses.pop_alert()
            while alert is not None:
                self.handle_alert(alert)
                alert = self.ses.pop_alert()
            time.sleep(0.1)

        self.ses.remove_torrent(h)

        while True:
            alert = self.ses.pop_alert()
            while alert is not None:
                self.handle_alert(alert)
                alert = self.ses.pop_alert()
            time.sleep(0.1)

    def handle_alert(self, alert):
        alert_type = type(alert).__name__
        print "[%s] %s" % (alert_type, alert.message())

        if alert_type == 'dht_get_peers_alert':
            print "[%s] %s" % (alert_type, alert.message())
            try:
                info_hash = alert.info_hash.to_string()
            except:
                return

            self.serial += 1
            if not info_hash in self.info_hashes:
                self.info_hashes[info_hash] = {'serial': self.serial, 'unixtime': time.time()}
            else:
                return

            meta = self.download_metadata(alert.info_hash.to_bytes(), 40)
            print("downloaded metadata of " + info_hash + " : " + str(meta))
            
            #h = self.ses.add_torrent({'info_hash': alert.info_hash.to_bytes(), 'save_path': './'})
            #h.queue_position_top()
        elif alert_type == 'metadata_received_alert':
            print "[%s] %s" % (alert_type, alert.message())
            h = alert.handle
            info_hash = str(h.info_hash())
            if h.is_valid():
                ti = h.get_torrent_info()
                serial = self.info_hashes[info_hash]['serial']
                unixtime = self.info_hashes[info_hash]['unixtime']
                line = '\t'.join([
                        str(serial),
                        time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(unixtime)),
                        info_hash,
                        str(ti.total_size()),
                        str(ti.num_files()),
                        ti.name(),
                        ti.comment(),
                        ti.creator(),
                ])
                fpath = time.strftime('log/btsniff-%Y%m%d.log', time.localtime(unixtime))
                with open(fpath, 'a') as f:
                    print >>f, line
                    f.flush()
                self.ses.remove_torrent(h, 1) # session::delete_files
        elif alert_type == 'torrent_added_alert':
            print "[%s] %s" % (alert_type, alert.message())
        elif alert_type == 'add_torrent_alert':
            print "[%s] %s" % (alert_type, alert.message())

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print >>sys.stderr, "Usage: python %s TORRENT_FILE" % sys.argv[0]
        sys.exit(1)
    torrent_file = sys.argv[1]

    btsniff = Btsniff()
    btsniff.start(torrent_file)
