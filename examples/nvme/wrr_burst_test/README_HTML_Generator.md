# WRR Trace HTML Generator

This directory contains tools for generating HTML visualizations directly from WRR (Weighted Round Robin) trace text files.

## Files

- `WRR_Trace_Analyze.py` - Original analyzer (generates CSV data)
- `wrr_html_generator.py` - **Main Tool**: Generates HTML directly from trace text files  

## Quick Start

### Direct HTML Generation (Recommended)
```bash
# Generate HTML visualization directly from trace file
python wrr_html_generator.py -i WRR_trace.txt -o report.html

# With verbose output
python wrr_html_generator.py -i WRR_trace.txt -o report.html --verbose
```

### Traditional Two-Step Process (Legacy)
1. **Analyze trace file:**
```bash
python WRR_Trace_Analyze.py
# This generates results_WRR_trace.csv
```

2. **Generate HTML from CSV:**
```bash
# Note: wrr_html_generator.py also supports CSV input for backward compatibility
python wrr_html_generator.py -i results_WRR_trace.csv -o visualization.html
```

## Command Line Options

### `wrr_html_generator.py`
```
usage: wrr_html_generator.py [-h] -i INPUT -o OUTPUT [-v]

Generate HTML visualization from WRR trace text files

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        Input trace text file
  -o OUTPUT, --output OUTPUT
                        Output HTML file path
  -v, --verbose         Enable verbose output

Examples:
  wrr_html_generator.py -i WRR_trace.txt -o visualization.html
  wrr_html_generator.py --input trace_data.txt --output report.html --verbose
```


## Output Format

The HTML visualization displays:

- **Table Layout**: Similar to the original image with time-indexed columns
- **Split ID Row**: Shows the split transaction IDs
- **Priority Rows**: 
  - High Q (red): Queues 1, 2, 3
  - Medium Q (orange): Queues 4, 5, 6  
  - Low Q (green): Queues 7, 8, 9
- **Color Coding**: Active queues are highlighted with their priority colors
- **Legend**: Explains the color scheme
- **Info Panel**: Shows analysis summary and queue assignments

## Input Format

### Trace Text File
The input file should be a trace text file containing lines with patterns like:
```
... Upstream ... Mem MRd ... Split Tra(2684) ...
... Address(0x274a10000) ...
... Data(256B) ...
```

Where:
- Lines contain "Upstream", "Mem MRd", and "Split Tra" to identify split transactions
- "Address()" contains the memory address being accessed
- "Data()" contains the data size (used to calculate number of commands)
- The tool matches addresses to queue base addresses to determine which queue (1-9) was active

### Legacy CSV Format (Still Supported)
If using the legacy CSV approach via `WRR_Trace_Analyze.py`:
```
High,4,4,4,4,7,7,7,7, , , , , ,1,1,1,1,4,4,4,4, , , , , ,
Medium, , , , ,8,8,8, , , , , , , , , , , , , ,2,2,2, ,
Low, , , , , , , ,6,6, , , , , , , , , , , , , , ,3,3,
```

## Python Version Compatibility

All scripts are compatible with both Python 2.7+ and Python 3.x thanks to:
- `from __future__ import print_function`
- `from __future__ import division`
- Consistent string formatting using `.format()`

## Dependencies

- Standard Python libraries only (no external packages required)
- `argparse` for command-line parsing
- `csv` for CSV file handling  
- `subprocess` for running external scripts

## Troubleshooting

### Common Issues

1. **"WRR_Trace_Analyze.py not found"**
   - Ensure all scripts are in the same directory
   - Check file permissions

2. **"CSV file must contain at least 3 lines"**
   - Verify the trace analysis completed successfully
   - Check that the input trace file has valid data

3. **"Input file does not exist"**
   - Verify the file path is correct
   - Use absolute paths if needed

### Debug Tips

- Use `-v` or `--verbose` flag for detailed output
- Use `--keep-csv` to inspect intermediate CSV data
- Check that trace file contains expected patterns:
  - "Upstream" and "Mem MRd" and "Split Tra"
  - "Address(" entries
  - "Data(" entries

## Example Workflow

```bash
# 1. Run WRR burst test to generate trace
./wrr_burst_test > WRR_trace.txt 2>&1

# 2. Generate HTML report  
python wrr_html_generator.py -i WRR_trace.txt -o wrr_analysis.html -v

# 3. Open in browser
open wrr_analysis.html  # macOS
# or
xdg-open wrr_analysis.html  # Linux
# or open manually in your web browser
```

The generated HTML file will show a visual representation of queue activity over time, helping to analyze the effectiveness of the WRR arbitration settings.