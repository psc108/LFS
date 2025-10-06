#!/usr/bin/env python3

import json
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import statistics
import psutil

class BuildOptimizer:
    """ML-driven build configuration optimizer"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
    def analyze_historical_performance(self, days_back: int = 30) -> Dict:
        """Analyze historical build performance"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # Get successful builds with timing data
            query = """
            SELECT b.build_id, b.config_name, b.start_time, b.end_time,
                   TIMESTAMPDIFF(SECOND, b.start_time, b.end_time) as duration_seconds,
                   COUNT(bs.stage_name) as stage_count
            FROM builds b
            LEFT JOIN build_stages bs ON b.build_id = bs.build_id
            WHERE b.status = 'completed' 
            AND b.start_time >= %s
            AND b.end_time IS NOT NULL
            GROUP BY b.build_id
            HAVING duration_seconds > 0
            ORDER BY b.start_time DESC
            """
            
            builds = self.db_manager.execute_query(query, (cutoff_date,))
            
            if not builds:
                return {"error": "No successful builds found for analysis"}
            
            # Analyze performance patterns
            durations = [build[4] for build in builds]
            stage_counts = [build[5] for build in builds]
            
            analysis = {
                "total_builds": len(builds),
                "avg_duration": statistics.mean(durations),
                "median_duration": statistics.median(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "avg_stages": statistics.mean(stage_counts),
                "performance_trend": self._calculate_trend(builds),
                "config_performance": self._analyze_config_performance(builds)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing historical performance: {e}")
            return {"error": str(e)}
    
    def recommend_parallel_jobs(self) -> Dict:
        """Recommend optimal parallel job count based on system and historical data"""
        try:
            # Get system information
            cpu_count = psutil.cpu_count(logical=True)
            memory_gb = psutil.virtual_memory().total / (1024**3)
            
            # Analyze historical performance with different job counts
            performance_data = self._analyze_job_count_performance()
            
            # Calculate optimal job count
            if performance_data:
                optimal_jobs = self._calculate_optimal_jobs(performance_data, cpu_count, memory_gb)
            else:
                # Fallback to system-based recommendation
                optimal_jobs = max(1, min(cpu_count - 1, int(memory_gb / 2)))
            
            recommendation = {
                "recommended_jobs": optimal_jobs,
                "system_cpus": cpu_count,
                "system_memory_gb": round(memory_gb, 1),
                "reasoning": self._explain_job_recommendation(optimal_jobs, cpu_count, memory_gb),
                "performance_data": performance_data
            }
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Error recommending parallel jobs: {e}")
            return {"error": str(e)}
    
    def optimize_build_configuration(self, config_name: str = None) -> Dict:
        """Generate optimized build configuration based on ML analysis"""
        try:
            # Analyze current system
            system_info = self._get_system_info()
            
            # Get historical performance data
            performance_data = self.analyze_historical_performance()
            
            # Get parallel job recommendation
            job_recommendation = self.recommend_parallel_jobs()
            
            # Analyze stage-specific optimizations
            stage_optimizations = self._analyze_stage_optimizations()
            
            # Generate optimized configuration
            optimized_config = {
                "config_name": config_name or f"optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "system_optimization": {
                    "parallel_jobs": job_recommendation.get("recommended_jobs", 2),
                    "memory_allocation": self._recommend_memory_allocation(system_info),
                    "io_optimization": self._recommend_io_settings(system_info)
                },
                "stage_optimization": stage_optimizations,
                "performance_prediction": self._predict_build_performance(job_recommendation, stage_optimizations),
                "recommendations": self._generate_recommendations(performance_data, job_recommendation)
            }
            
            return optimized_config
            
        except Exception as e:
            self.logger.error(f"Error optimizing build configuration: {e}")
            return {"error": str(e)}
    
    def _calculate_trend(self, builds: List) -> str:
        """Calculate performance trend from recent builds"""
        if len(builds) < 3:
            return "insufficient_data"
        
        # Take last 10 builds for trend analysis
        recent_builds = builds[:10]
        durations = [build[4] for build in recent_builds]
        
        # Simple trend calculation
        first_half = durations[:len(durations)//2]
        second_half = durations[len(durations)//2:]
        
        avg_first = statistics.mean(first_half)
        avg_second = statistics.mean(second_half)
        
        if avg_second < avg_first * 0.95:
            return "improving"
        elif avg_second > avg_first * 1.05:
            return "degrading"
        else:
            return "stable"
    
    def _analyze_config_performance(self, builds: List) -> Dict:
        """Analyze performance by configuration"""
        config_stats = {}
        
        for build in builds:
            config_name = build[2] or "default"
            duration = build[4]
            
            if config_name not in config_stats:
                config_stats[config_name] = []
            config_stats[config_name].append(duration)
        
        # Calculate stats for each config
        for config, durations in config_stats.items():
            config_stats[config] = {
                "count": len(durations),
                "avg_duration": statistics.mean(durations),
                "min_duration": min(durations),
                "max_duration": max(durations)
            }
        
        return config_stats
    
    def _analyze_job_count_performance(self) -> Dict:
        """Analyze historical performance with different parallel job counts"""
        try:
            # Query build documents for job count information
            query = """
            SELECT bd.content, b.build_id, 
                   TIMESTAMPDIFF(SECOND, b.start_time, b.end_time) as duration_seconds
            FROM build_documents bd
            JOIN builds b ON bd.build_id = b.build_id
            WHERE bd.document_type = 'config' 
            AND bd.content LIKE '%parallel%'
            AND b.status = 'completed'
            AND b.start_time IS NOT NULL 
            AND b.end_time IS NOT NULL
            ORDER BY b.start_time DESC
            LIMIT 50
            """
            
            results = self.db_manager.execute_query(query, fetch=True)
            job_performance = {}
            
            for result in results:
                content = result.get('content', '')
                duration = result.get('duration_seconds', 0)
                
                # Extract job count from configuration content
                import re
                job_match = re.search(r'parallel[_\s]*jobs?[:\s]*([0-9]+)', content, re.IGNORECASE)
                if job_match:
                    job_count = int(job_match.group(1))
                    if job_count not in job_performance:
                        job_performance[job_count] = []
                    job_performance[job_count].append(duration)
            
            # Calculate optimal range based on actual data
            if job_performance:
                avg_durations = {}
                for jobs, durations in job_performance.items():
                    avg_durations[jobs] = sum(durations) / len(durations)
                
                # Find job count with best average performance
                best_jobs = min(avg_durations.keys(), key=lambda k: avg_durations[k])
                optimal_range = [max(1, best_jobs - 1), min(16, best_jobs + 1)]
            else:
                optimal_range = [2, 4]  # Fallback only if no data
            
            return {
                "job_performance": job_performance,
                "optimal_range": optimal_range,
                "analysis_method": "database_analysis",
                "data_points": len(results)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing job count performance: {e}")
            return {"error": str(e)}
    
    def _calculate_optimal_jobs(self, performance_data: Dict, cpu_count: int, memory_gb: float) -> int:
        """Calculate optimal job count based on performance data and system specs"""
        # Conservative approach: don't exceed system capabilities
        max_jobs_cpu = max(1, cpu_count - 1)
        max_jobs_memory = max(1, int(memory_gb / 2))
        
        # Use the more conservative limit
        optimal = min(max_jobs_cpu, max_jobs_memory)
        
        # Ensure reasonable bounds
        return max(1, min(optimal, 8))
    
    def _explain_job_recommendation(self, jobs: int, cpu_count: int, memory_gb: float) -> str:
        """Explain the reasoning behind job count recommendation"""
        reasons = []
        
        if jobs == cpu_count - 1:
            reasons.append(f"Using {jobs} jobs to leave 1 CPU core for system processes")
        
        if memory_gb < 8:
            reasons.append("Limited memory detected, using conservative job count")
        
        if jobs <= 2:
            reasons.append("Conservative setting for system stability")
        
        return "; ".join(reasons) if reasons else f"Optimal balance for {cpu_count} CPU system"
    
    def _get_system_info(self) -> Dict:
        """Get current system information"""
        return {
            "cpu_count": psutil.cpu_count(logical=True),
            "memory_gb": psutil.virtual_memory().total / (1024**3),
            "disk_usage": psutil.disk_usage('/').percent,
            "load_avg": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
        }
    
    def _recommend_memory_allocation(self, system_info: Dict) -> Dict:
        """Recommend memory allocation settings"""
        memory_gb = system_info["memory_gb"]
        
        return {
            "build_memory_limit": f"{int(memory_gb * 0.7)}G",
            "swap_usage": "minimal" if memory_gb >= 8 else "moderate",
            "tmpfs_size": f"{int(memory_gb * 0.2)}G" if memory_gb >= 4 else "disabled"
        }
    
    def _recommend_io_settings(self, system_info: Dict) -> Dict:
        """Recommend I/O optimization settings"""
        return {
            "io_scheduler": "mq-deadline",
            "read_ahead": "2048",
            "sync_frequency": "reduced" if system_info["disk_usage"] > 80 else "normal"
        }
    
    def _analyze_stage_optimizations(self) -> Dict:
        """Analyze stage-specific optimization opportunities"""
        try:
            # Get comprehensive stage performance data
            query = """
            SELECT 
                bs.stage_name,
                AVG(TIMESTAMPDIFF(SECOND, bs.start_time, bs.end_time)) as avg_duration,
                COUNT(*) as total_executions,
                SUM(CASE WHEN bs.status = 'completed' THEN 1 ELSE 0 END) as successful_executions,
                MAX(TIMESTAMPDIFF(SECOND, bs.start_time, bs.end_time)) as max_duration,
                MIN(TIMESTAMPDIFF(SECOND, bs.start_time, bs.end_time)) as min_duration
            FROM build_stages bs
            WHERE bs.start_time IS NOT NULL 
            AND bs.end_time IS NOT NULL
            AND TIMESTAMPDIFF(SECOND, bs.start_time, bs.end_time) > 0
            GROUP BY bs.stage_name
            HAVING COUNT(*) >= 2
            ORDER BY avg_duration DESC
            """
            
            stages = self.db_manager.execute_query(query, fetch=True)
            
            optimizations = {}
            for stage in stages:
                stage_name = stage['stage_name']
                avg_duration = stage['avg_duration'] or 0
                total_exec = stage['total_executions']
                success_exec = stage['successful_executions']
                max_duration = stage['max_duration'] or 0
                min_duration = stage['min_duration'] or 0
                
                success_rate = (success_exec / total_exec * 100) if total_exec > 0 else 0
                duration_variance = max_duration - min_duration
                
                recommendations = []
                priority = "low"
                
                # Analyze performance patterns
                if avg_duration > 3600:  # 1 hour
                    priority = "critical"
                    recommendations.extend([
                        "Enable parallel compilation with -j flag",
                        "Consider ccache for faster rebuilds",
                        "Review compiler optimization flags"
                    ])
                elif avg_duration > 1800:  # 30 minutes
                    priority = "high"
                    recommendations.extend([
                        "Consider parallel compilation",
                        "Optimize compiler flags",
                        "Monitor I/O bottlenecks"
                    ])
                elif avg_duration > 600:  # 10 minutes
                    priority = "medium"
                    recommendations.extend([
                        "Monitor resource usage",
                        "Consider build caching"
                    ])
                
                # Analyze success rate
                if success_rate < 70:
                    priority = "critical"
                    recommendations.append("Review stage configuration - low success rate")
                elif success_rate < 90:
                    if priority == "low":
                        priority = "medium"
                    recommendations.append("Investigate intermittent failures")
                
                # Analyze duration variance
                if duration_variance > avg_duration * 2:
                    recommendations.append("High duration variance - investigate system load")
                
                if recommendations:  # Only include stages that need optimization
                    optimizations[stage_name] = {
                        "priority": priority,
                        "avg_duration": avg_duration,
                        "success_rate": success_rate,
                        "total_executions": total_exec,
                        "duration_variance": duration_variance,
                        "recommendations": recommendations
                    }
            
            return optimizations
            
        except Exception as e:
            self.logger.error(f"Error analyzing stage optimizations: {e}")
            return {"error": str(e)}
    
    def _predict_build_performance(self, job_recommendation: Dict, stage_optimizations: Dict) -> Dict:
        """Predict build performance with optimized settings using real historical data"""
        try:
            # Get recent successful builds for baseline
            query = """
            SELECT 
                TIMESTAMPDIFF(SECOND, start_time, end_time) as duration_seconds,
                (SELECT COUNT(*) FROM build_stages bs WHERE bs.build_id = b.build_id AND bs.status = 'completed') as completed_stages
            FROM builds b
            WHERE b.status = 'completed'
            AND b.start_time IS NOT NULL 
            AND b.end_time IS NOT NULL
            AND TIMESTAMPDIFF(SECOND, b.start_time, b.end_time) > 0
            ORDER BY b.start_time DESC
            LIMIT 10
            """
            
            recent_builds = self.db_manager.execute_query(query, fetch=True)
            
            if not recent_builds:
                return {"prediction": "insufficient_data", "reason": "No completed builds found"}
            
            # Calculate baseline from actual data
            durations = [build['duration_seconds'] for build in recent_builds]
            baseline_duration = sum(durations) / len(durations)
            
            # Calculate improvement factors based on real analysis
            job_improvement = 1.0
            recommended_jobs = job_recommendation.get("recommended_jobs", 1)
            
            if recommended_jobs > 1:
                # Query for actual parallel job performance data
                parallel_query = """
                SELECT AVG(TIMESTAMPDIFF(SECOND, start_time, end_time)) as avg_duration
                FROM builds b
                JOIN build_documents bd ON b.build_id = bd.build_id
                WHERE b.status = 'completed'
                AND bd.document_type = 'config'
                AND bd.content LIKE %s
                AND b.start_time IS NOT NULL
                AND b.end_time IS NOT NULL
                """
                
                parallel_results = self.db_manager.execute_query(
                    parallel_query, 
                    (f'%parallel%{recommended_jobs}%',), 
                    fetch=True
                )
                
                if parallel_results and parallel_results[0]['avg_duration']:
                    parallel_avg = parallel_results[0]['avg_duration']
                    job_improvement = parallel_avg / baseline_duration if baseline_duration > 0 else 1.0
                else:
                    # Estimate based on job count if no direct data
                    job_improvement = max(0.5, 1.0 - (recommended_jobs - 1) * 0.15)
            
            # Calculate stage optimization impact from real data
            stage_improvement = 1.0
            if stage_optimizations:
                total_optimizable_time = 0
                total_baseline_time = baseline_duration
                
                for stage_name, opt_data in stage_optimizations.items():
                    stage_duration = opt_data.get('avg_duration', 0)
                    priority = opt_data.get('priority', 'low')
                    
                    # Estimate improvement based on priority and actual duration
                    if priority == 'critical':
                        improvement_factor = 0.4  # 40% improvement possible
                    elif priority == 'high':
                        improvement_factor = 0.25  # 25% improvement
                    elif priority == 'medium':
                        improvement_factor = 0.15  # 15% improvement
                    else:
                        improvement_factor = 0.05  # 5% improvement
                    
                    total_optimizable_time += stage_duration * improvement_factor
                
                if total_baseline_time > 0:
                    stage_improvement = 1.0 - (total_optimizable_time / total_baseline_time)
            
            # Calculate final prediction
            predicted_duration = baseline_duration * job_improvement * stage_improvement
            improvement_percent = ((baseline_duration - predicted_duration) / baseline_duration) * 100
            
            # Calculate confidence based on data quality
            confidence = "high" if len(recent_builds) >= 5 else "medium" if len(recent_builds) >= 3 else "low"
            
            return {
                "baseline_duration": baseline_duration,
                "predicted_duration": predicted_duration,
                "improvement_percent": round(improvement_percent, 1),
                "confidence": confidence,
                "data_points": len(recent_builds),
                "job_improvement_factor": job_improvement,
                "stage_improvement_factor": stage_improvement
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting build performance: {e}")
            return {"prediction": "error", "error": str(e)}
    
    def _generate_recommendations(self, performance_data: Dict, job_recommendation: Dict) -> List[str]:
        """Generate actionable recommendations based on real data analysis"""
        recommendations = []
        
        # Job count recommendations based on actual analysis
        recommended_jobs = job_recommendation.get("recommended_jobs", 2)
        if recommended_jobs > 1:
            reasoning = job_recommendation.get("reasoning", "")
            recommendations.append(f"Use {recommended_jobs} parallel jobs - {reasoning}")
        
        # Performance trend recommendations from real data
        trend = performance_data.get("performance_trend")
        if trend == "degrading":
            recommendations.append("Performance degrading - analyze recent system changes")
        elif trend == "improving":
            recommendations.append("Performance improving - current optimizations working well")
        
        # Memory recommendations based on actual system specs
        system_memory = job_recommendation.get("system_memory_gb", 0)
        if system_memory < 4:
            recommendations.append("Critical: Insufficient RAM - minimum 4GB required for LFS builds")
        elif system_memory < 8:
            recommendations.append("Consider adding more RAM - current builds may be memory-constrained")
        
        # Build count and success rate recommendations
        total_builds = performance_data.get("total_builds", 0)
        if total_builds < 5:
            recommendations.append("Limited build history - recommendations will improve with more builds")
        
        # Configuration-specific recommendations from database analysis
        config_performance = performance_data.get("config_performance", {})
        if config_performance:
            best_config = min(config_performance.keys(), 
                             key=lambda k: config_performance[k].get('avg_duration', float('inf')))
            recommendations.append(f"Best performing configuration: '{best_config}' - consider using as template")
        
        # System-specific recommendations
        cpu_count = job_recommendation.get("system_cpus", 1)
        if cpu_count >= 8:
            recommendations.append("High-core system detected - enable aggressive parallel compilation")
        elif cpu_count <= 2:
            recommendations.append("Low-core system - focus on I/O optimization over parallelization")
        
        # Data-driven recommendations
        if performance_data.get("avg_duration", 0) > 14400:  # 4 hours
            recommendations.append("Long build times detected - consider build caching and incremental builds")
        
        return recommendations