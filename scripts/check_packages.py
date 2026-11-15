for pkg in ["transformers", "sentence_transformers", "lightgbm", "xgboost", "catboost", "onnxruntime", "optuna", "sklearn", "torch"]:
    try:
        m = __import__(pkg)
        v = getattr(m, "__version__", "installed")
        print(f"  [x] {pkg}: {v}")
    except ImportError as e:
        print(f"  [ ] {pkg}: NOT installed ({e})")
