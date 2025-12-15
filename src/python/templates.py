#generate templates to approximate positions on meteora
import numpy as np
from scipy.optimize import nnls
import matplotlib.pyplot as plt

def rectangle(center, width, B):
    left = int(np.round(center - (width-1)/2))
    vec = np.zeros(B)
    vec[left:left+width] = 1.0
    return vec

def curve(center, width, B):
    vec = np.zeros(B)
    maxd = width/2.0

    for i in range(B):
        d = abs(i - center)
        v = max(0, (maxd - d) / (maxd + 1e-12))
        vec[i] = v
    return vec

def bid_ask(center, width, B):
    vec = np.zeros(B)
    maxd = width/2.0

    for i in range(B):
        if i < (center - maxd) or i > (center + maxd):
            v = 0
        else:
            d = abs(i-center)
            v = max(0, 1 - (maxd - d) / (maxd + 1e-12))
            vec[i] = v
    return vec

def generate_templates(B, center_range = None, width_range = (7, 69), center_step = 3, width_step = 2):
    
    if center_range is None:
        center_range = (0, B-1)
    
    templates = []
    params = []

    strategy_funcs = [rectangle, curve, bid_ask]

    centers = range(center_range[0], center_range[1]+1, center_step)
    widths = range(width_range[0], width_range[1]+1, width_step)

    for func in strategy_funcs:
        for center in centers:
            for width in widths:
                vec = func(center,width,B)
                vec = vec / (np.sum(vec) + 1e-12)
                templates.append(vec)

                params.append({
                    "type": func.__name__,
                    "center": center,
                    "width": width
                })
    
    return np.array(templates), params

def approximate_nnls(target: np.ndarray, templates: np.ndarray, params: list = None, max_strategies = None):
    weights, residuals = nnls(templates.T, target)
    
    nonzero = np.where(weights > 1e-6)[0]
    print(nonzero, weights[nonzero])
    
    if max_strategies is not None and len(nonzero) > max_strategies:
        top_k_in_nonzero = np.argsort(weights[nonzero])[::-1][:max_strategies]
        top_idx = nonzero[top_k_in_nonzero]


        orig_weights = weights.copy()
        weights = np.zeros(len(templates))
        weights[top_idx] = orig_weights[nonzero][top_k_in_nonzero]

        nonzero = top_idx

    print("Final nonzero weights:", nonzero, weights[nonzero])

    weight_sum = np.sum(weights)
    if weight_sum > 1e-12:
        weights = weights / weight_sum
    
    approximation = templates.T @ weights
    #approximation = approximation / (np.sum(approximation) + 1e-12)
    
    strategies = []
    if params is not None:
        strategies = [(params[i], weights[i]) for i in nonzero]
    
    return {
        "weights": weights,
        "approximation": approximation,
        "residual": np.linalg.norm(target - approximation),
        "r_squared": 1 - np.sum((target - approximation)**2) / (np.sum((target - np.mean(target))**2) + 1e-12),
        "strategies": strategies
    }
    
def create_gaussian_target(B, center=None, sigma=10):
    if center is None:
        center = B // 2
    
    x = np.arange(B)
    target = np.exp(-0.5 * ((x - center) / sigma) ** 2)
    target = target / target.sum()
    return target

