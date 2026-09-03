import re
from pathlib import Path
try:
    from pypdf import PdfReader as Reader
except Exception:
    # pyrefly: ignore [missing-import]
    from PyPDF2 import PdfReader as Reader

def extract_and_chunk_pdf(pdf_path, law_name, chunk_size=500, overlap=100):
    """
    Extract text from a PDF and split into chunks.
    
    Args:
        pdf_path: Path to the PDF file
        law_name: Name of the law (e.g. "Pakistan Penal Code")
        chunk_size: Target words per chunk (default 500 for better retrieval precision)
        overlap: Number of overlapping words between chunks (prevents context loss at boundaries)
    """
    reader = Reader(str(pdf_path))
    chunks = []
    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        t = re.sub(r'\r\n?', '\n', text)
        
        # Skip blank or near-empty pages
        if not t.strip() or len(t.split()) < 5:
            continue
        
        # A real section heading is a numbered line at the start of a line, e.g.
        # "302. Punishment for qatl-e-amd." or an explicit "Section 20." label.
        # Requiring a number at line-start avoids matching prose such as
        # "this section may be attached...", which produced junk labels like "may".
        heading_re = re.compile(
            r'(?m)^[ \t]*(?:'
            r'(?:Section|Sec\.|S\.)[ \t]*[0-9]+[0-9A-Za-z\-.]*'
            r'|[0-9]{1,4}[A-Za-z]?\.[ \t]+[A-Z(]'
            r'|CHAPTER\b[^\n]*'
            r')',
            re.IGNORECASE
        )
        headings = list(heading_re.finditer(t))
        if headings:
            for i, h in enumerate(headings):
                start = h.start()
                end = headings[i+1].start() if i+1 < len(headings) else len(t)
                body = t[start:end].strip()
                header = body.split("\n", 1)[0].strip()
                
                # Skip empty sections
                if not body or len(body.split()) < 3:
                    continue
                
                # Extract the section number: prefer an explicit "Section N" label,
                # otherwise take the leading bare number ("302." -> "302").
                section_no = None
                m = re.search(r'(?:Section|Sec\.|S\.)[ \t]*([0-9]+[0-9A-Za-z\-.]*)', header, re.IGNORECASE)
                if not m:
                    m = re.match(r'([0-9]{1,4}[A-Za-z]?)\.', header)
                if m:
                    section_no = m.group(1).strip()
                
                # If section text is too long, split it with overlap
                section_words = body.split()
                if len(section_words) > chunk_size:
                    step = chunk_size - overlap
                    for ci in range(0, len(section_words), step):
                        chunk_body = " ".join(section_words[ci:ci + chunk_size])
                        if len(chunk_body.split()) < 3:
                            continue
                        chunks.append({
                            "law_name": law_name,
                            "section": f"{section_no or header[:80]}-part{ci // step + 1}" if ci > 0 else (section_no or header[:80]),
                            "text": chunk_body,
                            "page": page_num,
                            "source_path": str(pdf_path)
                        })
                else:
                    chunks.append({
                        "law_name": law_name,
                        "section": section_no or header[:80],
                        "text": body,
                        "page": page_num,
                        "source_path": str(pdf_path)
                    })
        else:
            # No headings found — split by word count with overlap
            words = t.split()
            if len(words) <= chunk_size:
                chunks.append({
                    "law_name": law_name,
                    "section": f"Page {page_num}",
                    "text": t,
                    "page": page_num,
                    "source_path": str(pdf_path)
                })
            else:
                step = chunk_size - overlap
                for i in range(0, len(words), step):
                    body = " ".join(words[i:i + chunk_size])
                    if len(body.split()) < 3:
                        continue
                    chunks.append({
                        "law_name": law_name,
                        "section": f"Page{page_num}-chunk{i // step + 1}",
                        "text": body,
                        "page": page_num,
                        "source_path": str(pdf_path)
                    })
    return chunks

if __name__ == "__main__":
    import json
    from pathlib import Path
    
    # Define PDF files and their law names (resolved relative to this file)
    backend_dir = Path(__file__).parent
    pdf_files = [
        (str(backend_dir / "CrPC.pdf"), "Code of Criminal Procedure"),
        (str(backend_dir / "PECA 2016.pdf"), "PECA 2016"),
        (str(backend_dir / "PECA 2025 Amendment.pdf"), "PECA 2025 Amendment"),
        (str(backend_dir / "PPC.pdf"), "Pakistan Penal Code")
    ]
    
    print("📚 Starting PDF extraction and chunking...")
    print(f"{'='*60}\n")
    
    all_chunks = []
    
    for pdf_path, law_name in pdf_files:
        pdf_file = Path(pdf_path)
        
        if not pdf_file.exists():
            print(f"⚠️  Warning: {pdf_file.name} not found at {pdf_path}")
            continue
        
        print(f"📄 Processing: {law_name}")
        print(f"   File: {pdf_file.name}")
        
        try:
            chunks = extract_and_chunk_pdf(pdf_path, law_name)
            all_chunks.extend(chunks)
            print(f"   ✅ Extracted {len(chunks)} chunks")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    # Summary
    print(f"{'='*60}")
    print(f"✅ Extraction Complete!")
    print(f"   Total chunks: {len(all_chunks)}")
    print(f"   Total PDFs processed: {len([p for p, _ in pdf_files if Path(p).exists()])}")
    print(f"{'='*60}\n")
    
    # Optionally save chunks to JSON
    output_file = "extracted_chunks.json"
    save_choice = input(f"💾 Save chunks to '{output_file}'? (y/n): ").strip().lower()
    
    if save_choice == 'y':
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(all_chunks)} chunks to {output_file}")
    
    print("\n💡 Next step: Run build_vector_db.py to create the vector database")
