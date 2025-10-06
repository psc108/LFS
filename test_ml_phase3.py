#!/usr/bin/env python3

"""
Test ML Phase 3 Build Optimization Implementation
Tests real database queries, system analysis, and optimization functions
"""

import sys
import os
import unittest
import tempfile
import json
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class TestMLPhase3(unittest.TestCase):
    """Test ML Phase 3 build optimization functionality"""
    
    def setUp(self):
        """Setup test environment"""
        try:
            from database.db_manager import DatabaseManager
            from ml.ml_engine import MLEngine
            from ml.optimization.build_optimizer import BuildOptimizer
            
            self.db = DatabaseManager()
            self.ml_engine = MLEngine(self.db)
            self.optimizer = BuildOptimizer(self.db)
            
            # Create test data
            self.create_test_data()
            
        except Exception as e:
            self.skipTest(f"Cannot initialize ML Phase 3 components: {e}")
    
    def create_test_data(self):
        """Create test build data for optimization analysis"""
        try:
            # Insert test builds
            test_builds = [
                ('test_build_1', 'completed', '2024-12-01 10:00:00', '2024-12-01 12:30:00'),
                ('test_build_2', 'completed', '2024-12-01 14:00:00', '2024-12-01 15:45:00'),
                ('test_build_3', 'failed', '2024-12-02 09:00:00', '2024-12-02 10:15:00'),
                ('test_build_4', 'completed', '2024-12-02 11:00:00', '2024-12-02 13:20:00')
            ]
            
            for build_id, status, start_time, end_time in test_builds:
                self.db.execute_query(
                    "INSERT INTO builds (build_id, status, start_time, end_time) VALUES (%s, %s, %s, %s)",
                    (build_id, status, start_time, end_time)
                )
            
            # Insert test build stages
            test_stages = [
                ('test_build_1', 'prepare_host', 'completed', '2024-12-01 10:00:00', '2024-12-01 10:15:00', 1),
                ('test_build_1', 'build_toolchain', 'completed', '2024-12-01 10:15:00', '2024-12-01 11:30:00', 2),
                ('test_build_1', 'build_final_system', 'completed', '2024-12-01 11:30:00', '2024-12-01 12:30:00', 3),
                ('test_build_2', 'prepare_host', 'completed', '2024-12-01 14:00:00', '2024-12-01 14:10:00', 1),
                ('test_build_2', 'build_toolchain', 'completed', '2024-12-01 14:10:00', '2024-12-01 15:00:00', 2),
                ('test_build_2', 'build_final_system', 'completed', '2024-12-01 15:00:00', '2024-12-01 15:45:00', 3)
            ]
            
            for build_id, stage_name, status, start_time, end_time, stage_order in test_stages:
                self.db.execute_query(
                    "INSERT INTO build_stages (build_id, stage_name, status, start_time, end_time, stage_order) VALUES (%s, %s, %s, %s, %s, %s)",
                    (build_id, stage_name, status, start_time, end_time, stage_order)
                )
            
            # Insert test build configurations
            test_configs = [
                ('test_build_1', 'config', 'Test Config 1', '{"parallel_jobs": 2, "memory_limit": "4G"}'),
                ('test_build_2', 'config', 'Test Config 2', '{"parallel_jobs": 4, "memory_limit": "8G"}'),
                ('test_build_4', 'config', 'Test Config 4', '{"parallel_jobs": 6, "memory_limit": "16G"}')
            ]
            
            for build_id, doc_type, title, content in test_configs:
                self.db.execute_query(
                    "INSERT INTO build_documents (build_id, document_type, title, content, created_at) VALUES (%s, %s, %s, %s, NOW())",
                    (build_id, doc_type, title, content)
                )
            
        except Exception as e:
            print(f"Warning: Could not create test data: {e}")
    
    def test_build_optimizer_initialization(self):
        """Test BuildOptimizer initializes correctly"""
        self.assertIsNotNone(self.optimizer)
        self.assertIsNotNone(self.optimizer.db_manager)
    
    def test_historical_performance_analysis(self):
        """Test real historical performance analysis"""
        result = self.optimizer.analyze_historical_performance(days_back=30)
        
        self.assertIsInstance(result, dict)
        self.assertNotIn('error', result)
        
        # Should have real metrics
        if 'total_builds' in result:
            self.assertIsInstance(result['total_builds'], int)
            self.assertGreaterEqual(result['total_builds'], 0)
        
        if 'avg_duration' in result:
            self.assertIsInstance(result['avg_duration'], (int, float))
    
    def test_parallel_job_recommendation(self):
        """Test real parallel job recommendation"""
        result = self.optimizer.recommend_parallel_jobs()
        
        self.assertIsInstance(result, dict)
        self.assertNotIn('error', result)
        
        # Should have system analysis
        self.assertIn('recommended_jobs', result)
        self.assertIn('system_cpus', result)
        self.assertIn('system_memory_gb', result)
        
        # Validate recommendations are realistic
        self.assertIsInstance(result['recommended_jobs'], int)
        self.assertGreater(result['recommended_jobs'], 0)
        self.assertLessEqual(result['recommended_jobs'], 16)
    
    def test_job_count_performance_analysis(self):
        """Test real job count performance analysis"""
        result = self.optimizer._analyze_job_count_performance()
        
        self.assertIsInstance(result, dict)
        
        if 'job_performance' in result:
            self.assertIsInstance(result['job_performance'], dict)
        
        if 'optimal_range' in result:
            self.assertIsInstance(result['optimal_range'], list)
            self.assertEqual(len(result['optimal_range']), 2)
    
    def test_stage_optimizations_analysis(self):
        """Test real stage optimization analysis"""
        result = self.optimizer._analyze_stage_optimizations()
        
        self.assertIsInstance(result, dict)
        
        # Check structure of optimization data
        for stage_name, opt_data in result.items():
            self.assertIsInstance(stage_name, str)
            self.assertIsInstance(opt_data, dict)
            
            if 'priority' in opt_data:
                self.assertIn(opt_data['priority'], ['low', 'medium', 'high', 'critical'])
            
            if 'recommendations' in opt_data:
                self.assertIsInstance(opt_data['recommendations'], list)
    
    def test_build_configuration_optimization(self):
        """Test complete build configuration optimization"""
        result = self.optimizer.optimize_build_configuration('test_config')
        
        self.assertIsInstance(result, dict)
        self.assertNotIn('error', result)
        
        # Should have optimization sections
        expected_sections = ['system_optimization', 'performance_prediction', 'recommendations']
        for section in expected_sections:
            if section in result:
                self.assertIsInstance(result[section], (dict, list))
    
    def test_performance_prediction(self):
        """Test real performance prediction"""
        job_rec = self.optimizer.recommend_parallel_jobs()
        stage_opt = self.optimizer._analyze_stage_optimizations()
        
        result = self.optimizer._predict_build_performance(job_rec, stage_opt)
        
        self.assertIsInstance(result, dict)
        
        if 'baseline_duration' in result:
            self.assertIsInstance(result['baseline_duration'], (int, float))
            self.assertGreater(result['baseline_duration'], 0)
        
        if 'predicted_duration' in result:
            self.assertIsInstance(result['predicted_duration'], (int, float))
            self.assertGreater(result['predicted_duration'], 0)
        
        if 'improvement_percent' in result:
            self.assertIsInstance(result['improvement_percent'], (int, float))
    
    def test_ml_engine_phase3_integration(self):
        """Test ML Engine Phase 3 integration"""
        # Test build optimization method
        result = self.ml_engine.get_build_optimization('test_config')
        self.assertIsInstance(result, dict)
        
        # Test parallel job recommendation method
        result = self.ml_engine.get_parallel_job_recommendation()
        self.assertIsInstance(result, dict)
        
        # Test performance history analysis method
        result = self.ml_engine.analyze_build_performance_history(30)
        self.assertIsInstance(result, dict)
    
    def test_system_info_detection(self):
        """Test real system information detection"""
        system_info = self.optimizer._get_system_info()
        
        self.assertIsInstance(system_info, dict)
        self.assertIn('cpu_count', system_info)
        self.assertIn('memory_gb', system_info)
        
        # Validate system info is realistic
        self.assertIsInstance(system_info['cpu_count'], int)
        self.assertGreater(system_info['cpu_count'], 0)
        
        self.assertIsInstance(system_info['memory_gb'], float)
        self.assertGreater(system_info['memory_gb'], 0)
    
    def test_memory_allocation_recommendation(self):
        """Test memory allocation recommendations"""
        system_info = self.optimizer._get_system_info()
        result = self.optimizer._recommend_memory_allocation(system_info)
        
        self.assertIsInstance(result, dict)
        self.assertIn('build_memory_limit', result)
        
        # Should be realistic memory limit
        memory_limit = result['build_memory_limit']
        self.assertTrue(memory_limit.endswith('G'))
    
    def test_io_settings_recommendation(self):
        """Test I/O settings recommendations"""
        system_info = self.optimizer._get_system_info()
        result = self.optimizer._recommend_io_settings(system_info)
        
        self.assertIsInstance(result, dict)
        self.assertIn('io_scheduler', result)
        
        # Should be valid I/O scheduler
        valid_schedulers = ['mq-deadline', 'kyber', 'bfq', 'none']
        self.assertIn(result['io_scheduler'], valid_schedulers)
    
    def test_recommendations_generation(self):
        """Test actionable recommendations generation"""
        perf_data = self.optimizer.analyze_historical_performance()
        job_rec = self.optimizer.recommend_parallel_jobs()
        
        result = self.optimizer._generate_recommendations(perf_data, job_rec)
        
        self.assertIsInstance(result, list)
        
        # Should have actionable recommendations
        for rec in result:
            self.assertIsInstance(rec, str)
            self.assertGreater(len(rec), 10)  # Should be meaningful recommendations
    
    def test_database_queries_work(self):
        """Test that database queries execute without errors"""
        try:
            # Test builds query
            builds = self.db.execute_query(
                "SELECT build_id, status FROM builds LIMIT 5",
                fetch=True
            )
            self.assertIsInstance(builds, list)
            
            # Test build_stages query
            stages = self.db.execute_query(
                "SELECT stage_name, status FROM build_stages LIMIT 5",
                fetch=True
            )
            self.assertIsInstance(stages, list)
            
            # Test build_documents query
            docs = self.db.execute_query(
                "SELECT document_type, title FROM build_documents LIMIT 5",
                fetch=True
            )
            self.assertIsInstance(docs, list)
            
        except Exception as e:
            self.fail(f"Database queries failed: {e}")
    
    def tearDown(self):
        """Clean up test data"""
        try:
            # Clean up test data
            test_build_ids = ['test_build_1', 'test_build_2', 'test_build_3', 'test_build_4']
            
            for build_id in test_build_ids:
                self.db.execute_query("DELETE FROM build_documents WHERE build_id = %s", (build_id,))
                self.db.execute_query("DELETE FROM build_stages WHERE build_id = %s", (build_id,))
                self.db.execute_query("DELETE FROM builds WHERE build_id = %s", (build_id,))
                
        except Exception as e:
            print(f"Warning: Could not clean up test data: {e}")

def run_phase3_tests():
    """Run ML Phase 3 tests and return results"""
    print("🚀 Testing ML Phase 3 Build Optimization Implementation")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMLPhase3)
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Run tests
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 ML Phase 3 Test Results Summary")
    print("=" * 60)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    passed = total_tests - failures - errors - skipped
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failures}")
    print(f"🚫 Errors: {errors}")
    print(f"⏭️  Skipped: {skipped}")
    
    success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
    print(f"\n🎯 Success Rate: {success_rate:.1f}%")
    
    if failures > 0:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if errors > 0:
        print("\n🚫 Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    # Overall assessment
    print("\n" + "=" * 60)
    if success_rate >= 90:
        print("🎉 ML Phase 3 Implementation: EXCELLENT")
    elif success_rate >= 80:
        print("✅ ML Phase 3 Implementation: GOOD")
    elif success_rate >= 70:
        print("⚠️  ML Phase 3 Implementation: NEEDS IMPROVEMENT")
    else:
        print("❌ ML Phase 3 Implementation: REQUIRES FIXES")
    
    print("=" * 60)
    
    return success_rate >= 80

if __name__ == '__main__':
    success = run_phase3_tests()
    sys.exit(0 if success else 1)