"""
Machine Learning Module for LFS Build System

Provides intelligent build analysis, failure prediction, and performance optimization
through machine learning algorithms trained on historical build data.
"""

try:
    from .ml_engine import MLEngine
    from .feature_extractor import FeatureExtractor
    ML_AVAILABLE = True
except ImportError as e:
    # ML dependencies not available
    MLEngine = None
    FeatureExtractor = None
    ML_AVAILABLE = False

__version__ = "1.0.0"
__all__ = ["MLEngine", "FeatureExtractor", "SystemAdvisor"]