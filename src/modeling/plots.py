"""
Model performance visualizations: ROC curve, PR curve, confusion matrix, calibration curve,
feature importance, risk distribution. Saved to artifacts/plots/.
"""
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.calibration import calibration_curve
from sklearn.metrics import confusion_matrix, precision_recall_curve, roc_curve

from src.config import PLOTS_DIR

logger = logging.getLogger(__name__)


def _ensure_plots_dir() -> Path:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    return PLOTS_DIR


def plot_roc_curve(y_true: np.ndarray, y_proba: np.ndarray, output_path: Path | None = None) -> Path:
    """Plot ROC curve from true labels and predicted probabilities."""
    output_path = output_path or _ensure_plots_dir() / "roc_curve.png"
    fpr, tpr, _ = roc_curve(y_true, y_proba)
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, color="darkorange", lw=2, label="ROC curve")
    plt.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve (Out-of-Fold)")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=100)
    plt.close()
    logger.info("Saved %s", output_path)
    return output_path


def plot_pr_curve(y_true: np.ndarray, y_proba: np.ndarray, output_path: Path | None = None) -> Path:
    """Plot Precision-Recall curve."""
    output_path = output_path or _ensure_plots_dir() / "pr_curve.png"
    precision, recall, _ = precision_recall_curve(y_true, y_proba)
    plt.figure(figsize=(6, 5))
    plt.plot(recall, precision, color="green", lw=2)
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curve (Out-of-Fold)")
    plt.tight_layout()
    plt.savefig(output_path, dpi=100)
    plt.close()
    logger.info("Saved %s", output_path)
    return output_path


def plot_calibration_curve(y_true: np.ndarray, y_proba: np.ndarray, output_path: Path | None = None) -> Path:
    """
    Plot reliability (calibration) curve: predicted vs observed frequency.
    Illustrative only for small datasets; use for qualitative assessment.
    """
    output_path = output_path or _ensure_plots_dir() / "calibration_curve.png"
    n_bins = min(10, max(2, len(np.unique(y_proba)) - 1))
    try:
        frac_pos, mean_pred = calibration_curve(y_true, y_proba, n_bins=n_bins)
    except Exception:
        frac_pos, mean_pred = np.array([0.0, 1.0]), np.array([0.0, 1.0])
    plt.figure(figsize=(6, 5))
    plt.plot(mean_pred, frac_pos, "s-", color="darkorange", lw=2, label="Model")
    plt.plot([0, 1], [0, 1], "k--", lw=2, label="Perfectly calibrated")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("Mean predicted probability")
    plt.ylabel("Fraction of positives")
    plt.title("Calibration Curve (Out-of-Fold)\nIllustrative only — small sample")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=100)
    plt.close()
    logger.info("Saved %s", output_path)
    return output_path


def plot_confusion_matrix(y_true: np.ndarray, y_proba: np.ndarray, output_path: Path | None = None) -> Path:
    """Confusion matrix using 0.5 threshold on probabilities."""
    output_path = output_path or _ensure_plots_dir() / "confusion_matrix.png"
    y_pred = (y_proba >= 0.5).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=["Low risk", "High risk"], yticklabels=["Low risk", "High risk"])
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title("Confusion Matrix (Out-of-Fold, threshold=0.5)")
    plt.tight_layout()
    plt.savefig(output_path, dpi=100)
    plt.close()
    logger.info("Saved %s", output_path)
    return output_path


def plot_feature_importance(feature_importance: list[tuple[str, float]], output_path: Path | None = None) -> Path:
    """Bar chart of feature importance (for tree model or abs(coef) for linear)."""
    output_path = output_path or _ensure_plots_dir() / "feature_importance.png"
    names = [x[0] for x in feature_importance]
    values = [x[1] for x in feature_importance]
    plt.figure(figsize=(8, max(4, len(names) * 0.3)))
    plt.barh(range(len(names)), values, color="steelblue", alpha=0.8)
    plt.yticks(range(len(names)), names, fontsize=9)
    plt.xlabel("Importance")
    plt.title("Feature Importance (Chosen Model)")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(output_path, dpi=100)
    plt.close()
    logger.info("Saved %s", output_path)
    return output_path


def plot_risk_distribution(prob_high_risk: np.ndarray, output_path: Path | None = None) -> Path:
    """Histogram of predicted merchant risk scores (portfolio risk distribution)."""
    output_path = output_path or _ensure_plots_dir() / "risk_distribution.png"
    plt.figure(figsize=(6, 4))
    plt.hist(prob_high_risk, bins=min(30, max(10, len(prob_high_risk) // 5)), edgecolor="black", alpha=0.7)
    plt.xlabel("Predicted P(high risk)")
    plt.ylabel("Number of merchants")
    plt.title("Portfolio Risk Score Distribution")
    plt.tight_layout()
    plt.savefig(output_path, dpi=100)
    plt.close()
    logger.info("Saved %s", output_path)
    return output_path


def generate_all_plots(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    feature_importance: list[tuple[str, float]],
    plots_dir: Path | None = None,
) -> None:
    """Generate ROC, PR, confusion matrix, calibration curve, feature importance, and risk distribution."""
    d = plots_dir or _ensure_plots_dir()
    plot_roc_curve(y_true, y_proba, d / "roc_curve.png")
    plot_pr_curve(y_true, y_proba, d / "pr_curve.png")
    plot_confusion_matrix(y_true, y_proba, d / "confusion_matrix.png")
    plot_calibration_curve(y_true, y_proba, d / "calibration_curve.png")
    plot_feature_importance(feature_importance, d / "feature_importance.png")
    plot_risk_distribution(y_proba, d / "risk_distribution.png")
