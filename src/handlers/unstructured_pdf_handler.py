"""
Unstructured API PDF Handler for Financial Documents
Created: October 29, 2025
Purpose: Replace PyMuPDF extraction with VLM-powered Unstructured API
"""

import os
import json
import base64
import requests
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnstructuredPDFHandler:
    """
    Modern PDF extraction using Unstructured API with VLM capabilities
    Optimized for financial documents (Rosenberg, Goldman, UBS, etc.)
    """
    
    def __init__(self):
        """Initialize with API credentials from environment"""
        # Load credentials securely
        self.load_credentials()
        
        # API configuration
        self.api_url = os.getenv('UNSTRUCTURED_API_URL', 
                                 'https://api.unstructuredapp.io/general/v0/general')
        
        # Strategy mapping for different document types
        self.strategy_map = {
            'Rosenberg Research': 'hi_res',  # Best for charts
            'Goldman Sachs': 'hi_res',        # Complex layouts
            'UBS Research': 'hi_res',         # Tables and charts
            'JPMorgan': 'hi_res',             # Mixed content
            'default': 'auto'                 # Let API decide
        }
        
    def load_credentials(self):
        """Load API key from secure environment file"""
        env_file = '/home/ubuntu/.env_unstructured'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if 'UNSTRUCTURED_API_KEY' in line:
                        key = line.split('=')[1].strip()
                        os.environ['UNSTRUCTURED_API_KEY'] = key
                        self.api_key = key
                        logger.info("✅ Unstructured API key loaded")
                        return
        
        # Fallback to environment variable
        self.api_key = os.getenv('UNSTRUCTURED_API_KEY')
        if not self.api_key:
            raise ValueError("❌ UNSTRUCTURED_API_KEY not found!")
    
    def process_pdf(self, 
                    pdf_path: str, 
                    sender_tag: str = 'default',
                    extract_charts: bool = True,
                    extract_tables: bool = True) -> Dict[str, Any]:
        """
        Main method to process PDF using Unstructured API
        
        Args:
            pdf_path: Path to PDF file
            sender_tag: Document source (affects processing strategy)
            extract_charts: Whether to extract chart data
            extract_tables: Whether to extract table data
            
        Returns:
            Dictionary with extracted content, charts, tables, metadata
        """
        
        logger.info(f"📄 Processing PDF: {pdf_path}")
        logger.info(f"📊 Strategy for {sender_tag}: {self.strategy_map.get(sender_tag, 'auto')}")
        
        try:
            # Step 1: Prepare the API request
            headers = {
                'unstructured-api-key': self.api_key,
                'Accept': 'application/json'
            }
            
            # Determine processing strategy based on sender
            strategy = self.strategy_map.get(sender_tag, 'auto')
            
            # Parameters for API call
            params = {
                'strategy': strategy,
                'pdf_infer_table_structure': extract_tables,
                'extract_image_block_types': ['Image', 'Table'] if extract_charts else [],
                'include_page_breaks': True,
                'languages': ['eng'],
                'encoding': 'utf-8'
            }
            
            # Step 2: Send PDF to Unstructured API
            with open(pdf_path, 'rb') as f:
                files = {'files': (os.path.basename(pdf_path), f, 'application/pdf')}
                
                logger.info(f"🚀 Sending to Unstructured API with {strategy} strategy...")
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    files=files,
                    data=params,
                    timeout=120  # 2 minutes timeout for large PDFs
                )
            
            # Step 3: Process the response
            if response.status_code == 200:
                elements = response.json()
                logger.info(f"✅ Received {len(elements)} elements from API")
                
                # Step 4: Structure the extracted content
                result = self.structure_content(elements, sender_tag)
                
                # Step 5: Add metadata
                result['metadata'] = {
                    'file_name': os.path.basename(pdf_path),
                    'sender_tag': sender_tag,
                    'strategy_used': strategy,
                    'processed_at': datetime.now().isoformat(),
                    'element_count': len(elements),
                    'api_version': 'unstructured_v0'
                }
                
                logger.info("✅ PDF processing complete!")
                return result
                
            else:
                logger.error(f"❌ API Error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                # Fallback to current method
                return self.fallback_extraction(pdf_path)
                
        except Exception as e:
            logger.error(f"❌ Error processing PDF: {str(e)}")
            # Fallback to current PyMuPDF method
            return self.fallback_extraction(pdf_path)
    
    def structure_content(self, elements: List[Dict], sender_tag: str) -> Dict[str, Any]:
        """
        Structure the raw elements from Unstructured API into organized content
        """
        
        result = {
            'content_text': '',
            'content_html': '<html><body>',
            'charts': [],
            'tables': [],
            'key_sections': {},
            'reconstructed_charts': []
        }
        
        current_section = None
        text_parts = []
        
        for element in elements:
            elem_type = element.get('type', 'Unknown')
            text = element.get('text', '')
            metadata = element.get('metadata', {})
            
            # Handle different element types
            if elem_type == 'Title':
                current_section = text
                result['key_sections'][current_section] = []
                text_parts.append(f"\n## {text}\n")
                result['content_html'] += f"<h2>{text}</h2>"
                
            elif elem_type in ['NarrativeText', 'Text']:
                text_parts.append(text)
                result['content_html'] += f"<p>{text}</p>"
                if current_section:
                    result['key_sections'][current_section].append(text)
                    
            elif elem_type == 'Table':
                table_data = self.extract_table_data(element)
                result['tables'].append({
                    'type': 'table',
                    'data': table_data,
                    'html': self.table_to_html(table_data),
                    'can_reconstruct': True,
                    'context': current_section
                })
                result['content_html'] += self.table_to_html(table_data)
                
            elif elem_type in ['Image', 'FigureCaption']:
                chart_info = self.process_chart(element, sender_tag)
                result['charts'].append(chart_info)
                
                if chart_info.get('base64'):
                    result['content_html'] += f'''
                    <div class="chart">
                        <img src="data:image/png;base64,{chart_info['base64']}" />
                        <p>{chart_info.get('caption', '')}</p>
                    </div>'''
                    
            elif elem_type == 'ListItem':
                text_parts.append(f"• {text}")
                result['content_html'] += f"<li>{text}</li>"
                
            elif elem_type == 'PageBreak':
                text_parts.append("\n---PAGE BREAK---\n")
                result['content_html'] += "<hr />"
        
        # Combine text parts
        result['content_text'] = '\n'.join(text_parts)
        result['content_html'] += '</body></html>'
        
        # Special handling for financial documents
        if sender_tag == 'Rosenberg Research':
            result = self.enhance_rosenberg_content(result, elements)
        elif sender_tag == 'Goldman Sachs':
            result = self.enhance_goldman_content(result, elements)
            
        return result
    
    def extract_table_data(self, element: Dict) -> Dict[str, Any]:
        """Extract structured table data from Unstructured element"""
        text = element.get('text', '')
        lines = text.strip().split('\n')
        
        if lines:
            headers = lines[0].split('\t') if '\t' in lines[0] else lines[0].split('  ')
            headers = [h.strip() for h in headers if h.strip()]
            
            rows = []
            for line in lines[1:]:
                if line.strip():
                    cells = line.split('\t') if '\t' in line else line.split('  ')
                    cells = [c.strip() for c in cells if c.strip()]
                    if cells:
                        rows.append(cells)
            
            return {'headers': headers, 'rows': rows, 'raw_text': text}
        
        return {'raw_text': text}
    
    def table_to_html(self, table_data: Dict) -> str:
        """Convert table data to HTML"""
        if 'headers' in table_data and 'rows' in table_data:
            html = '<table border="1" style="border-collapse: collapse;">'
            html += '<thead><tr>'
            for header in table_data['headers']:
                html += f'<th>{header}</th>'
            html += '</tr></thead><tbody>'
            for row in table_data['rows']:
                html += '<tr>'
                for cell in row:
                    html += f'<td>{cell}</td>'
                html += '</tr>'
            html += '</tbody></table>'
            return html
        
        return f'<pre>{table_data.get("raw_text", "")}</pre>'
    
    def process_chart(self, element: Dict, sender_tag: str) -> Dict[str, Any]:
        """Process chart/image element"""
        metadata = element.get('metadata', {})
        
        chart_info = {
            'type': 'chart',
            'caption': element.get('text', ''),
            'page_number': metadata.get('page_number'),
            'can_reconstruct': False
        }
        
        if 'image_base64' in metadata:
            chart_info['base64'] = metadata['image_base64']
        
        if 'extracted_data' in metadata:
            chart_info['data_points'] = metadata['extracted_data']
            chart_info['can_reconstruct'] = True
            
        if sender_tag in ['Rosenberg Research', 'Goldman Sachs']:
            chart_info['requires_analysis'] = True
            
        return chart_info
    
    def enhance_rosenberg_content(self, result: Dict, elements: List[Dict]) -> Dict:
        """Special enhancements for Rosenberg Research documents"""
        for section in ['Key Takeaways', 'Investment Strategy', 'Market Outlook']:
            if section in result['content_text']:
                result[f'highlighted_{section.lower().replace(" ", "_")}'] = True
        return result
    
    def enhance_goldman_content(self, result: Dict, elements: List[Dict]) -> Dict:
        """Special enhancements for Goldman Sachs documents"""
        if 'Trade Recommendations' in result['content_text'] or 'Top Trades' in result['content_text']:
            result['has_trade_recommendations'] = True
        return result
    
    def fallback_extraction(self, pdf_path: str) -> Dict[str, Any]:
        """Fallback to PyMuPDF if API fails"""
        logger.warning("⚠️ Falling back to PyMuPDF extraction")
        try:
            from drive_research_handler import extract_pdf_content_vlm
            return extract_pdf_content_vlm(pdf_path)
        except:
            return {
                'content_text': 'Error extracting PDF',
                'content_html': '<p>Error extracting PDF</p>',
                'charts': [],
                'tables': []
            }

def process_pdf_with_unstructured(pdf_path: str, sender_tag: str = 'default') -> Dict:
    """Main entry point for processing PDFs with Unstructured API"""
    handler = UnstructuredPDFHandler()
    return handler.process_pdf(pdf_path, sender_tag)
