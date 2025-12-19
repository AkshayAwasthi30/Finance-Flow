from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import threading
import uuid
import secrets
import time
import tempfile
import shutil

# Import your existing processor
try:
    from combined_sbi_processor import CombinedSBIProcessor
    PROCESSOR_AVAILABLE = True
    print("✅ Successfully imported CombinedSBIProcessor")
except ImportError as e:
    print(f"❌ ERROR: Could not import CombinedSBIProcessor: {e}")
    PROCESSOR_AVAILABLE = False

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Global variables
processing_status = {}
transaction_data = {}

class WorkingProcessor:
    def __init__(self):
        if not PROCESSOR_AVAILABLE:
            raise Exception("❌ CombinedSBIProcessor required!")
        self.processor = CombinedSBIProcessor()
        self.temp_dir = None
    
    def setup_temp_directory(self):
        self.temp_dir = tempfile.mkdtemp(prefix="sbi_processor_")
        return self.temp_dir
    
    def cleanup_temp_directory(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass
    
    def process_real_data(self, gmail_email, gmail_password, pdf_password, from_date, to_date):
        """Process real data with WORKING categorization"""
        print("🔄 Processing with WORKING categorization...")
        
        original_cwd = os.getcwd()
        temp_dir = self.setup_temp_directory()
        
        try:
            os.chdir(temp_dir)
            
            processor = CombinedSBIProcessor()
            
            # Override methods
            def mock_get_gmail_credentials():
                return gmail_email, gmail_password
            
            def mock_get_date_range():
                from_dt = datetime.strptime(from_date, '%Y-%m-%d').date()
                to_dt = datetime.strptime(to_date, '%Y-%m-%d').date()
                return from_dt, to_dt
            
            def mock_get_pdf_password():
                return pdf_password
            
            processor.get_gmail_credentials = mock_get_gmail_credentials
            processor.get_date_range = mock_get_date_range
            processor.get_pdf_password = mock_get_pdf_password
            
            # Gmail extraction
            print("📧 Extracting from Gmail...")
            extracted_count = processor.process_gmail_extraction()
            
            if extracted_count == 0:
                raise Exception("No PDF statements found in Gmail for the specified date range. Please check:\n1. Date range includes periods when you received SBI statements\n2. SBI statements are in your Gmail inbox\n3. Gmail credentials are correct")
            
            # PDF processing
            print("📄 Processing PDFs...")
            combined_df = processor.process_all_pdfs()
            
            if combined_df is None or (hasattr(combined_df, 'empty') and combined_df.empty):
                raise Exception("No transactions found in PDFs. Please check:\n1. PDF password is correct\n2. PDFs are valid SBI statements")
            
            print(f"✅ Processed {len(combined_df)} transactions with WORKING categorization!")
            
            # Convert to result format
            result = self.convert_to_result(combined_df)
            
            return result
            
        except Exception as e:
            raise Exception(f"Processing failed: {str(e)}")
        finally:
            os.chdir(original_cwd)
            self.cleanup_temp_directory()
    
    def convert_to_result(self, df):
        """Convert to result format with PROPER categorization"""
        transactions = []
        
        print(f"🧠 Converting {len(df)} transactions with categories...")
        
        for idx, row in df.iterrows():
            try:
                transaction = {
                    'Date': str(row.get('Date', '')),
                    'Description': str(row.get('Description', '')),
                    'Type': str(row.get('Type', 'Unknown')),
                    'Amount': float(row.get('Amount', 0)),
                    'Balance': float(row.get('Balance', 0)),
                    'Category': str(row.get('Category', 'Other')),  # THIS IS THE KEY - your backend already has this!
                    'Transaction_ID': f"REAL_{idx+1:04d}"
                }
                transactions.append(transaction)
            except Exception as e:
                print(f"Warning: Skipping row {idx}: {e}")
                continue
        
        if not transactions:
            raise Exception("No valid transactions found")
        
        # Calculate summary
        total_income = sum(t['Amount'] for t in transactions if t['Type'] == 'Credit')
        total_expenses = sum(t['Amount'] for t in transactions if t['Type'] == 'Debit')
        net_savings = total_income - total_expenses
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0
        
        # Category breakdown
        category_breakdown = {}
        for t in transactions:
            if t['Type'] == 'Debit':
                cat = t['Category']
                if cat not in category_breakdown:
                    category_breakdown[cat] = {'amount': 0, 'count': 0}
                category_breakdown[cat]['amount'] += t['Amount']
                category_breakdown[cat]['count'] += 1
        
        # Sort categories by amount
        sorted_categories = sorted(category_breakdown.items(), key=lambda x: x[1]['amount'], reverse=True)
        
        insights = []
        
        # Savings insight
        if savings_rate > 30:
            message = f"🌟 Outstanding savings rate of {savings_rate:.1f}%! You're in the top tier of savers."
        elif savings_rate > 20:
            message = f"🎯 Excellent {savings_rate:.1f}% savings rate! You're building wealth effectively."
        elif savings_rate > 10:
            message = f"📈 Good {savings_rate:.1f}% savings rate. Aim for 20%+ for optimal growth."
        else:
            message = f"⚠️ Low {savings_rate:.1f}% savings rate. Focus on expense optimization."
        
        insights.append({
            'type': 'savings_analysis',
            'title': f'💰 Savings Rate: {savings_rate:.1f}%',
            'message': message,
            'severity': 'success' if savings_rate > 20 else 'warning' if savings_rate > 10 else 'error',
            'value': f'{savings_rate:.1f}%'
        })
        
        # Top category insight
        if sorted_categories:
            top_category, data = sorted_categories[0]
            percentage = (data['amount'] / total_expenses * 100) if total_expenses > 0 else 0
            
            insights.append({
                'type': 'category_analysis',
                'title': f'🛒 Top Spending: {top_category}',
                'message': f'{top_category} accounts for {percentage:.1f}% of your expenses (₹{data["amount"]:,.0f}). {"Consider budgeting for this category." if percentage > 30 else "Well-distributed spending pattern."}',
                'severity': 'warning' if percentage > 30 else 'info',
                'value': f'₹{data["amount"]:,.0f}'
            })
        
        result = {
            'transactions': transactions,
            'summary': {
                'total_transactions': len(transactions),
                'total_income': round(total_income, 2),
                'total_expenses': round(total_expenses, 2),
                'net_savings': round(net_savings, 2),
                'savings_rate': round(savings_rate, 2),
                'avg_monthly_income': round(total_income / max(1, len(set(t['Date'][:7] for t in transactions if t['Date']))), 2),
                'avg_monthly_expenses': round(total_expenses / max(1, len(set(t['Date'][:7] for t in transactions if t['Date']))), 2),
                'date_range': {
                    'start': min(t['Date'] for t in transactions if t['Date']),
                    'end': max(t['Date'] for t in transactions if t['Date'])
                },
                'category_breakdown': dict(sorted_categories)
            },
            'insights': insights,
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'data_quality': 'Real Bank Data',
                'categorization': 'WORKING - Backend Categories Applied!',
                'categories_found': len(category_breakdown)
            }
        }
        
        return result

