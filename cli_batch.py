#!/usr/bin/env python
"""
Command-line batch processing wrapper for IFigure microscopy image analysis
"""

import argparse
import os
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description='Batch process microscopy images with IFigure analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i /path/to/images -o /path/to/output -f czi
  %(prog)s -i ./images -o ./results -f tif --blur 2.0
  %(prog)s --interactive
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        help='Input folder containing images',
        dest='input_dir'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output folder for processed images',
        dest='output_dir'
    )
    parser.add_argument(
        '-f', '--format',
        type=str,
        choices=['czi', 'tif', 'tiff', 'lsm', 'nd2', 'jpg', 'png'],
        default='czi',
        help='File format to process (default: czi)'
    )
    parser.add_argument(
        '--blur',
        type=float,
        default=1.0,
        help='Gaussian blur sigma value (default: 1.0)'
    )
    parser.add_argument(
        '--z-slice',
        type=int,
        help='Z slice to use (if not specified, will use middle slice)'
    )
    parser.add_argument(
        '--z-start',
        type=int,
        help='Start Z slice for projection'
    )
    parser.add_argument(
        '--z-end',
        type=int,
        help='End Z slice for projection'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive mode - prompt for folders and settings'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without running'
    )
    
    args = parser.parse_args()
    
    # Interactive mode
    if args.interactive:
        input_dir = input("Enter input folder path: ").strip()
        output_dir = input("Enter output folder path: ").strip()
        
        print("\nSupported formats: czi, tif, tiff, lsm, nd2, jpg, png")
        file_format = input("Enter file format (default: czi): ").strip() or "czi"
        
        blur_input = input("Enter blur sigma value (default: 1.0): ").strip()
        blur_sigma = float(blur_input) if blur_input else 1.0
    else:
        # Command-line mode
        if not args.input_dir or not args.output_dir:
            parser.print_help()
            print("\nError: -i/--input and -o/--output are required in non-interactive mode")
            sys.exit(1)
        
        input_dir = args.input_dir
        output_dir = args.output_dir
        file_format = args.format
        blur_sigma = args.blur
    
    # Validate input directory
    if not os.path.isdir(input_dir):
        print(f"Error: Input folder does not exist: {input_dir}")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Find matching files
    file_ext = f".{file_format}"
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(file_ext)]
    
    if not files:
        print(f"Error: No files found with extension {file_ext} in {input_dir}")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"Batch Processing Settings")
    print(f"{'='*60}")
    print(f"Input folder:     {input_dir}")
    print(f"Output folder:    {output_dir}")
    print(f"File format:      {file_format}")
    print(f"Blur sigma:       {blur_sigma}")
    print(f"Files to process: {len(files)}")
    print(f"{'='*60}\n")
    
    if args.dry_run:
        print("DRY RUN MODE - No files will be processed\n")
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f}")
        return
    
    print("Files to process:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f}")
    
    confirm = input("\nProceed with batch processing? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        sys.exit(0)
    
    # Import Fiji/ImageJ components
    try:
        from ij import IJ
        from ij.io import Opener, FileSaver
    except ImportError:
        print("Error: This script must be run from within Fiji/ImageJ")
        print("Please run this script using Fiji's Python interpreter:")
        print("  Plugins > Macros > Edit... (open this file)")
        print("  Then run with Macros > Run Macro")
        sys.exit(1)
    
    # Process files
    print(f"\nStarting batch processing of {len(files)} files...\n")
    
    processed = 0
    failed = 0
    
    for idx, filename in enumerate(files, 1):
        filepath = os.path.join(input_dir, filename)
        output_name = Path(filename).stem + "_figure.tif"
        output_path = os.path.join(output_dir, output_name)
        
        try:
            print(f"[{idx}/{len(files)}] Processing: {filename}")
            
            # Open image
            opener = Opener()
            imp = opener.openImage(filepath)
            imp.show()
            
            # Import and run IFigure processing
            ifigure_path = os.path.dirname(os.path.abspath(__file__))
            ifigure_script = os.path.join(ifigure_path, "IFigure.py")
            
            if not os.path.exists(ifigure_script):
                raise FileNotFoundError(f"IFigure.py not found at {ifigure_script}")
            
            # Execute processing
            exec(open(ifigure_script).read(), {'blur_sigma': blur_sigma})
            
            # Save result
            result_img = IJ.getImage()
            fs = FileSaver(result_img)
            fs.saveAsTiff(output_path)
            
            print(f"  ✓ Saved to: {output_name}")
            processed += 1
            
            # Close all windows
            IJ.run("Close All", "")
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            failed += 1
            try:
                IJ.run("Close All", "")
            except:
                pass
            continue
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Batch Processing Complete")
    print(f"{'='*60}")
    print(f"Processed:  {processed} files")
    print(f"Failed:     {failed} files")
    print(f"Output:     {output_dir}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
