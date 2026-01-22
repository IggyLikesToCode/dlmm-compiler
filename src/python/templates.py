#generate templates to approximate positions on meteora
import numpy as np
from scipy.optimize import nnls
import matplotlib.pyplot as plt
import sys
import json
import argparse
from datetime import datetime
import time

# Generating main templates:
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

# Computing R-squared:
def _compute_r_squared(target: np.ndarray, approximation: np.ndarray) -> float:
    """Compute R-squared metric for approximation quality."""
    ss_res = np.sum((target - approximation) ** 2)
    ss_tot = np.sum((target - np.mean(target)) ** 2) + 1e-12
    return 1 - ss_res / ss_tot




def greedy_select_templates(
    target: np.ndarray, 
    templates: np.ndarray, 
    k: int, 
    verbose: bool = True,
    min_improvement: float = 1e-6
) -> tuple:

    start_time = time.time()
    n_templates = len(templates)
    selected_idx = []
    remaining_idx = set(range(n_templates))
    
    if verbose:
        print(f"\nGreedy forward selection for {k} templates from {n_templates} candidates...")
    
    current_r2 = 0.0
    nnls_count = 0
    
    for iteration in range(k):
        best_r2 = -np.inf
        best_idx = None
        
        for idx in remaining_idx:
            # Try adding this template to current selection
            trial_idx = selected_idx + [idx]
            trial_templates = templates[trial_idx]
            
            # Solve NNLS with trial set
            weights, _ = nnls(trial_templates.T, target)
            nnls_count += 1
            
            # Compute approximation
            approx = trial_templates.T @ weights
            
            # Normalize approximation to match target sum (for fair R² comparison)
            approx_sum = np.sum(approx)
            if approx_sum > 1e-12:
                approx = approx * (np.sum(target) / approx_sum)
            
            r2 = _compute_r_squared(target, approx)
            
            if r2 > best_r2:
                best_r2 = r2
                best_idx = idx
        
        # Early termination if improvement is negligible
        improvement = best_r2 - current_r2
        if iteration > 0 and improvement < min_improvement:
            if verbose:
                print(f"  Early stop at step {iteration + 1}: improvement {improvement:.6f} < threshold {min_improvement}")
            break
        
        selected_idx.append(best_idx)
        remaining_idx.remove(best_idx)
        current_r2 = best_r2
        
        if verbose:
            print(f"  Step {iteration + 1}: Added template {best_idx}, R² = {best_r2:.6f} (improvement: {improvement:.6f})")
    
    total_time = time.time() - start_time
    
    # Timing info
    timing_info = {
        'total_time': total_time,
        'nnls_solves': nnls_count,
        'candidates_evaluated': n_templates,
        'strategies_selected': len(selected_idx)
    }
    
    if verbose:
        print(f"\n  Performance: {nnls_count} NNLS solves in {total_time:.3f}s ({nnls_count/total_time:.0f} solves/sec)")
    
    return selected_idx, timing_info


