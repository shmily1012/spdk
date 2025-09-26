#!/usr/bin/env python3
"""
WRR Trace HTML Generator
Generates HTML visualization from WRR trace text files

Usage: python wrr_html_generator.py -i WRR_trace.txt -o output.html
"""

from __future__ import print_function
import argparse
import sys
import os

def parse_trace_data(trace_file):
    """Parse the trace text file directly with improved SQ detection"""
    
    # SQ base addresses (as you prefer)
    SQ1_base_adr = 0x274a10000
    SQ2_base_adr = 0x274c20000
    SQ3_base_adr = 0x274c10000
    SQ4_base_adr = 0x1a1248000
    SQ5_base_adr = 0x275a48000
    SQ6_base_adr = 0x275648000
    SQ7_base_adr = 0x275448000
    SQ8_base_adr = 0x275048000
    SQ9_base_adr = 0x274e48000
    
    # Priority groups
    High = [1, 2, 3]
    Middle = [4, 5, 6] 
    Low = [7, 8, 9]
    
    # Address mask for SQ base matching (consistent 4KB alignment)
    SQ_BASE_MASK = 0xFFFFFFFFFFFFF000
    
    packets_array = []
    parse_stats = {'total_lines': 0, 'matched_lines': 0, 'parse_errors': 0}
    
    try:
        with open(trace_file, 'r') as fi:
            buf = fi.readlines()
    except Exception as e:
        print("Error reading trace file: {0}".format(e))
        sys.exit(1)
    
    parse_stats['total_lines'] = len(buf)
    line_id = 0
    
    # Parse trace data
    while line_id < len(buf):
        try:
            line = buf[line_id]
            if 'Upstream' in line and 'Mem MRd' in line and 'Split Tra' in line:
                parse_stats['matched_lines'] += 1
                
                split_id, address, data_size = _extract_trace_info(buf, line_id)
                if split_id is None:
                    parse_stats['parse_errors'] += 1
                    line_id += 1
                    continue
                
                # Determine SQ_ID based on address (consistent mask)
                SQ_ID = None
                masked_addr = address & SQ_BASE_MASK
                if masked_addr == (SQ1_base_adr & SQ_BASE_MASK):
                    SQ_ID = 1
                elif masked_addr == (SQ2_base_adr & SQ_BASE_MASK):
                    SQ_ID = 2
                elif masked_addr == (SQ3_base_adr & SQ_BASE_MASK):
                    SQ_ID = 3
                elif masked_addr == (SQ4_base_adr & SQ_BASE_MASK):
                    SQ_ID = 4
                elif masked_addr == (SQ5_base_adr & SQ_BASE_MASK):
                    SQ_ID = 5
                elif masked_addr == (SQ6_base_adr & SQ_BASE_MASK):
                    SQ_ID = 6
                elif masked_addr == (SQ7_base_adr & SQ_BASE_MASK):
                    SQ_ID = 7
                elif masked_addr == (SQ8_base_adr & SQ_BASE_MASK):
                    SQ_ID = 8
                elif masked_addr == (SQ9_base_adr & SQ_BASE_MASK):
                    SQ_ID = 9
                
                if SQ_ID is not None:
                    # Calculate number of commands (64 bytes per NVMe command)
                    num_cmds = max(1, data_size // 64) if data_size > 0 else 1
                    
                    # Add packets to array
                    for _ in range(num_cmds):
                        packets_array.append({
                            'split_id': split_id,
                            'sq_id': SQ_ID,
                            'address': address,
                            'data_size': data_size
                        })
        
        except Exception as e:
            parse_stats['parse_errors'] += 1
            print("Warning: Parse error at line {0}: {1}".format(line_id, e))
        
        line_id += 1
    
    # Print parsing statistics
    print("\nParsing Statistics:")
    print("  Total lines processed: {0}".format(parse_stats['total_lines']))
    print("  Matching lines found: {0}".format(parse_stats['matched_lines']))
    print("  Parse errors: {0}".format(parse_stats['parse_errors']))
    print("  Valid packets extracted: {0}".format(len(packets_array)))
    
    # Convert packets to queue activity arrays
    High_Q = ['High']
    Mid_Q = ['Medium'] 
    Low_Q = ['Low']
    
    for packet in packets_array:
        if packet['sq_id'] in High:
            High_Q.append(str(packet['sq_id']))
            Mid_Q.append('')
            Low_Q.append('')
        elif packet['sq_id'] in Middle:
            High_Q.append('')
            Mid_Q.append(str(packet['sq_id']))
            Low_Q.append('')
        elif packet['sq_id'] in Low:
            High_Q.append('')
            Mid_Q.append('')
            Low_Q.append(str(packet['sq_id']))
    
    # Handle case where no valid data was found
    if len(High_Q) == 1:  # Only header, no data found
        print("Warning: No valid queue activity found in trace file")
        # Add some dummy data for demonstration
        High_Q.extend(['', '', '', ''])
        Mid_Q.extend(['', '', '', ''])
        Low_Q.extend(['', '', '', ''])
    
    # Extract unique split IDs in order for HTML generation
    seen_split_ids = set()
    actual_split_ids = []
    for packet in packets_array:
        split_id = packet['split_id']
        if split_id not in seen_split_ids:
            seen_split_ids.add(split_id)
            actual_split_ids.append(split_id)
    
    return High_Q, Mid_Q, Low_Q, actual_split_ids

def _extract_trace_info(buf, line_id):
    """Extract Split ID, Address, and Data Size from trace lines"""
    split_id = None
    address = 0x0
    data_size = 0
    
    try:
        # Extract Split ID
        line = buf[line_id]
        start = line.index('Split Tra(') + len('Split Tra(')
        end = line.index(')', start)
        split_id = int(line[start:end], 10)
        
        # Look for Address and Data in next few lines
        search_range = min(10, len(buf) - line_id)
        
        for i in range(search_range):
            current_line = buf[line_id + i]
            
            # Extract Address
            if address == 0x0 and 'Address(' in current_line:
                try:
                    start = current_line.index('Address(') + len('Address(')
                    end = current_line.index(')', start)
                    addr_str = current_line[start:end]
                    
                    if ':' in addr_str:
                        # Handle format like "4:274a10000"
                        parts = addr_str.split(':')
                        high_addr = int(parts[0], 16)
                        low_addr = int(parts[1], 16) 
                        address = (high_addr << 32) | low_addr
                    else:
                        address = int(addr_str, 16)
                except (ValueError, IndexError):
                    continue
            
            # Extract Data Size
            if data_size == 0 and 'Data(' in current_line:
                try:
                    start = current_line.index('Data(') + len('Data(')
                    end = current_line.index('B', start)
                    data_size = int(current_line[start:end], 10)
                except (ValueError, IndexError):
                    continue
            
            # Break early if we have all info
            if address != 0x0 and data_size > 0:
                break
    
    except (ValueError, IndexError):
        return None, 0, 0
    
    return split_id, address, data_size

def generate_html(high_row, medium_row, low_row, output_file, split_ids=None):
    """Generate HTML file with table visualization"""
    
    data_length = len(high_row) - 1  # Subtract 1 for the header column
    
    # Use provided split IDs or generate fallback ones
    if split_ids is None or len(split_ids) == 0:
        # Fallback: generate sequential split IDs
        base_split_id = 2684
        split_ids = []
        current_id = base_split_id
        for i in range(data_length):
            if i > 0 and i % 4 == 0:  # Change split ID every 4 columns  
                current_id += 66
            split_ids.append(str(current_id))
    else:
        # Pad or trim split_ids to match data_length
        if len(split_ids) < data_length:
            # Repeat last split_id for missing entries
            last_id = split_ids[-1] if split_ids else 2684
            while len(split_ids) < data_length:
                split_ids.append(str(last_id))
        elif len(split_ids) > data_length:
            split_ids = split_ids[:data_length]
        
        # Convert to strings
        split_ids = [str(sid) for sid in split_ids]
    
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WRR Trace Analysis Results</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        
        .container {{
            max-width: 100%;
            overflow-x: auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            min-width: 1200px;
        }}
        
        th, td {{
            border: 1px solid #000;
            padding: 4px 6px;
            text-align: center;
            height: 25px;
            min-width: 30px;
        }}
        
        .header-row {{
            background-color: #e6e6e6;
            font-weight: bold;
        }}
        
        .label-col {{
            background-color: #e6e6e6;
            font-weight: bold;
            min-width: 80px;
            text-align: left;
            padding-left: 10px;
        }}
        
        .high-q {{
            background-color: #ffcccc;
        }}
        
        .medium-q {{
            background-color: #ffffcc;
        }}
        
        .low-q {{
            background-color: #ccffcc;
        }}
        
        .queue-active {{
            background-color: #ff6666;
            color: white;
            font-weight: bold;
        }}
        
        .queue-active.medium {{
            background-color: #ffaa00;
        }}
        
        .queue-active.low {{
            background-color: #00aa00;
        }}
        
        .split-id-row {{
            background-color: #f0f0f0;
        }}
        
        .info-panel {{
            margin-top: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-left: 4px solid #007bff;
        }}
        
        .legend {{
            margin-top: 20px;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border: 1px solid #000;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>WRR Trace Analysis Results</h1>
        
        <table>
            <tr class="header-row">
                <th class="label-col">idx</th>"""
    
    # Add column headers (starting from index 46 as shown in the image)
    start_idx = 46
    for i in range(data_length):
        html_content += '<th>{0}</th>'.format(start_idx + i)
    
    html_content += """
            </tr>
            <tr class="split-id-row">
                <th class="label-col">Split id</th>"""
    
    # Add split IDs
    for split_id in split_ids:
        html_content += '<td>{0}</td>'.format(split_id)
    
    html_content += """
            </tr>
            <tr class="high-q">
                <td class="label-col">High Q</td>"""
    
    # Add High Q data
    for i in range(1, len(high_row)):  # Skip the first element (header)
        cell_value = high_row[i] if i < len(high_row) else ''
        if cell_value and cell_value.strip() and cell_value.strip().isdigit():
            html_content += '<td class="queue-active">{0}</td>'.format(cell_value)
        else:
            html_content += '<td></td>'
    
    html_content += """
            </tr>
            <tr class="medium-q">
                <td class="label-col">Medium Q</td>"""
    
    # Add Medium Q data
    for i in range(1, len(medium_row)):  # Skip the first element (header)
        cell_value = medium_row[i] if i < len(medium_row) else ''
        if cell_value and cell_value.strip() and cell_value.strip().isdigit():
            html_content += '<td class="queue-active medium">{0}</td>'.format(cell_value)
        else:
            html_content += '<td></td>'
    
    html_content += """
            </tr>
            <tr class="low-q">
                <td class="label-col">Low Q</td>"""
    
    # Add Low Q data
    for i in range(1, len(low_row)):  # Skip the first element (header)
        cell_value = low_row[i] if i < len(low_row) else ''
        if cell_value and cell_value.strip() and cell_value.strip().isdigit():
            html_content += '<td class="queue-active low">{0}</td>'.format(cell_value)
        else:
            html_content += '<td></td>'
    
    html_content += """
            </tr>
        </table>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color queue-active"></div>
                <span>High Priority Queue Active</span>
            </div>
            <div class="legend-item">
                <div class="legend-color queue-active medium"></div>
                <span>Medium Priority Queue Active</span>
            </div>
            <div class="legend-item">
                <div class="legend-color queue-active low"></div>
                <span>Low Priority Queue Active</span>
            </div>
        </div>
        
        <div class="info-panel">
            <h3>Analysis Information</h3>
            <p><strong>Total Columns:</strong> {0}</p>
            <p><strong>High Priority Queues:</strong> 1, 2, 3</p>
            <p><strong>Medium Priority Queues:</strong> 4, 5, 6</p>
            <p><strong>Low Priority Queues:</strong> 7, 8, 9</p>
            <p><strong>Description:</strong> This visualization shows the activity of different priority queues over time. 
               Each column represents a time slice, and the numbers in colored cells indicate which specific queue was active.</p>
        </div>
    </div>
</body>
</html>""".format(data_length)
    
    try:
        with open(output_file, 'w') as f:
            f.write(html_content)
        print("HTML file generated successfully: {0}".format(output_file))
    except Exception as e:
        print("Error writing HTML file: {0}".format(e))
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Generate HTML visualization from WRR trace text files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s -i WRR_trace.txt -o visualization.html
  %(prog)s --input trace_data.txt --output report.html --verbose
        '''
    )
    
    parser.add_argument('-i', '--input', 
                       required=True,
                       help='Input trace text file')
    
    parser.add_argument('-o', '--output', 
                       required=True,
                       help='Output HTML file path')
    
    parser.add_argument('-v', '--verbose', 
                       action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not os.path.isfile(args.input):
        print("Error: Input file '{0}' does not exist.".format(args.input))
        sys.exit(1)
    
    # Validate output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        print("Error: Output directory '{0}' does not exist.".format(output_dir))
        sys.exit(1)
    
    if args.verbose:
        print("Reading trace data from: {0}".format(args.input))
    
    # Parse trace data
    high_row, medium_row, low_row, actual_split_ids = parse_trace_data(args.input)
    
    if args.verbose:
        print("Data parsed successfully:")
        print("  High Q entries: {0}".format(len([x for x in high_row[1:] if x.strip()])))
        print("  Medium Q entries: {0}".format(len([x for x in medium_row[1:] if x.strip()])))
        print("  Low Q entries: {0}".format(len([x for x in low_row[1:] if x.strip()])))
        print("  Total packets processed: {0}".format(len(high_row) - 1))
        print("  Unique split IDs found: {0}".format(len(actual_split_ids)))
    
    # Generate HTML
    generate_html(high_row, medium_row, low_row, args.output, actual_split_ids)
    
    if args.verbose:
        print("HTML visualization generated successfully!")

if __name__ == '__main__':
    main()