"""
Phase 2 Cross-System ML Integration
Deep integration with Git, CI/CD, Security, and other LFS facilities
"""

from typing import Dict, List, Optional
import logging

class CrossSystemIntegrator:
    """Integrates ML with all LFS system facilities"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Integration modules
        self.git_integration = GitMLIntegration(db_manager)
        self.cicd_integration = CICDMLIntegration(db_manager)
        self.security_integration = SecurityMLIntegration(db_manager)
        
    def get_integrated_features(self, build_id: str) -> Dict:
        """Extract features from all integrated systems"""
        features = {}
        
        # Git features
        git_features = self.git_integration.extract_git_features(build_id)
        features.update(git_features)
        
        # CI/CD features
        cicd_features = self.cicd_integration.extract_cicd_features(build_id)
        features.update(cicd_features)
        
        # Security features
        security_features = self.security_integration.extract_security_features(build_id)
        features.update(security_features)
        
        return features
    
    def predict_cross_system_impact(self, build_data: Dict) -> Dict:
        """Predict impact across all integrated systems"""
        impacts = {}
        
        # Git impact prediction
        impacts['git'] = self.git_integration.predict_git_impact(build_data)
        
        # CI/CD impact prediction
        impacts['cicd'] = self.cicd_integration.predict_cicd_impact(build_data)
        
        # Security impact prediction
        impacts['security'] = self.security_integration.predict_security_impact(build_data)
        
        return impacts

class GitMLIntegration:
    """ML integration with Git system"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
    
    def extract_git_features(self, build_id: str) -> Dict:
        """Extract ML features from Git data"""
        try:
            # Get Git-related build data
            git_data = self.db.execute_query("""
                SELECT bd.content FROM build_documents bd
                WHERE bd.build_id = %s AND bd.title LIKE '%git%'
                LIMIT 10
            """, (build_id,), fetch=True)
            
            features = {
                'git_operations_count': len(git_data),
                'has_git_activity': len(git_data) > 0,
                'git_complexity_score': min(1.0, len(git_data) * 0.1)
            }
            
            return features
            
        except Exception as e:
            self.logger.error(f"Git feature extraction failed: {e}")
            return {}
    
    def predict_git_impact(self, build_data: Dict) -> Dict:
        """Predict Git-related impacts"""
        git_risk = 0.0
        
        if build_data.get('git_complexity_score', 0) > 0.5:
            git_risk += 0.2
        
        return {
            'branch_conflict_risk': git_risk,
            'merge_complexity': git_risk * 0.8,
            'repository_health': 1.0 - git_risk
        }

class CICDMLIntegration:
    """ML integration with CI/CD system"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
    
    def extract_cicd_features(self, build_id: str) -> Dict:
        """Extract ML features from CI/CD data"""
        try:
            # Get CI/CD pipeline data
            pipeline_data = self.db.execute_query("""
                SELECT COUNT(*) as pipeline_count FROM builds
                WHERE start_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """, fetch=True)
            
            count = pipeline_data[0]['pipeline_count'] if pipeline_data else 0
            
            return {
                'recent_pipeline_activity': count,
                'pipeline_load_factor': min(1.0, count / 10.0),
                'cicd_stability_score': max(0.0, 1.0 - (count / 20.0))
            }
            
        except Exception as e:
            self.logger.error(f"CI/CD feature extraction failed: {e}")
            return {}
    
    def predict_cicd_impact(self, build_data: Dict) -> Dict:
        """Predict CI/CD-related impacts"""
        pipeline_risk = build_data.get('pipeline_load_factor', 0) * 0.3
        
        return {
            'pipeline_queue_delay': pipeline_risk,
            'resource_contention': pipeline_risk * 1.2,
            'deployment_risk': pipeline_risk * 0.8
        }

class SecurityMLIntegration:
    """ML integration with Security system"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
    
    def extract_security_features(self, build_id: str) -> Dict:
        """Extract ML features from Security data"""
        try:
            # Get security-related documents
            security_data = self.db.execute_query("""
                SELECT bd.content FROM build_documents bd
                WHERE bd.build_id = %s AND 
                (bd.content LIKE '%security%' OR bd.content LIKE '%compliance%')
                LIMIT 5
            """, (build_id,), fetch=True)
            
            return {
                'security_events_count': len(security_data),
                'has_security_issues': len(security_data) > 0,
                'security_risk_score': min(1.0, len(security_data) * 0.2)
            }
            
        except Exception as e:
            self.logger.error(f"Security feature extraction failed: {e}")
            return {}
    
    def predict_security_impact(self, build_data: Dict) -> Dict:
        """Predict Security-related impacts"""
        security_risk = build_data.get('security_risk_score', 0)
        
        return {
            'compliance_violation_risk': security_risk,
            'vulnerability_introduction_risk': security_risk * 0.7,
            'security_scan_failure_risk': security_risk * 1.1
        }