# file: src/cli/etc/pdf/merge.py
import os
from PyPDF2 import PdfMerger

# Initialize merger
merger = PdfMerger()

# List all PDFs in current directory
pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]

# Sort by filename
pdf_files.sort()

# Append each PDF
for pdf in pdf_files:
    merger.append(pdf)

# Write output
output_file = "merged.pdf"
merger.write(output_file)
merger.close()

print(f"Merged {len(pdf_files)} PDFs into {output_file}")
