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
    
    # Calculate statistics for each priority level
    high_events = len([x for x in high_row[1:] if x.strip() and x.strip().isdigit()])
    medium_events = len([x for x in medium_row[1:] if x.strip() and x.strip().isdigit()])
    low_events = len([x for x in low_row[1:] if x.strip() and x.strip().isdigit()])
    
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
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 100%;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 
                0 20px 40px rgba(0, 0, 0, 0.1),
                0 0 0 1px rgba(255, 255, 255, 0.2);
            overflow: hidden;
            animation: fadeInUp 0.8s ease-out;
        }}
        
        @keyframes fadeInUp {{
            from {{
                opacity: 0;
                transform: translateY(30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .header {{
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            padding: 40px 30px;
            text-align: center;
            color: white;
        }}
        
        h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }}
        
        .subtitle {{
            font-size: 1.1rem;
            opacity: 0.9;
            font-weight: 400;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .table-wrapper {{
            overflow-x: auto;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            margin-bottom: 30px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            min-width: 1200px;
            background: white;
        }}
        
        th, td {{
            border: 1px solid #e5e7eb;
            padding: 8px 12px;
            text-align: center;
            height: 40px;
            min-width: 40px;
            position: relative;
            transition: all 0.2s ease;
        }}
        
        th:hover, td:hover {{
            background-color: #f8fafc !important;
            transform: scale(1.02);
            z-index: 10;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }}
        
        .header-row th {{
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 12px;
        }}
        
        .label-col {{
            background: linear-gradient(135deg, #64748b 0%, #475569 100%) !important;
            color: white !important;
            font-weight: 600;
            min-width: 100px;
            text-align: left;
            padding-left: 16px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .high-q {{
            background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        }}
        
        .medium-q {{
            background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        }}
        
        .low-q {{
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        }}
        
        .queue-active {{
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
            color: white !important;
            font-weight: 700;
            font-size: 14px;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            animation: pulseActive 2s infinite;
            border: 2px solid #b91c1c !important;
        }}
        
        .queue-active.medium {{
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
            border-color: #b45309 !important;
        }}
        
        .queue-active.low {{
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
            border-color: #047857 !important;
        }}
        
        @keyframes pulseActive {{
            0%, 100% {{
                transform: scale(1);
            }}
            50% {{
                transform: scale(1.05);
            }}
        }}
        
        .split-id-row {{
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            font-weight: 500;
        }}
        
        .split-id-row td {{
            color: #475569;
            font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
        }}
        
        .legend {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            border: 1px solid #e5e7eb;
            transition: all 0.3s ease;
        }}
        
        .legend-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
            border-color: #3b82f6;
        }}
        
        .legend-color {{
            width: 24px;
            height: 24px;
            border-radius: 6px;
            border: 2px solid rgba(255, 255, 255, 0.8);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }}
        
        .legend-item span {{
            font-weight: 500;
            color: #374151;
        }}
        
        .info-panel {{
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            margin-top: 30px;
        }}
        
        .info-panel h3 {{
            color: #1e293b;
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .info-panel h3::before {{
            content: "▣";
            font-size: 1.2rem;
            color: #3b82f6;
        }}
        
        .info-panel p {{
            line-height: 1.6;
            color: #475569;
            margin-bottom: 12px;
        }}
        
        .info-panel p strong {{
            color: #1e293b;
            font-weight: 600;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin: 20px 0;
        }}
        
        .stat-item {{
            background: white;
            padding: 16px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            border: 1px solid #e5e7eb;
        }}
        
        .stat-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #3b82f6;
            display: block;
        }}
        
        .stat-label {{
            font-size: 0.9rem;
            color: #64748b;
            margin-top: 4px;
        }}
        
        /* Responsive Design */
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            .header {{
                padding: 30px 20px;
            }}
            
            h1 {{
                font-size: 2rem;
            }}
            
            .content {{
                padding: 20px;
            }}
            
            table {{
                font-size: 11px;
            }}
            
            th, td {{
                padding: 6px 8px;
                min-width: 35px;
            }}
        }}
        
        /* Print Styles */
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
                border-radius: 0;
            }}
            
            .header {{
                background: #4f46e5 !important;
                -webkit-print-color-adjust: exact;
                color-adjust: exact;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>WRR Trace Analysis Results</h1>
            <p class="subtitle">Weighted Round Robin Queue Activity Visualization</p>
        </div>
        
        <div class="content">
            <div class="table-wrapper">
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
            </div>
        
                <div class="legend">
                <div class="legend-item">
                    <div class="legend-color queue-active"></div>
                    <span>High Priority Queue Active (1-3)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color queue-active medium"></div>
                    <span>Medium Priority Queue Active (4-6)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color queue-active low"></div>
                    <span>Low Priority Queue Active (7-9)</span>
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-value">{1}</span>
                    <div class="stat-label">High Priority Events</div>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{2}</span>
                    <div class="stat-label">Medium Priority Events</div>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{3}</span>
                    <div class="stat-label">Low Priority Events</div>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{0}</span>
                    <div class="stat-label">Total Time Slices</div>
                </div>
            </div>
        
            <div class="info-panel">
                <h3>Analysis Information</h3>
                <p><strong>Queue Configuration:</strong></p>
                <p>• <strong>High Priority:</strong> Queues 1, 2, 3 (Red indicators)</p>
                <p>• <strong>Medium Priority:</strong> Queues 4, 5, 6 (Orange indicators)</p> 
                <p>• <strong>Low Priority:</strong> Queues 7, 8, 9 (Green indicators)</p>
                
                <p><strong>Visualization Details:</strong></p>
                <p>This interactive visualization displays Weighted Round Robin (WRR) arbitration behavior over time. Each column represents a time slice where queue activity is captured. The colored cells with numbers indicate which specific queue was active during that period. The split transaction IDs help correlate the activity with the original trace data.</p>
                
                <p><strong>Analysis Tips:</strong></p>
                <p>• Look for patterns in queue activation sequences</p>
                <p>• Observe how different priority levels are scheduled</p>
                <p>• Check for proper WRR weight distribution effectiveness</p>
            </div>
        </div>
    </div>
</body>
</html>""".format(data_length, high_events, medium_events, low_events)
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
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