def approximate_nnls(target: np.ndarray, templates: np.ndarray, params: list = None, max_strategies = None):
    
    # Step 1: Solve full NNLS
    weights, _ = nnls(templates.T, target)
    
    nonzero = np.where(weights > 1e-6)[0]
    print(f"Initial NNLS: {len(nonzero)} non-zero strategies")
    print(f"  Indices: {nonzero}")
    print(f"  Weights: {weights[nonzero]}")
    
    # Compute full solution metrics (before any truncation)
    full_weights_normalized = weights / (np.sum(weights) + 1e-12)
    full_approximation = templates.T @ full_weights_normalized
    full_r_squared = _compute_r_squared(target, full_approximation)
    
    truncated = False
    truncated_r_squared = None
    
    # Step 2: If max_strategies is set, use GREEDY FORWARD SELECTION
    if max_strategies is not None and len(nonzero) > max_strategies:
        truncated = True
        
        # Use greedy forward selection instead of top-k by weight
        # This selects templates that work well TOGETHER, not just high-weight ones
        selected_idx, timing_info = greedy_select_templates(
            target, templates, max_strategies, 
            verbose=True
        )
        top_k_idx = np.array(selected_idx)
        
        print(f"\nGreedy selection chose indices: {top_k_idx}")
        if params is not None:
            for idx in top_k_idx:
                p = params[idx]
                print(f"  {p['type']:10s} center={p['center']:2d} width={p['width']:2d}")
        
        # Re-solve NNLS with selected templates to get final weights
        reduced_templates = templates[top_k_idx]
        reduced_weights, _ = nnls(reduced_templates.T, target)
        
        print(f"  Final weights: {reduced_weights}")
        
        # Check if any weights are near zero (shouldn't happen with greedy selection)
        near_zero = reduced_weights < 1e-6
        if np.any(near_zero):
            print(f"  Warning: {np.sum(near_zero)} strategies got ~0 weight")
        
        # Map back to full weight vector
        weights = np.zeros(len(templates))
        weights[top_k_idx] = reduced_weights
        nonzero = top_k_idx[reduced_weights > 1e-6]
    
    print(f"\nFinal: {len(nonzero)} strategies with non-zero weights")
    print(f"  Indices: {nonzero}")
    print(f"  Weights (raw): {weights[nonzero]}")

    # Normalize weights to sum to 1
    weight_sum = np.sum(weights)
    if weight_sum > 1e-12:
        weights = weights / weight_sum
    
    print(f"  Weights (normalized): {weights[nonzero]}")
    
    # Compute final approximation and metrics
    approximation = templates.T @ weights
    final_r_squared = _compute_r_squared(target, approximation)
    residual = np.linalg.norm(target - approximation)
    
    # Report truncation cost if applicable
    if truncated:
        truncated_r_squared = final_r_squared
        r_squared_loss = full_r_squared - truncated_r_squared
        print(f"\nTruncation metrics:")
        print(f"  Full solution R²:      {full_r_squared:.6f}")
        print(f"  Truncated solution R²: {truncated_r_squared:.6f}")
        print(f"  R² loss from truncation: {r_squared_loss:.6f}")
    
    # Build strategy list
    strategies = []
    if params is not None:
        strategies = [(params[i], weights[i]) for i in nonzero]
    
    result = {
        "weights": weights,
        "approximation": approximation,
        "residual": residual,
        "r_squared": final_r_squared,
        "strategies": strategies,
        "full_r_squared": full_r_squared,
        "truncated": truncated,
    }
    
    if truncated:
        result["truncated_r_squared"] = truncated_r_squared
        result["r_squared_loss"] = full_r_squared - truncated_r_squared
    
    return result
    
def create_gaussian_target(B, center=None, sigma=10):
    if center is None:
        center = B // 2
    
    x = np.arange(B)
    target = np.exp(-0.5 * ((x - center) / sigma) ** 2)
    target = target / target.sum()
    return target


def export_strategy_plan(result: dict, output_path: str, pool_config: dict = None) -> dict:
    """
    Export optimization result to JSON for TypeScript deployment.
    
    Args:
        result: Output from approximate_nnls() containing strategies and metrics
        output_path: Path to write JSON file
        pool_config: Optional pool configuration (poolAddress, binStep, activeBin)
        
    Returns:
        The strategy plan dict that was written
    """
    plan = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "metrics": {
            "r_squared": float(result["r_squared"]),
            "residual": float(result["residual"]),
            "truncated": result.get("truncated", False),
            "full_r_squared": float(result.get("full_r_squared", result["r_squared"]))
        },
        "strategies": [
            {
                "type": strat["type"],  # "rectangle" | "curve" | "bid_ask"
                "center": int(strat["center"]),
                "width": int(strat["width"]),
                "weight": float(weight)
            }
            for strat, weight in result["strategies"]
        ]
    }
    
    if pool_config:
        plan["pool_config"] = pool_config
    
    with open(output_path, 'w') as f:
        json.dump(plan, f, indent=2)
    
    print(f"\nStrategy plan exported to: {output_path}")
    return plan


