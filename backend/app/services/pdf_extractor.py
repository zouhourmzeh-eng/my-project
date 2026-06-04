import os
import logging
import fitz  # PyMuPDF
import docx  # python-docx
import openpyxl  # openpyxl

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extracts raw text from a PDF file using PyMuPDF.
    """
    if not file_path or not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return ""
    
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        logger.error(f"Error extracting text from PDF {file_path}: {e}")
    
    return text.strip()

def extract_text_from_docx(file_path: str) -> str:
    """
    Extracts raw text from a DOCX file using python-docx.
    """
    if not file_path or not os.path.exists(file_path):
        return ""
    
    text = []
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text for cell in row.cells]
                text.append(" | ".join(row_cells))
    except Exception as e:
        logger.error(f"Error extracting text from DOCX {file_path}: {e}")
    
    return "\n".join(text).strip()

def extract_text_from_xlsx(file_path: str) -> str:
    """
    Extracts raw text from a XLSX file using openpyxl.
    """
    if not file_path or not os.path.exists(file_path):
        return ""
    
    text = []
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            text.append(f"--- Sheet: {sheet_name} ---")
            for row in ws.iter_rows(values_only=True):
                row_str = " | ".join(str(cell) for cell in row if cell is not None)
                if row_str.strip():
                    text.append(row_str)
    except Exception as e:
        logger.error(f"Error extracting text from XLSX {file_path}: {e}")
    
    return "\n".join(text).strip()

def extract_text_from_file(file_path: str) -> str:
    """
    Extracts text from PDF, DOCX, or XLSX file based on file extension.
    """
    if not file_path or not os.path.exists(file_path):
        return ""
    
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    elif ext in [".xlsx", ".xls"]:
        return extract_text_from_xlsx(file_path)
    else:
        logger.warning(f"Unsupported file format for text extraction: {ext}")
        return ""
