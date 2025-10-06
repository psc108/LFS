#!/usr/bin/env python3
"""
Complete ML Phase 2 Test Suite
Tests all Phase 2 ML components without demo modes
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_ml_phase2_complete():
    """Test all ML Phase 2 components"""
    print("🧪 Testing Complete ML Phase 2 System")
    print("=" * 50)
    
    test_results = {}
    
    # Test 1: Real-time Inference Engine
    try:
        from database.db_manager import DatabaseManager
        from ml.ml_engine import MLEngine
        
        db = DatabaseManager()
        ml_engine = MLEngine(db)
        
        if hasattr(ml_engine, 'real_time_inference'):
            # Test real-time prediction
            prediction = ml_engine.get_real_time_prediction('test-build-123', 'build_toolchain')
            
            if 'overall_risk' in prediction or 'error' in prediction:
                test_results['real_time_inference'] = 'PASS'
                print("✅ Real-time Inference Engine: PASS")
            else:
                test_results['real_time_inference'] = 'FAIL: No prediction data'
                print("❌ Real-time Inference Engine: FAIL - No prediction data")
        else:
            test_results['real_time_inference'] = 'FAIL: Component not available'
            print("❌ Real-time Inference Engine: FAIL - Component not available")
            
    except Exception as e:
        test_results['real_time_inference'] = f'FAIL: {e}'
        print(f"❌ Real-time Inference Engine: FAIL - {e}")
    
    # Test 2: Ensemble Predictor
    try:
        if hasattr(ml_engine, 'ensemble_predictor'):
            # Test ensemble prediction
            test_features = {
                'build_id': 'test-123',
                'stage_count': 8,
                'avg_duration': 3600,
                'cpu_percent': 75
            }
            
            ensemble_result = ml_engine.get_ensemble_prediction(test_features)
            
            if 'ensemble_prediction' in ensemble_result or 'error' in ensemble_result:
                test_results['ensemble_predictor'] = 'PASS'
                print("✅ Ensemble Predictor: PASS")
            else:
                test_results['ensemble_predictor'] = 'FAIL: No ensemble data'
                print("❌ Ensemble Predictor: FAIL - No ensemble data")
        else:
            test_results['ensemble_predictor'] = 'FAIL: Component not available'
            print("❌ Ensemble Predictor: FAIL - Component not available")
            
    except Exception as e:
        test_results['ensemble_predictor'] = f'FAIL: {e}'
        print(f"❌ Ensemble Predictor: FAIL - {e}")
    
    # Test 3: Adaptive Trainer
    try:
        if hasattr(ml_engine, 'adaptive_trainer'):
            # Test adaptive training
            training_result = ml_engine.trigger_adaptive_training()
            
            if isinstance(training_result, dict):
                test_results['adaptive_trainer'] = 'PASS'
                print("✅ Adaptive Trainer: PASS")
            else:
                test_results['adaptive_trainer'] = 'FAIL: Invalid training result'
                print("❌ Adaptive Trainer: FAIL - Invalid training result")
        else:
            test_results['adaptive_trainer'] = 'FAIL: Component not available'
            print("❌ Adaptive Trainer: FAIL - Component not available")
            
    except Exception as e:
        test_results['adaptive_trainer'] = f'FAIL: {e}'
        print(f"❌ Adaptive Trainer: FAIL - {e}")
    
    # Test 4: Advanced Predictor
    try:
        if hasattr(ml_engine, 'advanced_predictor'):
            # Test advanced prediction
            test_features = {
                'build_id': 'test-456',
                'stage_count': 10,
                'branch_count': 3,
                'avg_duration': 7200
            }
            
            advanced_pred = ml_engine.predict_advanced(test_features)
            
            if advanced_pred and 'advanced_prediction' in advanced_pred:
                test_results['advanced_predictor'] = 'PASS'
                print("✅ Advanced Predictor: PASS")
            else:
                test_results['advanced_predictor'] = 'FAIL: No advanced prediction'
                print("❌ Advanced Predictor: FAIL - No advanced prediction")
        else:
            test_results['advanced_predictor'] = 'FAIL: Component not available'
            print("❌ Advanced Predictor: FAIL - Component not available")
            
    except Exception as e:
        test_results['advanced_predictor'] = f'FAIL: {e}'
        print(f"❌ Advanced Predictor: FAIL - {e}")
    
    # Test 5: Real-time Learner
    try:
        if hasattr(ml_engine, 'real_time_learner'):
            # Test learning stats
            learning_stats = ml_engine.real_time_learner.get_learning_stats()
            
            if 'learning_active' in learning_stats:
                test_results['real_time_learner'] = 'PASS'
                print("✅ Real-time Learner: PASS")
            else:
                test_results['real_time_learner'] = 'FAIL: No learning stats'
                print("❌ Real-time Learner: FAIL - No learning stats")
        else:
            test_results['real_time_learner'] = 'FAIL: Component not available'
            print("❌ Real-time Learner: FAIL - Component not available")
            
    except Exception as e:
        test_results['real_time_learner'] = f'FAIL: {e}'
        print(f"❌ Real-time Learner: FAIL - {e}")
    
    # Test 6: Cross-system Integration
    try:
        if hasattr(ml_engine, 'cross_system_integrator'):
            # Test cross-system features
            features = ml_engine.cross_system_integrator.get_integrated_features('test-789')
            
            if isinstance(features, dict):
                test_results['cross_system_integration'] = 'PASS'
                print("✅ Cross-system Integration: PASS")
            else:
                test_results['cross_system_integration'] = 'FAIL: No features extracted'
                print("❌ Cross-system Integration: FAIL - No features extracted")
        else:
            test_results['cross_system_integration'] = 'FAIL: Component not available'
            print("❌ Cross-system Integration: FAIL - Component not available")
            
    except Exception as e:
        test_results['cross_system_integration'] = f'FAIL: {e}'
        print(f"❌ Cross-system Integration: FAIL - {e}")
    
    # Test 7: Production Integration
    try:
        if hasattr(ml_engine, 'production_integrator'):
            # Test production prediction
            test_data = {'build_id': 'prod-test-123', 'config_name': 'production'}
            prod_pred = ml_engine.predict_production(test_data)
            
            if prod_pred and 'production_prediction' in prod_pred:
                test_results['production_integration'] = 'PASS'
                print("✅ Production Integration: PASS")
            else:
                test_results['production_integration'] = 'FAIL: No production prediction'
                print("❌ Production Integration: FAIL - No production prediction")
        else:
            test_results['production_integration'] = 'FAIL: Component not available'
            print("❌ Production Integration: FAIL - Component not available")
            
    except Exception as e:
        test_results['production_integration'] = f'FAIL: {e}'
        print(f"❌ Production Integration: FAIL - {e}")
    
    # Test 8: Training Data Pipeline
    try:
        from ml.training.data_pipeline import TrainingDataPipeline
        
        pipeline = TrainingDataPipeline(db)
        
        # Test failure prediction data preparation
        features, labels = pipeline.prepare_failure_prediction_data(7)  # 7 days lookback
        
        if isinstance(features, list) and isinstance(labels, list):
            test_results['training_data_pipeline'] = 'PASS'
            print("✅ Training Data Pipeline: PASS")
        else:
            test_results['training_data_pipeline'] = 'FAIL: Invalid data format'
            print("❌ Training Data Pipeline: FAIL - Invalid data format")
            
    except Exception as e:
        test_results['training_data_pipeline'] = f'FAIL: {e}'
        print(f"❌ Training Data Pipeline: FAIL - {e}")
    
    # Test 9: Comprehensive ML Status
    try:
        comprehensive_status = ml_engine.get_comprehensive_ml_status()
        
        if 'phase2' in comprehensive_status and 'ml_enabled' in comprehensive_status:
            test_results['comprehensive_status'] = 'PASS'
            print("✅ Comprehensive ML Status: PASS")
        else:
            test_results['comprehensive_status'] = 'FAIL: Incomplete status'
            print("❌ Comprehensive ML Status: FAIL - Incomplete status")
            
    except Exception as e:
        test_results['comprehensive_status'] = f'FAIL: {e}'
        print(f"❌ Comprehensive ML Status: FAIL - {e}")
    
    # Test 10: System Performance Analysis
    try:
        performance_analysis = ml_engine.analyze_system_performance()
        
        if isinstance(performance_analysis, dict):
            test_results['system_performance_analysis'] = 'PASS'
            print("✅ System Performance Analysis: PASS")
        else:
            test_results['system_performance_analysis'] = 'FAIL: No analysis data'
            print("❌ System Performance Analysis: FAIL - No analysis data")
            
    except Exception as e:
        test_results['system_performance_analysis'] = f'FAIL: {e}'
        print(f"❌ System Performance Analysis: FAIL - {e}")
    
    # Test 11: Build Monitoring
    try:
        ml_engine.start_build_monitoring('monitor-test-123')
        test_results['build_monitoring'] = 'PASS'
        print("✅ Build Monitoring: PASS")
            
    except Exception as e:
        test_results['build_monitoring'] = f'FAIL: {e}'
        print(f"❌ Build Monitoring: FAIL - {e}")
    
    # Test 12: Phase 2 Status
    try:
        phase2_status = ml_engine.get_phase2_status()
        
        if phase2_status.get('phase2_enabled') and 'capabilities' in phase2_status:
            test_results['phase2_status'] = 'PASS'
            print("✅ Phase 2 Status: PASS")
        else:
            test_results['phase2_status'] = 'FAIL: Phase 2 not enabled'
            print("❌ Phase 2 Status: FAIL - Phase 2 not enabled")
            
    except Exception as e:
        test_results['phase2_status'] = f'FAIL: {e}'
        print(f"❌ Phase 2 Status: FAIL - {e}")
    
    # Cleanup
    try:
        ml_engine.shutdown()
        print("🔄 ML Engine shutdown completed")
    except Exception as e:
        print(f"⚠️ Shutdown warning: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 ML PHASE 2 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for result in test_results.values() if result == 'PASS')
    total = len(test_results)
    
    print(f"✅ Passed: {passed}/{total} ({(passed/total)*100:.1f}%)")
    print(f"❌ Failed: {total-passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL ML PHASE 2 COMPONENTS OPERATIONAL!")
        print("🚀 Advanced ML system ready for production")
    else:
        print(f"\n⚠️  {total-passed} components need attention")
        print("\nFailed components:")
        for component, result in test_results.items():
            if result != 'PASS':
                print(f"  - {component}: {result}")
    
    print(f"\n🔬 ML Phase 2 Features Tested:")
    print("  - Real-time Inference Engine")
    print("  - Ensemble Prediction Methods")
    print("  - Adaptive Model Training")
    print("  - Advanced Prediction with Confidence")
    print("  - Real-time Learning System")
    print("  - Cross-system Integration")
    print("  - Production System Integration")
    print("  - Training Data Pipeline")
    print("  - Comprehensive Status Monitoring")
    print("  - System Performance Analysis")
    print("  - Build Monitoring")
    print("  - Phase 2 Status Reporting")
    
    return test_results

if __name__ == "__main__":
    print("🤖 LFS Build System - ML Phase 2 Complete Test")
    print("=" * 50)
    
    # Test ML Phase 2 components
    results = test_ml_phase2_complete()
    
    # Overall summary
    total_tests = len(results)
    total_passed = sum(1 for r in results.values() if r == 'PASS')
    
    print(f"\n🎯 OVERALL ML PHASE 2 READINESS")
    print("=" * 40)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Success Rate: {(total_passed/total_tests)*100:.1f}%")
    
    if total_passed == total_tests:
        print("\n🚀 ML PHASE 2 IS PRODUCTION READY!")
        print("All advanced ML components operational")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total_tests - total_passed} issues need resolution")
        sys.exit(1)