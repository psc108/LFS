"""
Performance Optimizer Model

Optimizes build configurations based on historical performance data.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any


class PerformanceOptimizer:
    """Optimizes build performance based on historical analysis"""
    
    def __init__(self, db_manager):
        """Initialize performance optimizer"""
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self.is_trained_flag = False
        self.last_training_time = None
        self.accuracy = None
        self.prediction_count = 0
        
        # Performance patterns
        self.optimal_configs = {}
        self.performance_baselines = {}
        
        # Load existing patterns
        self._load_performance_patterns()
    
    def _load_performance_patterns(self):
        """Load performance patterns from database"""
        try:
            self._analyze_config_performance()
            self._analyze_timing_optimization()
            
            if self.optimal_configs:
                self.is_trained_flag = True
                self.last_training_time = datetime.now()
                self.logger.info("Loaded performance optimization patterns")
                
        except Exception as e:
            self.logger.error(f"Failed to load performance patterns: {e}")
    
    def _analyze_config_performance(self):
        """Analyze performance by configuration"""
        try:
            # Get performance data by configuration
            config_stats = self.db.execute_query(
                """SELECT config_name, 
                   AVG(duration_seconds) as avg_duration,
                   MIN(duration_seconds) as min_duration,
                   MAX(duration_seconds) as max_duration,
                   COUNT(*) as build_count,
                   SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count
                   FROM builds 
                   WHERE start_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                   AND duration_seconds IS NOT NULL
                   AND duration_seconds > 0
                   GROUP BY config_name
                   HAVING build_count >= 3""",
                fetch=True
            )
            
            for stat in config_stats:
                config_name = stat["config_name"]
                if not config_name:
                    continue
                
                self.optimal_configs[config_name] = {
                    "avg_duration": float(stat["avg_duration"]) if stat["avg_duration"] else 0.0,
                    "min_duration": float(stat["min_duration"]) if stat["min_duration"] else 0.0,
                    "max_duration": float(stat["max_duration"]) if stat["max_duration"] else 0.0,
                    "build_count": int(stat["build_count"]) if stat["build_count"] else 0,
                    "success_rate": float(stat["success_count"]) / float(stat["build_count"]) if stat["build_count"] else 0.0,
                    "efficiency_score": self._calculate_efficiency_score(stat)
                }
                
        except Exception as e:
            self.logger.error(f"Failed to analyze config performance: {e}")
    
    def _analyze_timing_optimization(self):
        """Analyze timing patterns for optimization"""
        try:
            # Get stage timing patterns
            stage_timings = self.db.execute_query(
                """SELECT bs.stage_name,
                   AVG(TIMESTAMPDIFF(SECOND, bs.start_time, bs.end_time)) as avg_duration,
                   MIN(TIMESTAMPDIFF(SECOND, bs.start_time, bs.end_time)) as min_duration,
                   COUNT(*) as execution_count
                   FROM build_stages bs
                   JOIN builds b ON bs.build_id = b.build_id
                   WHERE bs.start_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                   AND bs.status = 'completed'
                   AND b.status = 'success'
                   GROUP BY bs.stage_name
                   HAVING execution_count >= 5""",
                fetch=True
            )
            
            for timing in stage_timings:
                stage_name = timing["stage_name"]
                self.performance_baselines[stage_name] = {
                    "avg_duration": timing["avg_duration"],
                    "min_duration": timing["min_duration"],
                    "execution_count": timing["execution_count"],
                    "optimization_potential": self._calculate_optimization_potential(timing)
                }
                
        except Exception as e:
            self.logger.error(f"Failed to analyze timing optimization: {e}")
    
    def _calculate_efficiency_score(self, stats: Dict) -> float:
        """Calculate efficiency score for configuration"""
        success_rate = float(stats["success_count"]) / float(stats["build_count"]) if stats["build_count"] else 0.0
        
        avg_dur = float(stats["avg_duration"]) if stats["avg_duration"] else 1.0
        max_dur = float(stats["max_duration"]) if stats["max_duration"] else 0.0
        min_dur = float(stats["min_duration"]) if stats["min_duration"] else 0.0
        
        duration_consistency = 1.0 - ((max_dur - min_dur) / avg_dur) if avg_dur > 0 else 0.0
        duration_consistency = max(0.0, min(1.0, duration_consistency))
        
        # Combine success rate and consistency
        efficiency = (success_rate * 0.7) + (duration_consistency * 0.3)
        return efficiency
    
    def _calculate_optimization_potential(self, timing: Dict) -> float:
        """Calculate optimization potential for stage"""
        if timing["avg_duration"] <= 0 or timing["min_duration"] <= 0:
            return 0.0
        
        # Potential improvement based on best vs average performance
        potential = 1.0 - (timing["min_duration"] / timing["avg_duration"])
        return max(0.0, min(1.0, potential))
    
    def optimize(self, config_data: Dict) -> Optional[Dict]:
        """Generate optimization recommendations"""
        try:
            if not self.is_trained_flag:
                return None
            
            self.prediction_count += 1
            
            optimizations = {
                "config": {},
                "changes": [],
                "improvement_percent": 0.0,
                "confidence": 0.0
            }
            
            # Analyze current configuration
            current_config = config_data.get("build_config", {})
            config_name = config_data.get("build_info", {}).get("config_name")
            
            # Get optimization recommendations
            if config_name and config_name in self.optimal_configs:
                baseline = self.optimal_configs[config_name]
                optimizations.update(self._optimize_based_on_baseline(current_config, baseline))
            
            # Stage-specific optimizations
            stage_opts = self._optimize_stage_performance(config_data)
            if stage_opts:
                optimizations["changes"].extend(stage_opts["changes"])
                optimizations["improvement_percent"] += stage_opts["improvement_percent"]
            
            # Resource optimizations
            resource_opts = self._optimize_resource_usage(config_data)
            if resource_opts:
                optimizations["changes"].extend(resource_opts["changes"])
                optimizations["improvement_percent"] += resource_opts["improvement_percent"]
            
            # Calculate overall confidence
            optimizations["confidence"] = min(1.0, len(optimizations["changes"]) * 0.2)
            optimizations["improvement_percent"] = min(50.0, optimizations["improvement_percent"])
            
            return optimizations if optimizations["changes"] else None
            
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}")
            return None
    
    def _optimize_based_on_baseline(self, current_config: Dict, baseline: Dict) -> Dict:
        """Optimize based on baseline performance"""
        optimizations = {"changes": [], "improvement_percent": 0.0}
        
        # If efficiency is low, suggest improvements
        if baseline["efficiency_score"] < 0.8:
            optimizations["changes"].append({
                "type": "configuration",
                "description": "Consider using a more efficient build template",
                "impact": "medium",
                "expected_improvement": "15-25%"
            })
            optimizations["improvement_percent"] += 20.0
        
        # If duration variance is high, suggest consistency improvements
        duration_range = baseline["max_duration"] - baseline["min_duration"]
        if duration_range > baseline["avg_duration"] * 0.5:
            optimizations["changes"].append({
                "type": "consistency",
                "description": "Build times vary significantly - consider system resource optimization",
                "impact": "medium",
                "expected_improvement": "10-20%"
            })
            optimizations["improvement_percent"] += 15.0
        
        return optimizations
    
    def _optimize_stage_performance(self, config_data: Dict) -> Optional[Dict]:
        """Optimize individual stage performance"""
        optimizations = {"changes": [], "improvement_percent": 0.0}
        
        stages = config_data.get("stages", {})
        if not stages or "stage_sequence" not in stages:
            return None
        
        for stage in stages["stage_sequence"]:
            stage_name = stage.get("name", "")
            stage_duration = stage.get("duration", 0)
            
            if stage_name in self.performance_baselines:
                baseline = self.performance_baselines[stage_name]
                
                # If stage is taking much longer than baseline
                if stage_duration > baseline["avg_duration"] * 1.5:
                    optimizations["changes"].append({
                        "type": "stage_optimization",
                        "stage": stage_name,
                        "description": f"Stage '{stage_name}' is slower than average",
                        "current_duration": f"{stage_duration}s",
                        "expected_duration": f"{baseline['avg_duration']:.0f}s",
                        "impact": "high" if stage_duration > baseline["avg_duration"] * 2 else "medium"
                    })
                    
                    improvement = ((stage_duration - baseline["avg_duration"]) / stage_duration) * 100
                    optimizations["improvement_percent"] += min(30.0, improvement)
        
        return optimizations if optimizations["changes"] else None
    
    def _optimize_resource_usage(self, config_data: Dict) -> Optional[Dict]:
        """Optimize resource usage based on system metrics"""
        optimizations = {"changes": [], "improvement_percent": 0.0}
        
        system_metrics = config_data.get("system_metrics", {})
        if not system_metrics:
            return None
        
        # Check for resource bottlenecks
        resource_warnings = system_metrics.get("resource_warnings", 0)
        if resource_warnings > 2:
            optimizations["changes"].append({
                "type": "resource_optimization",
                "description": "Multiple resource warnings detected",
                "recommendation": "Consider reducing parallel jobs or increasing system resources",
                "impact": "high",
                "expected_improvement": "20-40%"
            })
            optimizations["improvement_percent"] += 25.0
        
        # Check for parallel compilation opportunities
        performance_indicators = system_metrics.get("performance_indicators", [])
        if "parallel_compilation" not in performance_indicators:
            optimizations["changes"].append({
                "type": "parallelization",
                "description": "Parallel compilation not detected",
                "recommendation": "Enable parallel make jobs (-j flag) for faster compilation",
                "impact": "high",
                "expected_improvement": "30-50%"
            })
            optimizations["improvement_percent"] += 35.0
        
        return optimizations if optimizations["changes"] else None
    
    def is_trained(self) -> bool:
        """Check if optimizer is trained"""
        return self.is_trained_flag
    
    def needs_training(self) -> bool:
        """Check if optimizer needs retraining"""
        if not self.is_trained_flag:
            return True
        
        if self.last_training_time:
            days_since_training = (datetime.now() - self.last_training_time).days
            return days_since_training > 14  # Retrain bi-weekly
        
        return True
    
    def get_recommendations(self, perf_data: Dict) -> List[str]:
        """Get performance recommendations - interface method for tests"""
        optimization = self.optimize(perf_data)
        if optimization and 'changes' in optimization:
            return [change.get('description', 'Performance optimization available') for change in optimization['changes']]
        return ["No specific optimizations identified", "Consider monitoring build performance over time"]
    
    def calculate_efficiency_score(self, perf_data: Dict) -> float:
        """Calculate efficiency score for performance data"""
        try:
            # Simple efficiency calculation based on available data
            build_duration = perf_data.get('build_duration', 0)
            cpu_cores = perf_data.get('cpu_cores', 1)
            parallel_jobs = perf_data.get('parallel_jobs', 1)
            
            # Efficiency based on parallelization utilization
            parallelization_efficiency = min(1.0, parallel_jobs / cpu_cores)
            
            # Duration efficiency (lower is better, normalized)
            duration_efficiency = max(0.0, 1.0 - (build_duration / 14400))  # 4 hours baseline
            
            overall_efficiency = (parallelization_efficiency * 0.6) + (duration_efficiency * 0.4)
            return max(0.0, min(1.0, overall_efficiency))
            
        except Exception as e:
            self.logger.error(f"Efficiency calculation failed: {e}")
            return 0.5  # Default moderate efficiency
    
    def train_model(self) -> Dict:
        """Train the performance optimizer - interface method for automated training"""
        return self.train()
    
    def train(self) -> Dict:
        """Train the performance optimizer"""
        try:
            self.logger.info("Training performance optimizer...")
            
            # Refresh performance patterns
            self._analyze_config_performance()
            self._analyze_timing_optimization()
            
            # Calculate accuracy based on data coverage
            config_count = len(self.optimal_configs)
            baseline_count = len(self.performance_baselines)
            
            accuracy = min(0.90, 0.4 + ((config_count + baseline_count) * 0.05))
            
            self.is_trained_flag = True
            self.last_training_time = datetime.now()
            self.accuracy = accuracy
            
            return {
                "success": True,
                "accuracy": accuracy,
                "training_time": "< 1 minute",
                "samples_used": config_count + baseline_count,
                "configs_analyzed": config_count,
                "stages_analyzed": baseline_count
            }
            
        except Exception as e:
            self.logger.error(f"Training failed: {e}")
            return {"success": False, "error": str(e)}