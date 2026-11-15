import sys, os
sys.path.insert(0, os.path.abspath("."))
from src.features.feature_pipeline import ResumeJobFeaturePipeline

p = ResumeJobFeaturePipeline()
feats, names = p._extract_dense_features(
    ["Python developer with 5 years experience in Django and AWS."],
    ["Looking for Python engineer with 3 years exp in Django."]
)
print("Dense feats shape:", feats.shape)
print("Feature count:", len(names))
print("Names:", names)
