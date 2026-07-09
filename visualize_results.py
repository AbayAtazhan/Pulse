import os
import json
import matplotlib.pyplot as plt
import numpy as np

def load_data(filepath: str = "final_comparison.json") -> dict:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Comparison file '{filepath}' not found.")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_plots(data: dict, output_dir: str = "plots"):
    os.makedirs(output_dir, exist_ok=True)
    
    m1_data = data["model_1"]
    m2_data = data["model_2"]
    
    m1_name = m1_data["model_name"].upper()
    m2_name = m2_data["model_name"].upper()
    
    minutes = ["20", "45", "70"]
    minutes_int = [20, 45, 70]
    
    m1_acc = [m1_data["metrics"]["accuracy_by_minute"]["final_result"][m] for m in minutes]
    m2_acc = [m2_data["metrics"]["accuracy_by_minute"]["final_result"][m] for m in minutes]
    baseline_acc = [m1_data["metrics"]["accuracy_by_minute"]["baseline"][m] for m in minutes]
    
    m1_cal = m1_data["metrics"]["calibration"]["final_result"]
    m2_cal = m2_data["metrics"]["calibration"]["final_result"]
    bins_list = ["0-30%", "30-70%", "70-100%"]
    
    m1_conf_pts, m1_acc_pts = [], []
    for b in bins_list:
        if m1_cal[b]["count"] > 0:
            m1_conf_pts.append(m1_cal[b]["avg_predicted_confidence"])
            m1_acc_pts.append(m1_cal[b]["actual_accuracy"])
            
    m2_conf_pts, m2_acc_pts = [], []
    for b in bins_list:
        if m2_cal[b]["count"] > 0:
            m2_conf_pts.append(m2_cal[b]["avg_predicted_confidence"])
            m2_acc_pts.append(m2_cal[b]["actual_accuracy"])

    m1_ratio = m1_data["update_test"]["consistency_ratio"]
    m2_ratio = m2_data["update_test"]["consistency_ratio"]

    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, axs = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle("Pulse: In-Play Match Reasoning - Evaluation Results", fontsize=18, fontweight='bold', y=0.98)
    
    color_m1 = "#1f77b4"
    color_m2 = "#ff7f0e"
    color_base = "#2ca02c"
    
    # Subplot 1
    ax = axs[0, 0]
    ax.plot(minutes_int, m1_acc, marker='o', linewidth=2, color=color_m1, label=m1_name)
    ax.plot(minutes_int, m2_acc, marker='s', linewidth=2, color=color_m2, label=m2_name)
    ax.set_title("Accuracy by Freeze Minute (Final Result)", fontsize=13, fontweight='semibold')
    ax.set_xlabel("Freeze Minute (T)", fontsize=11)
    ax.set_ylabel("Accuracy", fontsize=11)
    ax.set_xticks(minutes_int)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(frameon=True)
    
    # Subplot 2
    ax = axs[0, 1]
    ax.plot([0, 1], [0, 1], linestyle='--', color='gray', label='Perfect Calibration')
    if m1_conf_pts:
        ax.plot(m1_conf_pts, m1_acc_pts, marker='o', linewidth=2, color=color_m1, label=m1_name)
    if m2_conf_pts:
        ax.plot(m2_conf_pts, m2_acc_pts, marker='s', linewidth=2, color=color_m2, label=m2_name)
    ax.set_title("Confidence Calibration Curve", fontsize=13, fontweight='semibold')
    ax.set_xlabel("Average Predicted Confidence", fontsize=11)
    ax.set_ylabel("Actual Accuracy", fontsize=11)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(frameon=True)

    # Subplot 3
    ax = axs[1, 0]
    x = np.arange(len(minutes))
    width = 0.25
    ax.bar(x - width, m1_acc, width, label=m1_name, color=color_m1)
    ax.bar(x, m2_acc, width, label=m2_name, color=color_m2)
    ax.bar(x + width, baseline_acc, width, label='Naive Baseline', color=color_base)
    ax.set_title("Accuracy Comparison: Model vs Naive Baseline", fontsize=13, fontweight='semibold')
    ax.set_xlabel("Freeze Minute (T)", fontsize=11)
    ax.set_ylabel("Accuracy", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(minutes)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(frameon=True)

    # Subplot 4
    ax = axs[1, 1]
    models = [m1_name, m2_name]
    ratios = [m1_ratio, m2_ratio]
    colors = [color_m1, color_m2]
    
    bars = ax.bar(models, ratios, color=colors, width=0.5)
    ax.set_title("Update Consistency Test", fontsize=13, fontweight='semibold')
    ax.set_ylabel("Consistency Ratio (Sensible / Total)", fontsize=11)
    ax.set_ylim(-0.05, 1.05)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width()/2.0, 
            height + 0.02, 
            f"{height * 100:.1f}%", 
            ha='center', 
            va='bottom', 
            fontweight='bold'
        )

    plt.tight_layout()
    unified_filepath = os.path.join(output_dir, "evaluation_summary.png")
    fig.savefig(unified_filepath, dpi=300)
    plt.close(fig)
    print(f"Summary chart saved to '{unified_filepath}'")

if __name__ == "__main__":
    try:
        comparison_data = load_data()
        generate_plots(comparison_data)
    except Exception as e:
        print(f"Error while generating plots: {e}")
