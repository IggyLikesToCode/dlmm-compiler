# DLMM Compiler - Python Optimizer

Optimize arbitrary liquidity distributions into Meteora DLMM strategies using NNLS + greedy forward selection.

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/dlmm-compiler.git
cd dlmm-compiler/src/python
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install numpy scipy matplotlib streamlit plotly pandas
```

### 4. Run the Interactive UI

```bash
streamlit run ui.py
```

Then open **http://localhost:8501** in your browser.

---

## Usage

### Interactive UI (Recommended)

The UI has two tabs:

#### 📊 Optimizer Tab
- Generate distributions (Gaussian, uniform, curve, bid_ask)
- Load from JSON or CSV files
- Adjust max strategies (no limit)
- View optimization results with interactive charts

#### ✏️ Draw Distribution Tab
- Set custom bin count (10-100)
- Use presets (Flat, Peak, Edges, Random)
- Edit individual bin values in a table
- Live preview of your distribution
- Test optimization and export results

### Command Line

```bash
# Gaussian distribution with 3 strategies
python templates.py --target gaussian --center 34 --sigma 12 --max-strategies 3 -o plan.json

# Load from external JSON file
python templates.py --input-json my_distribution.json --max-strategies 5 -o plan.json

# Load from CSV
python templates.py --input-csv market_data.csv --max-strategies 4 -o plan.json

# With rebalancing state tracking
python templates.py --input-json target.json --state-file state.json --json-output -o plan.json
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--target` | Distribution type: gaussian, uniform, curve, bid_ask |
| `--center` | Center bin (default: 34) |
| `--sigma` | Sigma for Gaussian (default: 12) |
| `--width` | Width for other distributions (default: 25) |
| `--bins` | Number of bins (default: 69, auto-detected for external input) |
| `--max-strategies` | Maximum strategies to use (default: 3, no upper limit) |
| `--input-json` | Load target from JSON file |
| `--input-csv` | Load target from CSV file |
| `--input-api` | Fetch target from API endpoint |
| `--state-file` | State file for rebalancing tracking |
| `--output, -o` | Output JSON file for strategy plan |
| `--plot` | Show matplotlib visualization |
| `--json-output` | Output results as JSON (for automation) |
| `--quiet, -q` | Suppress verbose output |

---

## Input Formats

### JSON Format

```json
{
  "bins": [0.01, 0.02, 0.15, 0.3, 0.15, 0.02, 0.01],
  "metadata": {
    "source": "market_data",
    "timestamp": "2026-01-27T00:00:00Z"
  },
  "normalize": true
}
```

### CSV Format

Single column:
```csv
liquidity
0.01
0.02
0.15
0.30
0.15
0.02
0.01
```

Two columns:
```csv
bin_id,liquidity
0,0.01
1,0.02
2,0.15
...
```

---

## Output Format

### Strategy Plan (JSON)

```json
{
  "version": "1.0",
  "generated_at": "2026-01-27T10:30:00",
  "metrics": {
    "r_squared": 0.9954,
    "residual": 0.0113,
    "truncated": true,
    "full_r_squared": 1.0
  },
  "strategies": [
    {
      "type": "curve",
      "center": 12,
      "width": 19,
      "weight": 0.9039
    },
    {
      "type": "bid_ask",
      "center": 12,
      "width": 8,
      "weight": 0.0495
    }
  ]
}
```

---

## How It Works

1. **Template Generation**: Creates ~6,000 strategy templates from 3 base types (rectangle, curve, bid_ask) with varying centers and widths

2. **NNLS Optimization**: Solves non-negative least squares to find optimal weights for all templates

3. **Greedy Forward Selection**: Iteratively selects k best templates that maximize R² when used together

4. **Result**: Outputs strategy plan with selected strategies and their weights

---

## Files

| File | Description |
|------|-------------|
| `templates.py` | Core optimizer, CLI, template generation |
| `input_handlers.py` | JSON/CSV/API input parsing |
| `rebalancer.py` | Rebalancing state management |
| `ui.py` | Streamlit interactive UI |

---

## Requirements

- Python 3.10+
- numpy
- scipy
- matplotlib (for `--plot`)
- streamlit (for UI)
- plotly (for UI)
- pandas (for UI)
