import json, time, unittest
import manager
class RistJsonTests(unittest.TestCase):
    def sample(self, age=1):
        body={'schema_version':5,'receiver-stats':{'flowinstant':{'stats':{'received':480,'lost':0,'missing':0,'recovered_total':0,'retries':0,'quality':100,'bitrate':5177682},'peers':[{'dead':0,'stats':{'received_data':480,'rtt':4.68,'avg_rtt':4.2}}]}}}
        return str(time.time()-age)+'|0.0|[INFO] '+json.dumps(body,separators=(',',':'))
    def test_values(self):
        x=manager.rist_json_metrics(self.sample())
        self.assertEqual(x['rtt_ms'],4.68)
        self.assertEqual(x['lost'],0)
        self.assertIsNone(x['loss_pct'])
        self.assertEqual(x['rist_kbps'],5177.7)
        self.assertTrue(x['active_peer'])
    def test_stale(self): self.assertIsNone(manager.rist_json_metrics(self.sample(60)))
    def test_invalid(self): self.assertIsNone(manager.rist_json_metrics('hello'))
if __name__=='__main__': unittest.main()
