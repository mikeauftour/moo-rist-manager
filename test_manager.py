import unittest
from unittest.mock import patch
import manager

class ManagerTests(unittest.TestCase):
    def test_log_state_no_false_positive_from_startup(self):
        self.assertEqual(manager.connection_state('Initialized Receiver Peer, listening mode ...\nEAP Authentication enabled'), 'Nicht nachgewiesen')
    def test_log_state_connected(self):
        self.assertEqual(manager.connection_state('peer connected'), 'Verbunden (Loghinweis)')
    def test_log_state_disconnected(self):
        self.assertEqual(manager.connection_state('peer connected\npeer disconnected'), 'Getrennt')
    def test_port_conflict(self):
        with patch.object(manager, 'docker', return_value=[{'Names':['/other'], 'Ports':[{'PublicPort':2031,'Type':'udp'}]}]):
            self.assertEqual(manager.port_conflict(2031), '/other')
    def test_default_main(self):
        with patch.object(manager, 'FILE', __import__('pathlib').Path('/nonexistent-moo-manager-test/state.json')):
            s=manager.load()
        self.assertEqual((s['streams'][0]['in'],s['streams'][0]['out']), (2030,5556))

if __name__ == '__main__':
    unittest.main()

class TrafficTests(unittest.TestCase):
    def setUp(self):
        manager.TRAFFIC_SAMPLES.clear()
    def test_receiver_network_delta(self):
        packets = iter([{'id':'abc','networks':{'eth0':{'rx_bytes':10000}}}, {'id':'abc','networks':{'eth0':{'rx_bytes':110000}}}])
        with patch.object(manager, 'docker', side_effect=lambda *args: next(packets)), patch.object(manager.time, 'monotonic', side_effect=[10, 15]):
            first = manager.receiver_traffic(1, 'moo-single-1-rx')
            second = manager.receiver_traffic(1, 'moo-single-1-rx')
        self.assertEqual(first['state'], 'Messung läuft')
        self.assertEqual(second['rate_kbps'], 160.0)
    def test_receiver_restart_resets_measurement(self):
        packets = iter([{'id':'abc','networks':{'eth0':{'rx_bytes':10000}}}, {'id':'def','networks':{'eth0':{'rx_bytes':20000}}}])
        with patch.object(manager, 'docker', side_effect=lambda *args: next(packets)), patch.object(manager.time, 'monotonic', side_effect=[10, 15]):
            manager.receiver_traffic(1, 'rx')
            second = manager.receiver_traffic(1, 'rx')
        self.assertIsNone(second['rate_kbps'])

class QualityTests(unittest.TestCase):
    def test_missing(self):
        self.assertIsNone(manager.rist_log_metrics('Initialized Receiver Peer, rtt-min=70')['rtt_ms'])
    def test_explicit(self):
        v=manager.rist_log_metrics('peer rtt: 45.2 ms; packet loss: 1.5%')
        self.assertEqual(v['rtt_ms'],45.2)
        self.assertEqual(v['loss_pct'],1.5)
