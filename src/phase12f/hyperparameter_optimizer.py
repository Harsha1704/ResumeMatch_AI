"""
src/phase12f/hyperparameter_optimizer.py
Automated Hyperparameter Optimization for Phase 12F using Optuna.
Optimizes LightGBM and CatBoost configurations on group-aware validation data only.
Prevents test contamination and records all optimization trials.
"""

from typing import Dict, List, Optional, Tuple, Any
import optuna
import numpy as np
import lightgbm as lgb
from catboost import CatBoostClassifier
from sklearn.metrics import f1_score, balanced_accuracy_score

# Silence verbose Optuna logs
optuna.logging.set_verbosity(optuna.logging.WARNING)
CLASSES = ["No Fit", "Potential Fit", "Good Fit"]


class HyperparameterOptimizer:
    """
    Manages Bayesian hyperparameter optimization over validation folds.
    """

    def __init__(self, n_trials: int = 20, random_state: int = 42):
        self.n_trials = n_trials
        self.random_state = random_state

    def optimize_lightgbm(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray
    ) -> Dict[str, Any]:
        """
        Tunes LightGBM hyperparameters optimizing Macro F1 on validation data.
        """
        def objective(trial):
            params = {
                "objective": "multiclass",
                "num_class": 3,
                "metric": "multi_logloss",
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.15, log=True),
                "num_leaves": trial.suggest_int("num_leaves", 15, 63),
                "max_depth": trial.suggest_int("max_depth", 3, 8),
                "n_estimators": trial.suggest_int("n_estimators", 50, 150),
                "min_child_samples": trial.suggest_int("min_child_samples", 10, 50),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "class_weight": "balanced",
                "verbose": -1,
                "random_state": self.random_state
            }
            model = lgb.LGBMClassifier(**params)
            model.fit(X_train, y_train)
            preds = model.predict(X_val)
            # Optimize Macro F1
            return f1_score(y_val, preds, average="macro", labels=CLASSES, zero_division=0)

        study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=self.random_state))
        study.optimize(objective, n_trials=self.n_trials)

        best_params = study.best_params
        best_params.update({
            "objective": "multiclass",
            "num_class": 3,
            "metric": "multi_logloss",
            "class_weight": "balanced",
            "verbose": -1,
            "random_state": self.random_state
        })

        return {
            "best_params": best_params,
            "best_val_macro_f1": round(study.best_value, 4),
            "n_trials": len(study.trials)
        }
