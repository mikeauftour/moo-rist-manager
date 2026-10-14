import json,time,unittest
import manager
class OfflineTests(unittest.TestCase):
 def test_zero_peer_event(self):
  self.assertEqual(manager.connection_state('peer connected count is 1\nConnection Status changed, peer connected count is 0'),'Getrennt')
 def test_latest_reconnect(self):
  self.assertEqual(manager.connection_state('peer connected count is 0\npeer connected count is 1'),'Verbunden (Loghinweis)')
 def test_dead_flow(self):
  payload={'schema_version':5,'receiver-stats':{'flowinstant':{'dead':2,'stats':{'received':0,'bitrate':53378,'quality':100},'peers':[{'dead':0,'stats':{'received_data':0,'rtt':38.2}}]}}}
  result=manager.rist_json_metrics(f'{time.time()}|0|[INFO] '+json.dumps(payload,separators=(',',':')))
  self.assertEqual(result['flow_dead'],2)
  self.assertFalse(result['active_peer'])
 def test_active_flow(self):
  payload={'schema_version':5,'receiver-stats':{'flowinstant':{'dead':0,'stats':{'received':500,'bitrate':5000000},'peers':[{'dead':0,'stats':{'received_data':500,'rtt':5}}]}}}
  result=manager.rist_json_metrics(f'{time.time()}|0|[INFO] '+json.dumps(payload,separators=(',',':')))
  self.assertTrue(result['active_peer'])
if __name__=='__main__':unittest.main()
