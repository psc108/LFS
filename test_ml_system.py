#!/usr/bin/env python3
"""
Comprehensive ML System Test Suite
Tests all ML capabilities across the entire LFS system
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_ml_engine_initialization():
    """Test ML engine can be initialized and basic functionality works"""
    print("🧪 Testing ML Engine Initialization...")
    try:
        from ml.ml_engine import MLEngine
        from database.db_manager import DatabaseManager
        
        # Initialize database manager
        db_manager = DatabaseManager()
        engine = MLEngine(db_manager)
        print("✅ ML Engine initialized successfully")
        
        # Test basic health check
        health = engine.get_health_status()
        print(f"✅ Health Status: {health}")
        
        return True, engine
    except Exception as e:
        print(f"❌ ML Engine initialization failed: {e}")
        traceback.print_exc()
        return False, None

def test_feature_extraction(engine):
    """Test feature extraction from database"""
    print("\n🧪 Testing Feature Extraction...")
    try:
        features = engine.feature_extractor.extract_build_features()
        print(f"✅ Extracted {len(features)} build features")
        
        if features:
            sample = features[0]
            print(f"✅ Sample feature keys: {list(sample.keys())}")
        
        # Test system features
        sys_features = engine.feature_extractor.extract_system_features()
        print(f"✅ Extracted system features: {list(sys_features.keys())}")
        
        return True
    except Exception as e:
        print(f"❌ Feature extraction failed: {e}")
        traceback.print_exc()
        return False

def test_failure_prediction(engine):
    """Test failure prediction model"""
    print("\n🧪 Testing Failure Prediction...")
    try:
        # Test with sample build data
        build_data = {
            'stage_count': 10,
            'avg_stage_duration': 300,
            'system_load': 0.5,
            'memory_usage': 0.7,
            'disk_space': 0.8,
            'previous_failures': 2
        }
        
        prediction = engine.failure_predictor.predict_failure_risk(build_data)
        print(f"✅ Failure prediction: {prediction}")
        
        # Test batch prediction
        batch_data = [build_data, {**build_data, 'system_load': 0.9}]
        batch_predictions = engine.failure_predictor.predict_batch(batch_data)
        print(f"✅ Batch predictions: {batch_predictions}")
        
        return True
    except Exception as e:
        print(f"❌ Failure prediction failed: {e}")
        traceback.print_exc()
        return False

def test_performance_optimization(engine):
    """Test performance optimization recommendations"""
    print("\n🧪 Testing Performance Optimization...")
    try:
        # Test with sample performance data
        perf_data = {
            'build_duration': 7200,
            'cpu_cores': 4,
            'memory_gb': 8,
            'parallel_jobs': 2,
            'stage_durations': [300, 600, 1200, 900, 800, 700, 1000, 500, 400, 300]
        }
        
        recommendations = engine.performance_optimizer.get_recommendations(perf_data)
        print(f"✅ Performance recommendations: {recommendations}")
        
        # Test optimization scoring
        score = engine.performance_optimizer.calculate_efficiency_score(perf_data)
        print(f"✅ Efficiency score: {score}")
        
        return True
    except Exception as e:
        print(f"❌ Performance optimization failed: {e}")
        traceback.print_exc()
        return False

def test_anomaly_detection(engine):
    """Test anomaly detection capabilities"""
    print("\n🧪 Testing Anomaly Detection...")
    try:
        # Test with sample system metrics
        metrics = {
            'cpu_usage': [20, 25, 30, 85, 90, 95],  # Spike in CPU
            'memory_usage': [40, 42, 45, 48, 50, 52],
            'disk_io': [100, 120, 110, 500, 480, 520],  # Spike in I/O
            'network_io': [50, 55, 60, 58, 62, 65]
        }
        
        anomalies = engine.anomaly_detector.detect_anomalies(metrics)
        print(f"✅ Detected anomalies: {anomalies}")
        
        # Test real-time detection
        current_metrics = {'cpu_usage': 95, 'memory_usage': 85, 'disk_io': 600}
        realtime_anomaly = engine.anomaly_detector.check_realtime_anomaly(current_metrics)
        print(f"✅ Real-time anomaly check: {realtime_anomaly}")
        
        return True
    except Exception as e:
        print(f"❌ Anomaly detection failed: {e}")
        traceback.print_exc()
        return False

def test_system_wide_insights(engine):
    """Test system-wide insights across all facilities"""
    print("\n🧪 Testing System-Wide Insights...")
    try:
        insights = engine.get_system_wide_insights()
        print(f"✅ Generated system-wide insights")
        
        # Check all expected facilities
        expected_facilities = ['git', 'security', 'deployment', 'cicd', 'collaboration', 'performance', 'database']
        
        for facility in expected_facilities:
            if facility in insights:
                facility_data = insights[facility]
                print(f"✅ {facility.upper()}: {facility_data.get('health_score', 'N/A')}% health")
                if 'recommendations' in facility_data:
                    print(f"   📋 {len(facility_data['recommendations'])} recommendations")
            else:
                print(f"⚠️  {facility.upper()}: No insights available")
        
        return True
    except Exception as e:
        print(f"❌ System-wide insights failed: {e}")
        traceback.print_exc()
        return False

def test_build_analysis_integration(engine):
    """Test integration with build analysis system"""
    print("\n🧪 Testing Build Analysis Integration...")
    try:
        from analysis.build_advisor import BuildAdvisor
        from database.db_manager import DatabaseManager
        
        db_manager = DatabaseManager()
        advisor = BuildAdvisor(db_manager)
        
        # Test ML-enhanced analysis
        analysis = advisor.analyze_build_history()
        print(f"✅ Build analysis completed")
        
        if 'ml_insights' in analysis:
            ml_insights = analysis['ml_insights']
            print(f"✅ ML insights included: {list(ml_insights.keys())}")
        else:
            print("⚠️  No ML insights in build analysis")
        
        return True
    except Exception as e:
        print(f"❌ Build analysis integration failed: {e}")
        traceback.print_exc()
        return False

def test_model_training_and_updates(engine):
    """Test model training and update capabilities"""
    print("\n🧪 Testing Model Training and Updates...")
    try:
        # Test model training
        training_result = engine.model_manager.train_models()
        print(f"✅ Model training result: {training_result}")
        
        # Test model updates
        update_result = engine.model_manager.update_models()
        print(f"✅ Model update result: {update_result}")
        
        # Test model versioning
        versions = engine.model_manager.get_model_versions()
        print(f"✅ Model versions: {versions}")
        
        return True
    except Exception as e:
        print(f"❌ Model training/updates failed: {e}")
        traceback.print_exc()
        return False

def test_ml_performance_metrics(engine):
    """Test ML system performance and metrics"""
    print("\n🧪 Testing ML Performance Metrics...")
    try:
        # Test prediction accuracy
        accuracy_metrics = engine.get_prediction_accuracy()
        print(f"✅ Prediction accuracy: {accuracy_metrics}")
        
        # Test processing speed
        start_time = time.time()
        for i in range(10):
            engine.get_system_wide_insights()
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 10
        print(f"✅ Average insight generation time: {avg_time:.3f}s")
        
        # Test memory usage
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        print(f"✅ ML engine memory usage: {memory_mb:.1f} MB")
        
        return True
    except Exception as e:
        print(f"❌ Performance metrics failed: {e}")
        traceback.print_exc()
        return False

def test_error_handling_and_graceful_degradation(engine):
    """Test error handling and graceful degradation"""
    print("\n🧪 Testing Error Handling and Graceful Degradation...")
    try:
        # Test with invalid data
        try:
            engine.failure_predictor.predict_failure_risk({})
            print("✅ Handled empty prediction data gracefully")
        except Exception as e:
            print(f"⚠️  Empty data handling: {e}")
        
        # Test with corrupted data
        try:
            corrupted_data = {'invalid': 'data', 'numbers': 'not_a_number'}
            engine.performance_optimizer.get_recommendations(corrupted_data)
            print("✅ Handled corrupted data gracefully")
        except Exception as e:
            print(f"⚠️  Corrupted data handling: {e}")
        
        # Test database connection failure simulation
        try:
            # Temporarily break database connection
            original_db = engine.feature_extractor.db_manager
            engine.feature_extractor.db_manager = None
            
            features = engine.feature_extractor.extract_build_features()
            print("✅ Graceful degradation with no database")
            
            # Restore connection
            engine.feature_extractor.db_manager = original_db
        except Exception as e:
            print(f"⚠️  Database failure handling: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        traceback.print_exc()
        return False

def test_integration_with_gui_components():
    """Test integration with GUI components"""
    print("\n🧪 Testing GUI Integration...")
    try:
        # Test if ML insights can be displayed in GUI
        from ml.ml_engine import MLEngine
        from database.db_manager import DatabaseManager
        
        db_manager = DatabaseManager()
        engine = MLEngine(db_manager)
        insights = engine.get_system_wide_insights()
        
        # Simulate GUI display formatting with error handling
        gui_formatted = {}
        for facility, data in insights.items():
            if isinstance(data, dict):
                gui_formatted[facility] = {
                    'status': f"{data.get('health_score', 0)}% Health",
                    'recommendations': len(data.get('recommendations', [])),
                    'alerts': len(data.get('alerts', []))
                }
            else:
                gui_formatted[facility] = {
                    'status': 'Data Available',
                    'recommendations': 0,
                    'alerts': 0
                }
        
        print(f"✅ GUI formatting successful: {len(gui_formatted)} facilities")
        
        return True
    except Exception as e:
        print(f"❌ GUI integration failed: {e}")
        traceback.print_exc()
        return False

def run_comprehensive_ml_test():
    """Run all ML system tests"""
    print("🚀 Starting Comprehensive ML System Test Suite")
    print("=" * 60)
    
    test_results = {}
    
    # Initialize ML engine
    success, engine = test_ml_engine_initialization()
    test_results['initialization'] = success
    
    if not success:
        print("\n❌ Cannot continue tests without ML engine")
        return test_results
    
    # Run all tests
    tests = [
        ('feature_extraction', lambda: test_feature_extraction(engine)),
        ('failure_prediction', lambda: test_failure_prediction(engine)),
        ('performance_optimization', lambda: test_performance_optimization(engine)),
        ('anomaly_detection', lambda: test_anomaly_detection(engine)),
        ('system_wide_insights', lambda: test_system_wide_insights(engine)),
        ('build_analysis_integration', lambda: test_build_analysis_integration(engine)),
        ('model_training', lambda: test_model_training_and_updates(engine)),
        ('performance_metrics', lambda: test_ml_performance_metrics(engine)),
        ('error_handling', lambda: test_error_handling_and_graceful_degradation(engine)),
        ('gui_integration', lambda: test_integration_with_gui_components())
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results[test_name] = result
        except Exception as e:
            print(f"\n❌ Test {test_name} crashed: {e}")
            test_results[test_name] = False
    
    # Print summary
    print("\n" + "=" * 60)
    print("🏁 ML System Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for result in test_results.values() if result)
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    print(f"\n📊 Overall Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All ML system tests passed! System is fully operational.")
    elif passed >= total * 0.8:
        print("⚠️  Most tests passed. Minor issues detected.")
    else:
        print("🚨 Significant issues detected. ML system needs attention.")
    
    return test_results

if __name__ == "__main__":
    results = run_comprehensive_ml_test()
    
    # Exit with appropriate code
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    if passed == total:
        sys.exit(0)  # All tests passed
    else:
        sys.exit(1)  # Some tests failed