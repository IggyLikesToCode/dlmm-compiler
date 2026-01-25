# DLMM Compiler

A modular open-source engine for constructing, optimizing, and deploying custom liquidity distributions on Meteora's Dynamic Liquidity Market Maker (DLMM) protocol.

## Overview

The DLMM Compiler solves a fundamental problem in DeFi liquidity management: translating an arbitrary desired liquidity distribution into deployable strategies that Meteora's protocol supports.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INPUT                                  │
│   "I want a Gaussian distribution centered at price X"              │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PYTHON OPTIMIZER                               │
│   1. Generate template library (rectangle, curve, bid_ask)          │
│   2. Run greedy forward selection to find best strategies           │
│   3. Output: JSON strategy plan with optimal weights                │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      TYPESCRIPT EXECUTOR                            │
│   1. Load strategy plan JSON                                        │
│   2. Map to Meteora StrategyType (Spot/Curve/BidAsk)                │
│   3. Deploy positions on-chain                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Installation

### Python Dependencies

```bash
pip install the requirements.txt
```

### TypeScript Dependencies

```bash
npm install
```

## Usage

### Python Optimizer (CLI)

Generate a strategy plan from a target distribution:

```bash
# Gaussian distribution with 3 strategies
python src/python/templates.py \
  --target gaussian \
  --center 34 \
  --sigma 12 \
  --max-strategies 3 \
  --output strategy_plan.json

# With visualization (To see plot)
python src/python/templates.py \
  --target gaussian \
  --center 34 \
  --sigma 10 \
  --max-strategies 3 \
  --plot
```

### CLI Options


 `--target`         -- Distribution type: gaussian, uniform, curve, bid_ask - Usually gaussian 
 `--center`         -- Center bin for the distribution                      - Usually 34 
 `--sigma`          -- Sigma for Gaussian distribution                      - Usually 12
 `--width`          -- Width for other distribution types                   - Usually 25 
 `--bins`           -- Total number of bins                                 - Usually 69 
 `--max-strategies` -- Maximum number of strategies                         - Usually 3
 `--output`, `-o`   -- Output JSON file path                                - Usually None
 `--plot`           -- Show visualization                                   - Usually False 
 `--quiet`, `-q`    -- Suppress verbose output                              - Usually False 


### TypeScript Executor

Preview a strategy plan:

```bash
npx ts-node src/sdk/executor.ts strategy_plan.json --preview
```

## Output Format

The strategy plan JSON format:

```json
{
  "version": "1.0",
  "generated_at": "2024-01-15T10:30:00",
  "metrics": {
    "r_squared": 0.9959,
    "residual": 0.0062,
    "truncated": true,
    "full_r_squared": 1.0
  },
  "strategies": [
    {
      "type": "curve",
      "center": 34,
      "width": 55,
      "weight": 0.89
    },
    {
      "type": "bid_ask",
      "center": 15,
      "width": 61,
      "weight": 0.055
    }
  ]
}
```

## Algorithm

The optimizer uses **greedy forward selection** with Non-Negative Least Squares (NNLS):

1. **Full NNLS**: Find optimal weights for all ~6000 templates
2. **Greedy Selection**: Iteratively select templates that maximize R² improvement
3. **Re-optimization**: Solve NNLS again with only selected templates

This achieves R² > 0.99 with just 3 strategies for most distributions.

## Project Structure

```
dlmm-compiler/
├── src/
│   ├── python/
│   │   ├── __init__.py      # Package exports
│   │   └── templates.py     # Core optimizer + CLI
│   └── sdk/
│       ├── client.ts        # Meteora DLMM client
│       └── executor.ts      # Strategy executor
├── config/
│   └── pool_config.json     # Pool configuration
├── requirements.txt         # Python dependencies
└── package.json            # Node dependencies
```


## Author

me
