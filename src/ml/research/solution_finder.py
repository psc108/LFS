#!/usr/bin/env python3

import requests
import json
import re
import time
from typing import Dict, List, Optional
from urllib.parse import quote_plus
import logging
import hashlib

class SolutionFinder:
    """Internet-based solution finder for build failures"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Search sources prioritized by reliability
        self.search_sources = [
            {
                'name': 'Stack Overflow',
                'base_url': 'https://api.stackexchange.com/2.3/search/advanced',
                'params': {
                    'site': 'stackoverflow',
                    'sort': 'votes',
                    'order': 'desc',
                    'pagesize': 5
                }
            },
            {
                'name': 'GitHub Issues',
                'base_url': 'https://api.github.com/search/issues',
                'params': {
                    'sort': 'updated',
                    'order': 'desc',
                    'per_page': 5
                }
            }
        ]
    
    def find_solutions(self, error_message: str, build_stage: str, package_name: str = None) -> List[Dict]:
        """Find solutions for a specific build error"""
        solutions = []
        
        # Check cache first
        cached = self.get_cached_solutions(error_message)
        if cached:
            return cached
        
        # Extract key error information
        error_keywords = self._extract_error_keywords(error_message)
        
        # Search each source
        for source in self.search_sources:
            try:
                source_solutions = self._search_source(source, error_keywords, build_stage, package_name)
                solutions.extend(source_solutions)
                time.sleep(1)  # Rate limiting
            except Exception as e:
                self.logger.warning(f"Failed to search {source['name']}: {e}")
        
        # Rank and filter solutions
        ranked_solutions = self._rank_solutions(solutions, error_keywords)
        
        # Store solutions in database
        self._store_solutions(error_message, build_stage, package_name, ranked_solutions)
        
        return ranked_solutions[:10]
    
    def _extract_error_keywords(self, error_message: str) -> List[str]:
        """Extract key terms from error message"""
        keywords = []
        
        # Common error patterns
        error_patterns = [
            r'error:\s*(.+?)(?:\n|$)',
            r'fatal error:\s*(.+?)(?:\n|$)',
            r'undefined reference to\s*[`\'"](.+?)[`\'"]',
            r'No such file or directory:\s*(.+?)(?:\n|$)',
            r'command not found:\s*(.+?)(?:\n|$)',
            r'configure:\s*error:\s*(.+?)(?:\n|$)'
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, error_message, re.IGNORECASE | re.MULTILINE)
            keywords.extend(matches)
        
        # Clean keywords
        cleaned_keywords = []
        for keyword in keywords:
            cleaned = re.sub(r'[^\w\s\-\.]', ' ', keyword).strip()
            if len(cleaned) > 3 and len(cleaned) < 100:
                cleaned_keywords.append(cleaned)
        
        return cleaned_keywords[:5]
    
    def _search_source(self, source: Dict, error_keywords: List[str], build_stage: str, package_name: str) -> List[Dict]:
        """Search a specific source for solutions"""
        solutions = []
        
        # Build search query
        query_parts = []
        query_parts.extend(error_keywords)
        
        if package_name:
            query_parts.append(package_name)
        
        query_parts.extend(['linux from scratch', 'lfs'])
        query = ' '.join(query_parts[:8])
        
        if source['name'] == 'Stack Overflow':
            solutions = self._search_stackoverflow(source, query)
        elif source['name'] == 'GitHub Issues':
            solutions = self._search_github(source, query)
        
        return solutions
    
    def _search_stackoverflow(self, source: Dict, query: str) -> List[Dict]:
        """Search Stack Overflow for solutions"""
        solutions = []
        
        try:
            params = source['params'].copy()
            params['q'] = query
            
            response = requests.get(source['base_url'], params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            for item in data.get('items', []):
                if item.get('is_answered', False):
                    solution = {
                        'source': 'Stack Overflow',
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'score': item.get('score', 0),
                        'answer_count': item.get('answer_count', 0),
                        'tags': item.get('tags', []),
                        'relevance_score': 0
                    }
                    solutions.append(solution)
        
        except Exception as e:
            self.logger.warning(f"Stack Overflow search failed: {e}")
        
        return solutions
    
    def _search_github(self, source: Dict, query: str) -> List[Dict]:
        """Search GitHub issues for solutions"""
        solutions = []
        
        try:
            params = source['params'].copy()
            params['q'] = f"{query} is:issue state:closed"
            
            response = requests.get(source['base_url'], params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            for item in data.get('items', []):
                solution = {
                    'source': 'GitHub Issues',
                    'title': item.get('title', ''),
                    'url': item.get('html_url', ''),
                    'score': item.get('score', 0),
                    'comments': item.get('comments', 0),
                    'labels': [label['name'] for label in item.get('labels', [])],
                    'relevance_score': 0
                }
                solutions.append(solution)
        
        except Exception as e:
            self.logger.warning(f"GitHub search failed: {e}")
        
        return solutions
    
    def _rank_solutions(self, solutions: List[Dict], error_keywords: List[str]) -> List[Dict]:
        """Rank solutions by relevance"""
        for solution in solutions:
            score = 0
            
            # Base score from source metrics
            if solution['source'] == 'Stack Overflow':
                score += solution.get('score', 0) * 2
                score += solution.get('answer_count', 0) * 5
            elif solution['source'] == 'GitHub Issues':
                score += solution.get('comments', 0)
            
            # Keyword relevance
            title_lower = solution.get('title', '').lower()
            for keyword in error_keywords:
                if keyword.lower() in title_lower:
                    score += 10
            
            # LFS relevance
            lfs_keywords = ['linux from scratch', 'lfs build', 'gcc compilation']
            for lfs_keyword in lfs_keywords:
                if lfs_keyword in title_lower:
                    score += 15
            
            solution['relevance_score'] = score
        
        return sorted(solutions, key=lambda x: x['relevance_score'], reverse=True)
    
    def _store_solutions(self, error_message: str, build_stage: str, package_name: str, solutions: List[Dict]):
        """Store found solutions in database with comprehensive metadata"""
        try:
            cursor = self.db_manager.get_cursor()
            
            # Create enhanced solutions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ml_solutions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    error_hash VARCHAR(64) NOT NULL,
                    error_message TEXT,
                    error_keywords JSON,
                    build_stage VARCHAR(100),
                    package_name VARCHAR(100),
                    solutions JSON,
                    solution_count INT DEFAULT 0,
                    best_solution_score INT DEFAULT 0,
                    search_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP NULL,
                    usage_count INT DEFAULT 0,
                    effectiveness_rating DECIMAL(3,2) DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_error_hash (error_hash),
                    INDEX idx_build_stage (build_stage),
                    INDEX idx_package_name (package_name),
                    INDEX idx_last_used (last_used)
                )
            """)
            
            # Generate error hash and extract keywords
            error_hash = hashlib.sha256(error_message.encode()).hexdigest()[:16]
            error_keywords = self._extract_error_keywords(error_message)
            
            # Calculate metadata
            solution_count = len(solutions)
            best_score = max([s.get('relevance_score', 0) for s in solutions]) if solutions else 0
            
            # Check if solution already exists
            cursor.execute("SELECT id FROM ml_solutions WHERE error_hash = %s", (error_hash,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing solution with new data
                cursor.execute("""
                    UPDATE ml_solutions SET 
                        solutions = %s,
                        solution_count = %s,
                        best_solution_score = %s,
                        search_timestamp = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE error_hash = %s
                """, (json.dumps(solutions), solution_count, best_score, error_hash))
                self.logger.info(f"Updated {solution_count} solutions for existing error in {build_stage}")
            else:
                # Insert new solution
                cursor.execute("""
                    INSERT INTO ml_solutions 
                    (error_hash, error_message, error_keywords, build_stage, package_name, 
                     solutions, solution_count, best_solution_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (error_hash, error_message, json.dumps(error_keywords), build_stage, 
                      package_name, json.dumps(solutions), solution_count, best_score))
                self.logger.info(f"Stored {solution_count} new solutions for error in {build_stage}")
            
            self.db_manager.connection.commit()
        
        except Exception as e:
            self.logger.error(f"Failed to store solutions: {e}")
    
    def get_cached_solutions(self, error_message: str) -> Optional[List[Dict]]:
        """Get previously found solutions from cache and update usage tracking"""
        try:
            error_hash = hashlib.sha256(error_message.encode()).hexdigest()[:16]
            
            cursor = self.db_manager.get_cursor()
            cursor.execute(
                "SELECT id, solutions, solution_count FROM ml_solutions WHERE error_hash = %s",
                (error_hash,)
            )
            
            result = cursor.fetchone()
            if result:
                solution_id, solutions_json, solution_count = result
                
                # Update usage tracking
                cursor.execute("""
                    UPDATE ml_solutions SET 
                        last_used = CURRENT_TIMESTAMP,
                        usage_count = usage_count + 1
                    WHERE id = %s
                """, (solution_id,))
                
                self.db_manager.connection.commit()
                self.logger.info(f"Retrieved {solution_count} cached solutions (usage updated)")
                
                return json.loads(solutions_json)
        
        except Exception as e:
            self.logger.error(f"Failed to get cached solutions: {e}")
        
        return None
    
    def mark_solution_effective(self, error_message: str, effectiveness_rating: float):
        """Mark a solution as effective for future reference"""
        try:
            error_hash = hashlib.sha256(error_message.encode()).hexdigest()[:16]
            cursor = self.db_manager.get_cursor()
            
            cursor.execute("""
                UPDATE ml_solutions SET 
                    effectiveness_rating = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE error_hash = %s
            """, (effectiveness_rating, error_hash))
            
            self.db_manager.connection.commit()
            self.logger.info(f"Updated solution effectiveness rating to {effectiveness_rating}")
        
        except Exception as e:
            self.logger.error(f"Failed to update solution effectiveness: {e}")
    
    def get_solution_analytics(self) -> Dict:
        """Get analytics on solution database usage"""
        try:
            cursor = self.db_manager.get_cursor()
            
            # Get overall statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_solutions,
                    AVG(solution_count) as avg_solutions_per_error,
                    AVG(usage_count) as avg_usage_count,
                    AVG(effectiveness_rating) as avg_effectiveness,
                    COUNT(CASE WHEN last_used IS NOT NULL THEN 1 END) as used_solutions
                FROM ml_solutions
            """)
            
            stats = cursor.fetchone()
            
            # Get top error patterns
            cursor.execute("""
                SELECT build_stage, COUNT(*) as error_count
                FROM ml_solutions 
                GROUP BY build_stage 
                ORDER BY error_count DESC 
                LIMIT 10
            """)
            
            top_stages = cursor.fetchall()
            
            return {
                'total_solutions': stats[0] or 0,
                'avg_solutions_per_error': float(stats[1] or 0),
                'avg_usage_count': float(stats[2] or 0),
                'avg_effectiveness': float(stats[3] or 0),
                'used_solutions': stats[4] or 0,
                'top_error_stages': [{'stage': stage, 'count': count} for stage, count in top_stages]
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get solution analytics: {e}")
            return {'error': str(e)}
    
    def generate_solution_report(self, build_id: int) -> Dict:
        """Generate comprehensive solution report for failed build with metadata"""
        try:
            cursor = self.db_manager.get_cursor()
            
            cursor.execute("""
                SELECT stage_name, error_message, package_name, start_time, end_time
                FROM build_stages 
                WHERE build_id = %s AND status = 'failed'
                ORDER BY stage_order
            """, (build_id,))
            
            failures = cursor.fetchall()
            report = {
                'build_id': build_id,
                'total_failures': len(failures),
                'solutions_found': 0,
                'cached_solutions': 0,
                'new_solutions': 0,
                'report_generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'stage_solutions': []
            }
            
            for stage_name, error_message, package_name, start_time, end_time in failures:
                # Check if we have cached solutions first
                cached = self.get_cached_solutions(error_message)
                if cached:
                    solutions = cached
                    report['cached_solutions'] += 1
                else:
                    solutions = self.find_solutions(error_message, stage_name, package_name)
                    if solutions:
                        report['new_solutions'] += 1
                
                stage_solution = {
                    'stage_name': stage_name,
                    'package_name': package_name,
                    'error_summary': error_message[:200] + '...' if len(error_message) > 200 else error_message,
                    'stage_start_time': start_time.isoformat() if start_time else None,
                    'stage_end_time': end_time.isoformat() if end_time else None,
                    'solutions': solutions[:5],
                    'solution_count': len(solutions),
                    'solution_source': 'cached' if cached else 'new_search'
                }
                
                report['stage_solutions'].append(stage_solution)
                if solutions:
                    report['solutions_found'] += 1
            
            # Store the report in database for future reference
            self._store_solution_report(build_id, report)
            
            return report
        
        except Exception as e:
            self.logger.error(f"Failed to generate solution report: {e}")
            return {'error': str(e)}
    
    def _store_solution_report(self, build_id: int, report: Dict):
        """Store solution report in database"""
        try:
            cursor = self.db_manager.get_cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ml_solution_reports (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    build_id INT NOT NULL,
                    report_data JSON,
                    total_failures INT,
                    solutions_found INT,
                    cached_solutions INT,
                    new_solutions INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_build_id (build_id)
                )
            """)
            
            cursor.execute("""
                INSERT INTO ml_solution_reports 
                (build_id, report_data, total_failures, solutions_found, cached_solutions, new_solutions)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (build_id, json.dumps(report), report['total_failures'], 
                  report['solutions_found'], report['cached_solutions'], report['new_solutions']))
            
            self.db_manager.connection.commit()
            self.logger.info(f"Stored solution report for build {build_id}")
        
        except Exception as e:
            self.logger.error(f"Failed to store solution report: {e}")