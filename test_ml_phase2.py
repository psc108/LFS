#!/usr/bin/env python3
"""
Phase 2 ML System Test
Verify advanced ML capabilities are working
"""

import sys
import os
import unittest
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class TestMLPhase2(unittest.TestCase):
    """Test Phase 2 ML system capabilities"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_db = Mock()
        self.mock_db.execute_query.return_value = []
        self.mock_db.fetch_all.return_value = []
    
    def test_advanced_predictor(self):
        """Test advanced predictor with confidence intervals"""
        try:
            from ml.phase2.advanced_predictor import AdvancedPredictor
            
            predictor = AdvancedPredictor(self.mock_db)
            
            test_features = {
                'stage_count': 10,
                'avg_duration': 7200,
                'branch_count': 3,
                'success_rate': 0.8
            }
            
            result = predictor.predict_with_confidence(test_features)
            
            # Verify result structure
            self.assertIn('prediction', result)
            self.assertIn('confidence_interval', result)
            self.assertIn('uncertainty_score', result)
            self.assertIsInstance(result['confidence_interval'], tuple)
            
            print("✅ Advanced predictor: PASS")
            
        except Exception as e:
            self.fail(f"Advanced predictor test failed: {e}")
    
    def test_real_time_learner(self):
        """Test real-time learning system"""
        try:
            from ml.phase2.real_time_learner import RealTimeLearner
            
            mock_ml_engine = Mock()
            learner = RealTimeLearner(mock_ml_engine, self.mock_db)
            
            # Test learning lifecycle
            learner.start_learning()
            self.assertTrue(learner.learning_active)
            
            # Add feedback
            learner.add_feedback('build_1', {'prediction': 0.3}, 'success')
            self.assertEqual(len(learner.feedback_queue), 1)
            
            # Get stats
            stats = learner.get_learning_stats()
            self.assertIn('learning_active', stats)
            self.assertIn('total_feedback', stats)
            
            learner.stop_learning()
            self.assertFalse(learner.learning_active)
            
            print("✅ Real-time learner: PASS")
            
        except Exception as e:
            self.fail(f"Real-time learner test failed: {e}")
    
    def test_cross_system_integration(self):
        """Test cross-system ML integration"""
        try:
            from ml.phase2.cross_system_integrator import CrossSystemIntegrator
            
            integrator = CrossSystemIntegrator(self.mock_db)
            
            # Test feature extraction
            features = integrator.get_integrated_features('build_1')
            self.assertIsInstance(features, dict)
            
            # Test impact prediction
            build_data = {'stage_count': 10, 'git_complexity_score': 0.3}
            impacts = integrator.predict_cross_system_impact(build_data)
            
            self.assertIn('git', impacts)
            self.assertIn('cicd', impacts)
            self.assertIn('security', impacts)
            
            print("✅ Cross-system integration: PASS")
            
        except Exception as e:
            self.fail(f"Cross-system integration test failed: {e}")
    
    def test_ml_engine_phase2_integration(self):
        """Test Phase 2 integration with main ML engine"""
        try:
            from ml.ml_engine import MLEngine
            
            ml_engine = MLEngine(self.mock_db)
            
            # Verify Phase 2 components exist
            self.assertTrue(hasattr(ml_engine, 'advanced_predictor'))
            self.assertTrue(hasattr(ml_engine, 'real_time_learner'))
            self.assertTrue(hasattr(ml_engine, 'cross_system_integrator'))
            
            # Test Phase 2 methods
            self.assertTrue(hasattr(ml_engine, 'predict_advanced'))
            self.assertTrue(hasattr(ml_engine, 'get_phase2_status'))
            
            # Test Phase 2 status
            status = ml_engine.get_phase2_status()
            self.assertIn('phase2_enabled', status)
            self.assertTrue(status['phase2_enabled'])
            
            print("✅ ML Engine Phase 2 integration: PASS")
            
        except Exception as e:
            self.fail(f"ML Engine Phase 2 integration test failed: {e}")

def run_phase2_test():
    """Run Phase 2 ML system test"""
    print("=" * 60)
    print("PHASE 2 ML SYSTEM TEST")
    print("=" * 60)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMLPhase2)
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed}")
    print(f"Failed: {failures}")
    print(f"Errors: {errors}")
    print(f"Success Rate: {(passed/total_tests)*100:.1f}%")
    
    if passed == total_tests:
        print("\n🎉 PHASE 2 ML SYSTEM READY!")
        print("✅ Advanced ML capabilities operational")
    else:
        print("\n❌ Phase 2 needs attention")
    
    print("=" * 60)
    return passed == total_tests

if __name__ == '__main__':
    success = run_phase2_test()
    sys.exit(0 if success else 1)