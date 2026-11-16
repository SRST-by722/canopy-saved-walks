import sys,unittest
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'health_planning'))
from walking_cost_search import Edge
from zero_speed_history_wave import solve as wave_solve
from destination_wave import solve,timed_path
from walk_signal_schedule import WalkGate,WalkProgram

class Costs:
    initial=0.;departure=0.;reference_objective=1.;neutral=False
    def edge(self,e,state,elapsed):
        duration=e.length/(4/3)
        return state+duration,np.array([duration,0.,0.]),duration
    def wait(self,point,state,elapsed,duration):
        return state+duration,np.array([duration,0.,0.]),duration

def network(rows):
    edges={};nodes={}
    for u,v,length in rows:
        nodes[u]=[0,0,0,0];nodes[v]=[length,0,0,0]
        points=np.array([[0.,0.,0.,0.],[length,0.,0.,0.]])
        edges[u,v]=Edge(u,v,points,np.array([0.,length]),'test')
        edges[v,u]=Edge(v,u,points[::-1],np.array([0.,length]),'test')
    return nodes,edges,{k:1. for k in edges}

class DestinationWaveTests(unittest.TestCase):
    def test_sub_bucket_path_sections_are_not_lost(self):
        n,e,d=network([('s','a',.02),('a','g',.02)])
        path,a=wave_solve(n,e,'s','g',d,Costs(),dt_s=.125,duration_s=10)
        self.assertEqual(path,[('s','a'),('a','g')])
        self.assertAlmostEqual(a['trace'][-1]['physical_s'],.03)

    def test_budget_keeps_already_emitted_destination_packet(self):
        n,e,d=network([('s','a_goal',10),('s','b',1),('s','c',1),('b','d',1)])
        path,a=wave_solve(n,e,'s','a_goal',d,Costs(),max_records=3)
        self.assertEqual(path,[('s','a_goal')]);self.assertTrue(a['truncated'])
        self.assertIsNone(a['failure']);self.assertEqual(a['records'],3)

    def test_feasible_candidate_survives_tiny_refinement_budget_and_wave_horizon(self):
        n,e,d=network([('s','a',2),('a','g',2),('s','b',3),('b','g',3)])
        gate=WalkGate('light',WalkProgram(red_s=4,green_s=2,clearance_s=4,origin_s=0))
        gates={('a','g'):gate,('g','a'):gate}
        path,a=solve(n,e,'s','g',d,Costs(),gates=gates,max_records=2,duration_s=30,max_wave_time=.1)
        self.assertIsNotNone(path);self.assertIsNone(a['failure'])
        self.assertTrue(a['search_limited']);self.assertFalse(a['search_complete'])
        self.assertEqual(a['selected_from'],'validated_candidate_wave')
        self.assertGreater(a['carried_parts'][0],.1)
        self.assertLessEqual(a['trace'][-1]['physical_s'],30)

    def test_true_duration_failure_is_distinct_from_search_budget(self):
        n,e,d=network([('s','a',2),('a','g',2)])
        gate=WalkGate('light',WalkProgram(red_s=4,green_s=2,clearance_s=4,origin_s=0))
        gates={('a','g'):gate}
        path,a=solve(n,e,'s','g',d,Costs(),gates=gates,duration_s=3)
        self.assertIsNone(path);self.assertEqual(a['failure'],'journey_duration')
        timed,arrival=timed_path(e,'s','g',gates,0,30)
        self.assertEqual(timed,[('s','a'),('a','g')]);self.assertAlmostEqual(arrival,5.5)

if __name__=='__main__':unittest.main()