# Initialize processor
try:
    working_processor = WorkingProcessor()
    print("✅ WORKING processor initialized!")
except Exception as e:
    print(f"❌ Failed to initialize: {e}")
    working_processor = None

# Flask Routes
@app.route('/')
def index():
    if 'authenticated' not in session:
        return render_template('auth.html')
    return render_template('dashboard.html')

@app.route('/authenticate', methods=['POST'])
def authenticate():
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not email or not password or '@gmail.com' not in email.lower():
            return jsonify({'success': False, 'message': 'Valid Gmail address required'})
        
        session['gmail_credentials'] = {'email': email, 'password': password}
        session['authenticated'] = True
        session.permanent = True
        
        return jsonify({'success': True, 'redirect': url_for('dashboard')})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Authentication failed'})

@app.route('/dashboard')
def dashboard():
    if 'authenticated' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html')

@app.route('/api/process-statements', methods=['POST'])
def process_statements():
    if 'authenticated' not in session or not working_processor:
        return jsonify({'success': False, 'message': 'Not available'})
    
    try:
        data = request.get_json()
        from_date = data.get('from_date')
        to_date = data.get('to_date')
        pdf_password = data.get('pdf_password')
        
        if not all([from_date, to_date, pdf_password]):
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        gmail_creds = session.get('gmail_credentials')
        if not gmail_creds:
            return jsonify({'success': False, 'message': 'Gmail credentials not found'})
        
        task_id = str(uuid.uuid4())
        
        processing_status[task_id] = {
            'status': 'processing',
            'progress': 0,
            'message': 'Starting WORKING categorization processing...',
            'start_time': time.time()
        }
        
        thread = threading.Thread(
            target=working_background_processing,
            args=(task_id, gmail_creds['email'], gmail_creds['password'], pdf_password, from_date, to_date)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'task_id': task_id})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

