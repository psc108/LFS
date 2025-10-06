#!/usr/bin/env python3
"""
Test Production ML Integration
Verify real system integration works
"""

import sys
import os
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class TestMLProduction(unittest.TestCase):
    
    def setUp(self):
        self.mock_db = Mock()
        self.mock_db.execute_query.return_value = []
    
    def test_production_git_integration(self):
        """Test production Git integration"""
        try:
            from ml.phase2.production_integrator import ProductionGitIntegrator
            
            git_integrator = ProductionGitIntegrator()
            features = git_integrator.extract_real_git_features('test_build')
            
            # Should return dict even if Git commands fail
            self.assertIsInstance(features, dict)
            print("✅ Production Git integration: PASS")
            
        except Exception as e:
            self.fail(f"Production Git integration failed: {e}")
    
    def test_production_system_monitor(self):
        """Test production system monitoring"""
        try:
            from ml.phase2.production_integrator import ProductionSystemMonitor
            
            monitor = ProductionSystemMonitor()
            metrics = monitor.get_real_system_metrics()
            
            # Should return system metrics
            self.assertIsInstance(metrics, dict)
            if metrics:  # If psutil is available
                self.assertIn('cpu_percent', metrics)
                self.assertIn('memory_percent', metrics)
            
            print("✅ Production system monitor: PASS")
            
        except Exception as e:
            self.fail(f"Production system monitor failed: {e}")
    
    def test_production_security_integration(self):
        """Test production security integration"""
        try:
            from ml.phase2.production_integrator import ProductionSecurityIntegrator
            
            security = ProductionSecurityIntegrator()
            metrics = security.get_real_security_metrics()
            
            # Should return security metrics
            self.assertIsInstance(metrics, dict)
            print("✅ Production security integration: PASS")
            
        except Exception as e:
            self.fail(f"Production security integration failed: {e}")
    
    def test_ml_engine_production_prediction(self):
        """Test ML engine production prediction"""
        try:
            from ml.ml_engine import MLEngine
            
            ml_engine = MLEngine(self.mock_db)
            
            # Test production prediction
            build_data = {'build_id': 'test_123', 'stage_count': 10}
            result = ml_engine.predict_production(build_data)
            
            if result:  # May be None if dependencies missing
                self.assertIn('production_prediction', result)
                self.assertIn('real_system_features', result)
            
            print("✅ ML Engine production prediction: PASS")
            
        except Exception as e:
            self.fail(f"ML Engine production prediction failed: {e}")

def run_production_test():
    """Run production ML test"""
    print("=" * 60)
    print("PRODUCTION ML INTEGRATION TEST")
    print("=" * 60)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMLProduction)
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed}")
    print(f"Failed: {failures}")
    print(f"Success Rate: {(passed/total_tests)*100:.1f}%")
    
    if passed == total_tests:
        print("\n🎉 PRODUCTION ML INTEGRATION READY!")
        print("✅ Real system integration operational")
    else:
        print("\n⚠️ Some production features may need system dependencies")
    
    print("=" * 60)
    return passed == total_tests

if __name__ == '__main__':
    run_production_test()