def load_strategy_plan(input_path: str) -> dict:
    """
    Load a strategy plan from JSON file.
    
    Args:
        input_path: Path to JSON file
        
    Returns:
        Strategy plan dict
    """
    with open(input_path, 'r') as f:
        return json.load(f)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DLMM Compiler - Optimize liquidity distributions for Meteora DLMM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate Gaussian distribution with 3 strategies, export to JSON
  python templates.py --target gaussian --center 34 --sigma 12 --max-strategies 3 --output plan.json
  
  # Generate uniform distribution
  python templates.py --target uniform --center 34 --width 20 --max-strategies 2 --output plan.json
  
  # Run with visualization (no export)
  python templates.py --target gaussian --center 34 --sigma 10 --plot
        """
    )
    
    # Target distribution parameters
    parser.add_argument("--target", type=str, default="gaussian",
                        choices=["gaussian", "uniform", "curve", "bid_ask"],
                        help="Target distribution type (default: gaussian)")
    parser.add_argument("--center", type=int, default=34,
                        help="Center bin for target distribution (default: 34)")
    parser.add_argument("--sigma", type=float, default=12,
                        help="Sigma for Gaussian target (default: 12)")
    parser.add_argument("--width", type=int, default=25,
                        help="Width for uniform/curve/bid_ask target (default: 25)")
    parser.add_argument("--bins", type=int, default=69,
                        help="Total number of bins (default: 69)")
    
    # Optimization parameters
    parser.add_argument("--max-strategies", type=int, default=3,
                        help="Maximum number of strategies to use (default: 3)")
    
    # Output options
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output JSON file path for strategy plan")
    parser.add_argument("--plot", action="store_true",
                        help="Show visualization plots")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress verbose output")
    
    return parser.parse_args()


def create_target_distribution(target_type: str, B: int, center: int, sigma: float, width: int) -> np.ndarray:
    """Create a target distribution based on type."""
    if target_type == "gaussian":
        return create_gaussian_target(B, center=center, sigma=sigma)
    elif target_type == "uniform":
        target = rectangle(center, width, B)
    elif target_type == "curve":
        target = curve(center, width, B)
    elif target_type == "bid_ask":
        target = bid_ask(center, width, B)
    else:
        raise ValueError(f"Unknown target type: {target_type}")
    
    # Normalize
    return target / (np.sum(target) + 1e-12)


def visualize_results(target: np.ndarray, result: dict, B: int):
    """Display visualization plots."""
    approximation = result['approximation']
    
    plt.figure(figsize=(12, 5))
    
    # Plot target
    plt.subplot(1, 3, 1)
    plt.bar(range(B), target, alpha=0.7, color='blue', edgecolor='black', linewidth=0.5)
    plt.title('Target Position', fontsize=14, fontweight='bold')
    plt.xlabel('Bin')
    plt.ylabel('Liquidity')
    plt.grid(True, alpha=0.3)
    
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
    
    # Strategy contributions
    plt.figure(figsize=(14, 6))
    
    plt.subplot(1, 2, 1)
    bottom = np.zeros(B)
    colors = plt.cm.tab10(np.linspace(0, 1, len(result['strategies'])))
    
    for i, (strat, weight) in enumerate(result['strategies'][:8]):
        if strat['type'] == 'rectangle':
            strategy_vec = rectangle(strat['center'], strat['width'], B)
        elif strat['type'] == 'curve':
            strategy_vec = curve(strat['center'], strat['width'], B)
        elif strat['type'] == 'bid_ask':
            strategy_vec = bid_ask(strat['center'], strat['width'], B)
        
        strategy_vec = strategy_vec / (np.sum(strategy_vec) + 1e-12)
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


def main():
    """Main entry point for the DLMM Compiler."""
    args = parse_args()
    B = args.bins
    
    # Create target distribution
    if not args.quiet:
        print(f"Creating target distribution ({args.target})...")
        print(f"  Center: {args.center}, Bins: {B}")
        if args.target == "gaussian":
            print(f"  Sigma: {args.sigma}")
        else:
            print(f"  Width: {args.width}")
    
    target = create_target_distribution(
        args.target, B, args.center, args.sigma, args.width
    )
    
    # Generate templates
    if not args.quiet:
        print("\nGenerating templates...")
    templates, params = generate_templates(B, center_step=1, width_step=2)
    if not args.quiet:
        print(f"Generated {len(params)} templates")
    
    # Run optimization
    if not args.quiet:
        print(f"\nRunning NNLS optimization (max_strategies={args.max_strategies})...")
    
    result = approximate_nnls(target, templates, params, max_strategies=args.max_strategies)
    
    # Print results
    if not args.quiet:
        print(f"\n" + "=" * 50)
        print("OPTIMIZATION RESULTS")
        print("=" * 50)
        print(f"  R-squared: {result['r_squared']:.4f}")
        print(f"  Residual: {result['residual']:.6f}")
        print(f"  Strategies: {len(result['strategies'])}")
        
        if result['truncated']:
            print(f"\n  Truncation info:")
            print(f"    Full solution R²: {result['full_r_squared']:.4f}")
            print(f"    R² loss: {result.get('r_squared_loss', 0):.4f}")
        
        print(f"\nSelected strategies:")
        for i, (strat, weight) in enumerate(result['strategies'], 1):
            print(f"  {i}. {strat['type']:10s} | center={strat['center']:2d} width={strat['width']:2d} | weight={weight:.4f}")
    
    # Export to JSON if output path provided
    if args.output:
        export_strategy_plan(result, args.output)
    
    # Show plots if requested
    if args.plot:
        visualize_results(target, result, B)
    
    return result


if __name__ == "__main__":
    main()