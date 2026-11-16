import sys,unittest,math,json,struct
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'pedestrian'),str(ROOT/'pedestrian/health_planning')]
from traffic_gaps import ClearWindows,TrafficGapGate,RecordedTrafficGaps,mark_sweeps,shapely,SPATIAL_MARGIN_M
from walk_signal_schedule import WalkGate,WalkProgram
from zero_speed_entrance_wave import solve_crossing
from zero_speed_history_wave import solve as wave_solve
from destination_wave import solve,timed_path
from test_destination_wave import network,Costs

def gate(blocked,period=600):
    return TrafficGapGate(WalkGate('test',WalkProgram(1,1000,20,origin_s=-1)),ClearWindows(blocked,period))

class GapTests(unittest.TestCase):
 def test_full_crossing_and_clearance_not_just_entry(self):
    g=gate([(5,15)])
    self.assertFalse(g.permitted(0,4)) # car arrives before the 2 s clearance ends
    self.assertEqual(g.next_entry(0,4,30),15)
    self.assertTrue(g.permitted(15,4));self.assertTrue(g.permitted(0,3))
    self.assertIsNone(g.next_entry(0,4,18))
 def test_signal_and_vehicle_conditions_both_required(self):
    signal=WalkGate('test',WalkProgram(10,5,10,origin_s=0))
    g=TrafficGapGate(signal,ClearWindows([(10,16)]))
    self.assertEqual(g.next_entry(0,4,100),35)
    self.assertFalse(g.permitted(16,4))
    d=g.wait_details(0,4,100,35)
    self.assertEqual(d['signal_only_wait_s'],10);self.assertEqual(d['traffic_extra_wait_s'],25)
 def test_repeat_seam_and_whole_horizon(self):
    w=ClearWindows([(0,4),(598,600)])
    self.assertFalse(w.clear(595,5));self.assertFalse(w.clear(599,5));self.assertTrue(w.clear(604,5))
    self.assertFalse(w.clear(1199,5));self.assertTrue(w.clear(46204,5))
    self.assertEqual(gate([(0,600)]).next_entry(0,4,46800),None)
 def test_jump_wait_keeps_closed_wave_zero_and_releases_at_exact_time(self):
    g=gate([(0,15)])
    a=solve_crossing(8,g,departure=0,arrival_s=.3,dt_requested=.125,horizon_s=50)
    self.assertTrue(a['feasible']);self.assertEqual(a['entry_s'],15)
    self.assertAlmostEqual(a['wait_s'],14.7);self.assertAlmostEqual(a['detected_finish_s'],21,places=7)
    self.assertEqual(a['closed_field_max'],0);self.assertEqual(a['stored_packet_change'],0)
    self.assertFalse(solve_crossing(8,g,horizon_s=10)['feasible'])
 def test_wave_carries_wait_cost_exposure_and_physiological_time(self):
    n,e,d=network([('s','g',8)]);g=gate([(0,15)])
    path,a=wave_solve(n,e,'s','g',d,Costs(),gates={('s','g'):g},duration_s=50,dt_s=.125)
    self.assertEqual(path,[('s','g')]);self.assertAlmostEqual(a['trace'][-1]['physical_s'],21)
    self.assertEqual(a['trace'][-1]['wait_s'],15)
    self.assertEqual(a['carried_parts'][0],21);self.assertEqual(a['carried_exposure'],21)
    self.assertEqual(a['terminal_delay_added_s'],0)
 def test_wave_chooses_clear_detour_over_traffic_wait(self):
    n,e,d=network([('s','g',8),('s','a',8),('a','g',8)])
    gates={('s','g'):gate([(0,30)]),('g','s'):gate([(0,30)])}
    path,a=solve(n,e,'s','g',d,Costs(),gates=gates,duration_s=60)
    self.assertEqual(path,[('s','a'),('a','g')]);self.assertEqual(a['carried_parts'][0],12)
    fastest,t=timed_path(e,'s','g',gates,0,60);self.assertEqual(fastest,path);self.assertEqual(t,12)
 def test_sweeps_catch_fast_vehicle_and_bus_body(self):
    tree=shapely.STRtree([shapely.LineString([(0,-2),(0,2)])])
    self.assertEqual(mark_sweeps(tree,np.array([[-20.,0]]),np.array([[20.,0]]),np.array([3.])).tolist(),[0])
    point=np.array([[6.,0.]])
    self.assertEqual(mark_sweeps(tree,point,point,np.array([math.hypot(2.25,.925)+SPATIAL_MARGIN_M])).tolist(),[])
    self.assertEqual(mark_sweeps(tree,point,point,np.array([math.hypot(5.75,1.25)+SPATIAL_MARGIN_M])).tolist(),[0])
 def test_no_phantom_sweep_at_replay_teleport(self):
    # Motion across the saved loop boundary must not invent a path through x=0.
    frames=[[(0,20.,0.,0.)],[(0,20.,0.,0.)],[],[(0,-20.,0.,0.)]]
    raw=b''.join(struct.pack('<I',len(f))+b''.join(struct.pack('<Ifff',*v) for v in f) for f in frames)
    m=dict(frames=4,vehicles=[dict(type='car')])
    mask=RecordedTrafficGaps.build(raw,m,[dict(points=[[0,-2],[0,2]])])
    self.assertFalse(mask.any())
 def test_stopped_vehicle_blocks_repeated_frames(self):
    raw=b''.join(struct.pack('<I',1)+struct.pack('<Ifff',0,0.,0.,0.) for _ in range(4))
    mask=RecordedTrafficGaps.build(raw,dict(frames=4,vehicles=[dict(type='car')]),[dict(points=[[0,-2],[0,2]])])
    self.assertTrue(mask.all())

if __name__=='__main__':unittest.main()