def main():
    B = 69
    
    # Create a target position - Gaussian curve
    #print("Creating target position (Gaussian curve)...")
    #target = create_gaussian_target(B, center=34, sigma=12)
    target = bid_ask(34, 25, B) * 0.5 + curve(34, 15, B) * 0.5
    target = target / np.sum(target)
    
    # Plot target
    plt.figure(figsize=(12, 5))
    plt.subplot(1, 3, 1)
    plt.bar(range(B), target, alpha=0.7, color='blue', edgecolor='black', linewidth=0.5)
    plt.title('Target Position (Gaussian)', fontsize=14, fontweight='bold')
    plt.xlabel('Bin')
    plt.ylabel('Liquidity')
    plt.grid(True, alpha=0.3)

    print("Generating templates...")
    templates, params = generate_templates(B, center_step=1, width_step=2)
    print(f"Generated {len(params)} templates")
    for i, p in enumerate(params, 1):
        if p['type'] == 'curve' and p['width'] == 15 and p['center'] == 34:
            print(f"Template {i}: {p}")
        if p['type'] == 'bid_ask' and p['width'] == 25 and p['center'] == 34:
            print(f"Template {i}: {p}")
    
    
    print("Running NNLS approximation...")
    result = approximate_nnls(target, templates, params, max_strategies=2)
    approximation = result['approximation']

    
    print(f"\nResults:")
    print(f"  R-squared: {result['r_squared']:.4f}")
    print(f"  Residual: {result['residual']:.4f}")
    print(f"  Strategies used: {len(result['strategies'])}")
    
    print(f"\nTop strategies:")
    for i, (strat, weight) in enumerate(result['strategies'][:5], 1):
        print(f"  {i}. {strat['type']:10s} | center={strat['center']:2d} width={strat['width']:2d} | weight={weight:.4f}")
    
    # Plot approximation
    plt.subplot(1, 3, 2)
    plt.bar(range(B), approximation, alpha=0.7, color='green', edgecolor='black', linewidth=0.5)
    plt.title('NNLS Approximation', fontsize=14, fontweight='bold')
    plt.xlabel('Bin')
    plt.ylabel('Liquidity')
    plt.grid(True, alpha=0.3)
    
    # Plot comparison
    plt.subplot(1, 3, 3)
    x = np.arange(B)
    plt.plot(x, target, 'b-', linewidth=2, label='Target', marker='o', markersize=3, alpha=0.7)
    plt.plot(x, approximation, 'g--', linewidth=2, label='Approximation', marker='s', markersize=3, alpha=0.7)
    plt.fill_between(x, target, approximation, alpha=0.2, color='red', label='Error')
    plt.title(f'Comparison (R²={result["r_squared"]:.3f})', fontsize=14, fontweight='bold')
    plt.xlabel('Bin')
    plt.ylabel('Liquidity')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # Additional visualization: Individual strategy contributions
    plt.figure(figsize=(14, 6))
    
    # Show each strategy contribution
    plt.subplot(1, 2, 1)
    bottom = np.zeros(B)
    colors = plt.cm.tab10(np.linspace(0, 1, len(result['strategies'])))
    
    for i, (strat, weight) in enumerate(result['strategies'][:8]):
        strategy_vec = None
        if strat['type'] == 'rectangle':
            strategy_vec = rectangle(strat['center'], strat['width'], B)
        elif strat['type'] == 'curve':
            strategy_vec = curve(strat['center'], strat['width'], B)
        elif strat['type'] == 'bid_ask':
            strategy_vec = bid_ask(strat['center'], strat['width'], B)
        
        contribution = strategy_vec * weight
        plt.bar(range(B), contribution, bottom=bottom, alpha=0.8, 
                label=f"{strat['type'][:4]} c={strat['center']} w={strat['width']}", 
                color=colors[i])
        bottom += contribution
    
    plt.title('Strategy Contributions (Stacked)', fontsize=14, fontweight='bold')
    plt.xlabel('Bin')
    plt.ylabel('Liquidity')
    plt.legend(fontsize=8, loc='upper right')
    plt.grid(True, alpha=0.3)
    
    # Error analysis
    plt.subplot(1, 2, 2)
    error = target - approximation
    plt.bar(range(B), error, alpha=0.7, color='red', edgecolor='black', linewidth=0.5)
    plt.axhline(y=0, color='black', linestyle='-', linewidth=1)
    plt.title('Approximation Error', fontsize=14, fontweight='bold')
    plt.xlabel('Bin')
    plt.ylabel('Error (Target - Approximation)')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()