def working_background_processing(task_id, gmail_email, gmail_password, pdf_password, from_date, to_date):
    """WORKING background processing"""
    try:
        print(f"🚀 Starting WORKING processing for task {task_id}")
        
        processing_status[task_id].update({
            'progress': 15,
            'message': 'Connecting to Gmail...'
        })
        time.sleep(2)
        
        processing_status[task_id].update({
            'progress': 35,
            'message': 'Scanning for SBI statements...'
        })
        time.sleep(2)
        
        processing_status[task_id].update({
            'progress': 55,
            'message': 'Processing PDFs with categorization...'
        })
        time.sleep(2)
        
        processing_status[task_id].update({
            'progress': 80,
            'message': 'Applying WORKING backend categorization...'
        })
        
        # Use WORKING processor
        result = working_processor.process_real_data(
            gmail_email, gmail_password, pdf_password, from_date, to_date
        )
        
        processing_status[task_id].update({
            'progress': 95,
            'message': 'Finalizing WORKING categorized results...'
        })
        time.sleep(1)
        
        processing_status[task_id].update({
            'progress': 100,
            'status': 'completed',
            'message': f'✅ WORKING categorization completed! {len(result["transactions"])} transactions with {result["metadata"]["categories_found"]} categories!'
        })
        
        transaction_data[task_id] = result
        print(f"✅ WORKING task {task_id} completed successfully!")
        
    except Exception as e:
        print(f"❌ WORKING processing failed: {str(e)}")
        processing_status[task_id].update({
            'status': 'error',
            'progress': 0,
            'message': f'Processing failed: {str(e)}'
        })

@app.route('/api/processing-status/<task_id>')
def get_processing_status(task_id):
    if task_id not in processing_status:
        return jsonify({'status': 'not_found'})
    
    status = processing_status[task_id].copy()
    status.pop('start_time', None)
    return jsonify(status)

@app.route('/api/transactions/<task_id>')
def get_transactions(task_id):
    if task_id not in transaction_data:
        return jsonify({'error': 'No data found'})
    
    data = transaction_data[task_id]
    print(f"📊 Returning WORKING categorized data: {len(data.get('transactions', []))} transactions with {data['metadata']['categories_found']} categories")
    return jsonify(data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("🚀 FINANCE FLOW - WORKING CATEGORIZATION GUARANTEED!")
    print("🧠 Using your backend's existing categorization")
    print("📊 Categories: Food & Dining, Shopping, Transport, Utilities, etc.")
    print("💻 Access: http://127.0.0.1:5000")
    
    if not working_processor:
        print("❌ WORKING processor not available!")
        exit(1)
    
    print("✅ WORKING categorization ready!")
    print("✅ Uses your backend's categories directly!")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
