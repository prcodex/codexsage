from flask import Flask, render_template, jsonify, request
import json
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('admin_complete.html')

@app.route('/api/allowed_senders')
def get_allowed_senders():
    """Get list of allowed senders (tags only)"""
    try:
        with open('allowed_senders.json', 'r') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            senders = list(set([item.get('sender_tag', '') for item in data if item.get('sender_tag')]))
            senders.sort()
        else:
            senders = data.get('senders', [])
        
        return jsonify({'senders': senders})
    except Exception as e:
        print(f"Error loading allowed senders: {e}")
        return jsonify({'senders': []}), 500

@app.route('/api/allowed_senders_full')
def get_allowed_senders_full():
    """Get full allowlist data with email patterns"""
    try:
        with open('allowed_senders.json', 'r') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return jsonify({'senders': data})
        else:
            return jsonify({'senders': data.get('senders', [])})
    except Exception as e:
        print(f"Error loading full allowed senders: {e}")
        return jsonify({'senders': []}), 500

@app.route('/api/update_allowed_sender', methods=['POST'])
def update_allowed_sender():
    """Update or add an allowed sender"""
    try:
        data = request.get_json()
        old_email = data.get('old_email')
        new_entry = {
            'email': data.get('email'),
            'sender_tag': data.get('sender_tag'),
            'description': data.get('description', '')
        }
        
        if not new_entry['email'] or not new_entry['sender_tag']:
            return jsonify({'success': False, 'error': 'Missing email or sender_tag'}), 400
        
        with open('allowed_senders.json', 'r') as f:
            senders = json.load(f)
        
        if isinstance(senders, dict):
            senders = senders.get('senders', [])
        
        if old_email:
            for i, sender in enumerate(senders):
                if sender.get('email') == old_email:
                    senders[i] = new_entry
                    break
        else:
            senders.append(new_entry)
        
        with open('allowed_senders.json', 'w') as f:
            json.dump(senders, f, indent=2)
        
        return jsonify({'success': True, 'entry': new_entry})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete_allowed_sender', methods=['POST'])
def delete_allowed_sender():
    """Delete an allowed sender"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'error': 'Missing email'}), 400
        
        with open('allowed_senders.json', 'r') as f:
            senders = json.load(f)
        
        if isinstance(senders, dict):
            senders = senders.get('senders', [])
        
        senders = [s for s in senders if s.get('email') != email]
        
        with open('allowed_senders.json', 'w') as f:
            json.dump(senders, f, indent=2)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/detection_rules')
def get_detection_rules():
    """Get all detection rules"""
    try:
        with open('tag_detection_rules.json', 'r') as f:
            rules = json.load(f)
        return jsonify(rules)
    except Exception as e:
        print(f"Error loading detection rules: {e}")
        return jsonify({}), 500

@app.route('/api/tag_mappings_data')
def get_tag_mappings_data():
    """Get tag-to-handler mappings"""
    try:
        with open('tag_handler_mappings.json', 'r') as f:
            mappings = json.load(f)
        return jsonify(mappings)
    except Exception as e:
        print(f"Error loading tag mappings: {e}")
        return jsonify({}), 500

@app.route('/api/available_handlers')
def get_available_handlers():
    """Get list of available enrichment handlers"""
    handlers = [
        "newsbrief_with_links",
        "gold_standard_enhanced",
        "rosenberg_deep_research",
        "breakfast_headlines",
        "cochrane_detailed",
        "itau_daily",
        "tony_pasquariello",
        "wsj_opinion",
        "shadow_vlm",
        "charts_vlm",
        "elerian_rep",
        "javier_blas",
        "digest",
        "bloomberg_breaking",
        "classification"
    ]
    return jsonify({'handlers': handlers})

@app.route('/api/update_tag_mapping', methods=['POST'])
def update_tag_mapping():
    """Update a tag's handler mapping"""
    try:
        data = request.get_json()
        tag = data.get('tag')
        new_handler = data.get('handler')
        
        if not tag or not new_handler:
            return jsonify({'success': False, 'error': 'Missing tag or handler'}), 400
        
        with open('tag_handler_mappings.json', 'r') as f:
            mappings = json.load(f)
        
        old_handler = mappings.get(tag, 'UNKNOWN')
        mappings[tag] = new_handler
        
        with open('tag_handler_mappings.json', 'w') as f:
            json.dump(mappings, f, indent=2)
        
        return jsonify({
            'success': True,
            'tag': tag,
            'old_handler': old_handler,
            'new_handler': new_handler
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test_rule', methods=['POST'])
def test_rule():
    """Test a detection rule against actual emails"""
    data = request.get_json()
    
    sender = data.get('sender', '')
    subject_contains = data.get('subject_contains', '')
    body_contains = data.get('body_contains', '')
    logic = data.get('logic', 'OR')
    
    import requests
    
    try:
        response = requests.get('http://localhost:8540/api/feed', timeout=5)
        emails = response.json()
        
        matches = []
        
        for email in emails:
            email_sender = str(email.get('sender', '') or email.get('display_name', '')).lower()
            email_subject = str(email.get('title', '')).lower()
            email_content = str(email.get('content_text', '')).lower()
            
            sender_match = sender.lower() in email_sender if sender else True
            
            if subject_contains and body_contains:
                if logic == 'OR':
                    content_match = (subject_contains.lower() in email_subject or 
                                   body_contains.lower() in email_content)
                else:
                    content_match = (subject_contains.lower() in email_subject and 
                                   body_contains.lower() in email_content)
            elif subject_contains:
                content_match = subject_contains.lower() in email_subject
            elif body_contains:
                content_match = body_contains.lower() in email_content
            else:
                content_match = True
            
            if sender_match and content_match:
                matches.append({
                    'title': email.get('title', ''),
                    'sender': email.get('display_name', email.get('sender', 'Unknown')),
                    'date': email.get('created_at', ''),
                    'current_tag': email.get('sender_tag', 'NO TAG')
                })
            
            if len(matches) >= 5:
                break
        
        return jsonify({
            'success': True,
            'matches': matches[:5],
            'total_checked': len(emails),
            'total_matches': len(matches)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/keyword_exclusions')
def get_keyword_exclusions():
    """Get keyword exclusion list"""
    try:
        with open('keyword_exclusions.json', 'r') as f:
            exclusions = json.load(f)
        return jsonify(exclusions)
    except Exception as e:
        print(f"Error loading exclusions: {e}")
        return jsonify({}), 500

@app.route('/api/keyword_exclusions', methods=['POST'])
def save_keyword_exclusions():
    """Save keyword exclusion list"""
    try:
        data = request.get_json()
        with open('keyword_exclusions.json', 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error saving exclusions: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8543, debug=True)

@app.route('/test')
def test_page():
    return render_template('test_simple.html')
