
    Core Algorithm Flow:
Template Generation (generate_templates()):
    Generates a library of possible strategies by varying:
    Strategy type (rectangle, curve, bid_ask)
    Center position (where the strategy is centered)
    Width (how many bins it spans)
    Each template is normalized to sum to 1.0
NNLS Approximation (approximate_nnls()):
    Takes a target distribution and the template library
    Solves: min ||Ax - b|| where A = templates, b = target, x ≥ 0
    Returns optimal weights for each strategy template
    Supports limiting to max_strategies for practical deployment
Output Metrics:
    R-squared value (fit quality)
    Residual error
    List of strategies with their weights



Shape	Function	Description	Meteora Equivalent
rectangle	Uniform distribution	Flat liquidity across bins	Spot strategy
curve	Triangular peak	Linear falloff from center	Curve strategy
bid_ask	Inverted triangle	High at edges, low at center

Then we approcimate templates to get Gaussian distribution




: CODE understanding:

73:
"""
    Approximate a target distribution using Non-Negative Least Squares.
    
    When max_strategies is set, the algorithm:
    1. Solves full NNLS to find optimal weights across all templates
    2. Selects the top-k strategies by weight
    3. Re-solves NNLS with only those k templates to get optimal weights for the subset
    
    This ensures the returned weights are truly optimal for the selected strategies,
    rather than just keeping the original weights which may be suboptimal when
    other strategies are removed.
    
    Args:
        target: Target distribution vector (normalized)
        templates: Matrix of template distributions (each row is a template)
        params: Optional list of parameter dicts describing each template
        max_strategies: Optional limit on number of strategies to use
        
    Returns:
        Dictionary containing weights, approximation, metrics, and strategy details
"""




greedy_select_templates:
    """
    Greedily select k templates that best approximate the target.
    
    At each step, adds the template that most improves R². This ensures
    the selected templates work well together as a small set.
    
    Features:
    - Full search over all templates (required for quality)
    - Early termination: Stops if R² improvement drops below threshold
    - Timing: Reports performance metrics
    
    Returns:
        tuple: (selected_indices, timing_info)
    """