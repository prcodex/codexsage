#!/usr/bin/env python3
"""
SAGE 4.0 Interface - Fixed
"""

from flask import Flask, render_template, jsonify, request, make_response
import lancedb
import pandas as pd
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URI = "s3://sage-unified-feed-lance/lancedb/"
TABLE_NAME = "unified_feed"

def _format_item(row):
    """Format a database row for JSON response"""
    try:
        if hasattr(row, 'to_dict'):
            item = row.to_dict()
        else:
            item = dict(row)
        
        formatted = {
            'id': str(item.get('id', '')),
            'source_type': str(item.get('source_type', 'email')),
            'created_at': str(item.get('created_at', '')),
            'author': str(item.get('author', '')),
            'author_email': str(item.get('author_email', '')),
            'title': str(item.get('title', '')),
            'content_text': str(item.get('content_text', ''))[:1000],
            'content_html': '',
            'sender_tag': str(item.get('sender_tag', 'unknown')),
            'ai_score': float(item.get('ai_score', 0.0)) if item.get('ai_score') else 0.0,
            'ai_relevance_score': float(item.get('ai_relevance_score', 0.0)) if item.get('ai_relevance_score') else 0.0,
            'enriched_content': str(item.get('enriched_content', '')),
            'actors': str(item.get('actors', '')),
            'themes': str(item.get('themes', ''))
        }
        
        return formatted
    except Exception as e:
        logger.error(f"Error formatting item: {e}")
        return {}

@app.route('/')
def index():
    """Serve the main interface"""
    return render_template('sage_4.0_interface.html')

@app.route('/api/feed')
def get_feed():
    """Get all feed items"""
    try:
        db = lancedb.connect(DB_URI)
        table = db.open_table(TABLE_NAME)
        df = table.to_pandas()
        
        if 'created_at' in df.columns:
            df = df.sort_values('created_at', ascending=False)
        
        items = []
        for _, row in df.iterrows():
            item = _format_item(row)
            if item:
                items.append(item)
        
        response = make_response(jsonify({
            'items': items,
            'total': len(items),
            'timestamp': datetime.now().isoformat()
        }))
        
        # No-cache headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting feed: {e}")
        return jsonify({'error': str(e), 'items': []}), 500


@app.route('/api/email/<email_id>')
def get_email_detail(email_id):
    """Get detailed email content including full HTML"""
    try:
        db = lancedb.connect(DB_URI)
        table = db.open_table(TABLE_NAME)
        df = table.to_pandas()
        
        logger.info(f"Looking for email ID: {email_id}")
        logger.info(f"Available IDs: {df['id'].tolist()[:5]}")
        
        # Find the email - convert both to string for comparison
        email_row = df[df['id'].astype(str) == str(email_id)]
        
        if len(email_row) == 0:
            logger.warning(f"Email {email_id} not found in {len(df)} items")
            return jsonify({'error': f'Email not found: {email_id}'}), 404
        
        row = email_row.iloc[0]
        
        logger.info(f"Found email: {row.get('title', '')[:50]}")
        
        # Return complete email data
        email_data = {
            'id': str(row.get('id', '')),
            'title': str(row.get('title', '')),
            'subject': str(row.get('title', '')),
            'author': str(row.get('author', '')),
            'author_email': str(row.get('author_email', '')),
            'created_at': str(row.get('created_at', '')),
            'content_html': str(row.get('content_html', ''))[:50000],
            'content_text': str(row.get('content_text', ''))[:5000],
            'sender_tag': str(row.get('sender_tag', ''))
        }
        
        logger.info(f"Returning email with HTML length: {len(email_data['content_html'])}")
        
        return jsonify(email_data)
        
    except Exception as e:
        logger.error(f"Error getting email detail: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8540, debug=False)

