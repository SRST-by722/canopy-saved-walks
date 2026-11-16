"""Integration checks against the running local Canopy API, not internet services."""
import json,os,unittest,urllib.request,urllib.error

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=os.environ.get('CANOPY_TEST_URL','http://127.0.0.1:8811')
        cls.meta=json.load(urllib.request.urlopen(cls.base+'/api/pedestrian/meta'))
    def request(self,value):
        r=urllib.request.Request(self.base+'/api/pedestrian/plan',data=json.dumps(value).encode(),headers={'Content-Type':'application/json'})
        return urllib.request.urlopen(r,timeout=120)
    def test_canopy_source_and_longest_duration(self):
        m=self.meta
        self.assertEqual(m['summary']['environmental_exclusions'],0)
        self.assertIn('vector_landscape/source/scene-meta.json',m['provenance']['source'])
        self.assertEqual(m['journey_horizon_s'],46800)
        with self.request(dict(origin=m['example'][0],goal=m['example'][1],departure_s=0,max_minutes=780)) as response:
            result=json.load(response)
        self.assertTrue(result['cvae_enabled'])
        self.assertEqual(result['signal_mode'],'modelled_pedestrian_plus_recorded_vehicle_gaps')
        self.assertEqual(len(result['routes'][1]['timeline'][0]['points'][0]),3)
    def test_out_of_coverage_is_rejected(self):
        for start,minutes in [(0,781),(240,777),(46800,1)]:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request(dict(origin=self.meta['example'][0],goal=self.meta['example'][1],departure_s=start,max_minutes=minutes))
            self.assertEqual(error.exception.code,400)
    def test_connectivity_metadata_matches_roads_and_real_gaps_are_rejected(self):
        m=self.meta;components=m['node_components'];origin=m['example'][0]
        self.assertEqual(set(components),set(m['nodes']))
        self.assertEqual(len(m['road_components']),len(m['roads']))
        goal=next(n for n in m['nodes'] if components[n]!=components[origin])
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request(dict(origin=origin,goal=goal,departure_s=0,max_minutes=780))
        self.assertEqual(error.exception.code,400)
        self.assertIn('disconnected',json.load(error.exception)['error'])
    def test_long_journey_restored_with_repeating_environment(self):
        body=dict(origin='0:0:0:1801.2097,-712.0518',goal='0:0:0:2027.5000,237.5000',departure_s=240,max_minutes=776)
        with self.request(body) as response:result=json.load(response)
        self.assertGreater(result['routes'][1]['duration_s'],600)
        self.assertTrue(result['environment']['replay'])
        self.assertIsNone(result['wave_audit'][1]['failure'])
    def test_private_files_and_traversal_are_not_served(self):
        for path in ['/pedestrian/private/breathing_model/scaler.json','/pedestrian/cache/default-plan.json','/viewer/3d/pedestrian/../../../pedestrian/private/breathing_model/scaler.json']:
            for method in ['GET','HEAD']:
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(urllib.request.Request(self.base+path,method=method))
                self.assertEqual(error.exception.code,403)

if __name__=='__main__':unittest.main()
