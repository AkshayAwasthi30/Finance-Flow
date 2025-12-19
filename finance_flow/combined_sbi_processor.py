# Combined SBI Statement Processor - JSON Output Version

# Requirements: pip install PyPDF2 pdfplumber pandas matplotlib seaborn

import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import getpass
import os
from PyPDF2 import PdfReader, PdfWriter
import io
from datetime import datetime
import re
import pdfplumber
import pandas as pd
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import json

class CombinedSBIProcessor:
    def __init__(self):
        self.df = None
        self.all_statements_df = None
        self.categories = {
            "Food & Dining": ['swiggy', 'zomato', 'restaurant', 'paytm.d', 'paytm', 'food', 'cafe', 'hotel', 'dining', 'dominos', 'pizza', 'kfc', 'mcdonalds'],
            "Shopping": ['amazon', 'flipkart', 'meesho', 'myntra', 'mayuri a', 'shopping', 'mall', 'store', 'retail', 'purchase', 'buy'],
            "Transport": ['uber', 'ola', 'cab', 'irctc', 'taxi', 'metro', 'bus', 'petrol', 'fuel', 'travel', 'booking', 'flight'],
            "Income": ['salary', 'credit', 'payme', 'decentro', 'refund', 'interest', 'dividend', 'bonus', 'cashback'],
            "Education": ['vit', 'club', 'school', 'college', 'university', 'fees', 'tuition', 'course', 'training'],
            "Cash Withdrawal": ['atm', 'withdrawal', 'cash', 'pos'],
            "Utilities": ['electricity', 'water', 'gas', 'mobile', 'internet', 'broadband', 'recharge', 'bill'],
            "Healthcare": ['hospital', 'medical', 'pharmacy', 'doctor', 'clinic', 'medicine', 'health'],
            "Entertainment": ['movie', 'netflix', 'spotify', 'gaming', 'theatre', 'subscription', 'entertainment'],
            "Investment": ['mutual fund', 'sip', 'fd', 'insurance', 'policy', 'investment', 'equity'],
            "Transfer": ['neft', 'imps', 'rtgs', 'upi', 'transfer', 'payment']
        }

    # ==================== GMAIL EXTRACTION METHODS ====================
    def get_gmail_credentials(self):
        """Get Gmail credentials directly from user"""
        print("🔐 Gmail Login")
        print("=" * 40)
        email_address = input("📧 Enter your Gmail address: ").strip()
        print("\n🔑 Password Options:")
        print("1. Regular Gmail password (if 2FA is disabled)")
        print("2. App Password (if 2FA is enabled)")
        print("\nNote: If you have 2-Factor Authentication enabled, you'll need an App Password")
        password = getpass.getpass("Enter your Gmail password: ").strip()
        return email_address, password

    def connect_to_mailbox(self):
        """Connect to Gmail using IMAP"""
        IMAP_SERVER = 'imap.gmail.com'
        EMAIL, PASSWORD = self.get_gmail_credentials()
        
        try:
            print("\n⌛ Connecting to IMAP server...")
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            print("🔐 Attempting login...")
            mail.login(EMAIL, PASSWORD)
            print("✅ Login successful!")
            return mail
        except imaplib.IMAP4.error as e:
            print(f"❌ Login failed: {e}")
            print("\nTroubleshooting tips:")
            print("1. If you have 2-Factor Authentication enabled, use an App Password")
            print("2. If you don't have 2FA, you may need to enable 'Less secure app access'")
            print("3. Make sure IMAP is enabled in Gmail settings")
            print("4. Check your email address and password")
            return None

    def get_date_range(self):
        """Get date range from user for filtering emails"""
        print("\n📅 Date Range Selection")
        print("=" * 40)
        print("Enter the date range for emails you want to process")
        print("Format: DD/MM/YYYY or DD-MM-YYYY")
        print("Examples: 01/01/2024, 15-06-2024")
        
        while True:
            try:
                from_date_str = input("\n📅 From date (DD/MM/YYYY): ").strip()
                to_date_str = input("📅 To date (DD/MM/YYYY): ").strip()
                
                # Parse dates with multiple formats
                for date_format in ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y']:
                    try:
                        from_date = datetime.strptime(from_date_str, date_format).date()
                        to_date = datetime.strptime(to_date_str, date_format).date()
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError("Invalid date format")
                
                if from_date > to_date:
                    print("❌ From date cannot be later than To date. Please try again.")
                    continue
                
                print(f"✅ Date range: {from_date.strftime('%d/%m/%Y')} to {to_date.strftime('%d/%m/%Y')}")
                return from_date, to_date
                
            except ValueError:
                print("❌ Invalid date format. Please use DD/MM/YYYY format (e.g., 15/06/2024)")
            except KeyboardInterrupt:
                print("\n⚠️ Operation cancelled by user")
                return None, None

    def find_target_emails(self, mail, from_date, to_date):
        """Find all target emails within the specified date range"""
        try:
            print(f"\n🔍 Searching for emails from {from_date.strftime('%d/%m/%Y')} to {to_date.strftime('%d/%m/%Y')}...")
            
            # Search for emails from specific sender with specific subject
            status, messages = mail.search(None, 
                                         '(FROM "bhavyadivya.gupta156@gmail.com" '
                                         'SUBJECT "Fwd: E-account statement for your SBI account(s).")')
            
            if status != 'OK':
                print("No matching emails found")
                return []
                
            email_ids = messages[0].split()
            if not email_ids:
                print("No matching emails found")
                return []
                
            print(f"📧 Found {len(email_ids)} total matching email(s)")
            print("📅 Filtering by date range...")
            
            filtered_emails = []
            for email_id in email_ids:
                try:
                    _, msg_data = mail.fetch(email_id, '(RFC822)')
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # Extract email date
                    if 'Date' in msg:
                        email_date = parsedate_to_datetime(msg['Date'])
                        email_date_only = email_date.date()
                        
                        # Check if email is within date range
                        if from_date <= email_date_only <= to_date:
                            filtered_emails.append((msg, email_date, email_id.decode()))
                            print(f"  ✅ {email_date.strftime('%d/%m/%Y %H:%M')} - Email included")
                        else:
                            print(f"  ⏭️ {email_date.strftime('%d/%m/%Y %H:%M')} - Outside date range")
                    else:
                        print(f"  ⚠️ Email {email_id.decode()} - No date found, skipping")
                        
                except Exception as e:
                    print(f"  ❌ Error processing email {email_id.decode()}: {e}")
                    continue
            
            # Sort by date (oldest first)
            filtered_emails.sort(key=lambda x: x[1])
            print(f"\n📊 Found {len(filtered_emails)} email(s) in the specified date range")
            return filtered_emails
            
        except Exception as e:
            print(f"❌ Error searching emails: {e}")
            return []

    def extract_pdf_attachment(self, msg):
        """Extract PDF attachment from email message"""
        try:
            for part in msg.walk():
                if part.get_content_type() == 'application/pdf':
                    filename = part.get_filename()
                    if filename:
                        return filename, part.get_payload(decode=True)
            return None, None
        except Exception as e:
            print(f"❌ Error extracting attachment: {e}")
            return None, None

    def get_pdf_password(self):
        """Get PDF password once for all PDFs"""
        print("\n🔐 PDF Password Information:")
        print("=" * 50)
        print("Password format: Last 5 digits of mobile number + Date of birth")
        print("Example: If mobile ends with 67890 and DOB is 15/03/1990")
        print("Password should be: 67890150390")
        print("Format: xxxxxDDMMYY (where xxxxx = last 5 digits of mobile)")
        print("=" * 50)
        print("Note: This password will be used for all PDFs in the selected date range")
        return getpass.getpass("Enter password for PDF decryption: ")

    def decrypt_multiple_pdfs(self, emails_with_pdfs, pdf_password):
        """Decrypt multiple PDFs using the same password"""
        successful_decryptions = 0
        failed_decryptions = 0
        
        print(f"\n🔓 Starting decryption of {len(emails_with_pdfs)} PDF(s)...")
        print("=" * 60)
        
        for i, (msg, email_date, email_id, filename, pdf_data) in enumerate(emails_with_pdfs, 1):
            try:
                print(f"\n📄 Processing PDF {i}/{len(emails_with_pdfs)}: {filename}")
                print(f"📅 Email date: {email_date.strftime('%d/%m/%Y %H:%M:%S')}")
                
                pdf_reader = PdfReader(io.BytesIO(pdf_data))
                
                if pdf_reader.is_encrypted:
                    if not pdf_reader.decrypt(pdf_password):
                        print(f"❌ Failed to decrypt {filename} - Incorrect password")
                        failed_decryptions += 1
                        continue
                
                pdf_writer = PdfWriter()
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
                
                # Create filename with email date
                date_str = email_date.strftime("%Y-%m-%d")
                time_str = email_date.strftime("%H%M")
                output_filename = f"SBI_Statement_{date_str}_{time_str}.pdf"
                
                # Ensure unique filename if file already exists
                counter = 1
                base_filename = output_filename
                while os.path.exists(output_filename):
                    name, ext = os.path.splitext(base_filename)
                    output_filename = f"{name}_v{counter}{ext}"
                    counter += 1
                
                with open(output_filename, "wb") as output_file:
                    pdf_writer.write(output_file)
                
                print(f"✅ Successfully saved as: {output_filename}")
                successful_decryptions += 1
                
            except Exception as e:
                print(f"❌ Error processing {filename}: {e}")
                failed_decryptions += 1
        
        print("\n" + "=" * 60)
        print("📊 GMAIL EXTRACTION SUMMARY:")
        print(f"✅ Successfully decrypted: {successful_decryptions} PDF(s)")
        print(f"❌ Failed to decrypt: {failed_decryptions} PDF(s)")
        print(f"📁 Files saved in: {os.path.abspath('.')}")
        
        return successful_decryptions, failed_decryptions

    def process_gmail_extraction(self):
        """Main method for Gmail extraction"""
        print("\n" + "=" * 70)
        print("🌟 STEP 1: GMAIL EXTRACTION")
        print("=" * 70)
        
        mail = self.connect_to_mailbox()
        if not mail:
            return 0
        
        try:
            mail.select('inbox')
            
            # Get date range from user
            from_date, to_date = self.get_date_range()
            if not from_date or not to_date:
                return 0
            
            # Find all emails in date range
            filtered_emails = self.find_target_emails(mail, from_date, to_date)
            if not filtered_emails:
                print("❌ No emails found in the specified date range")
                return 0
            
            # Extract PDF attachments from all emails
            print(f"\n📎 Extracting PDF attachments from {len(filtered_emails)} email(s)...")
            emails_with_pdfs = []
            for msg, email_date, email_id in filtered_emails:
                filename, pdf_data = self.extract_pdf_attachment(msg)
                if filename and pdf_data:
                    emails_with_pdfs.append((msg, email_date, email_id, filename, pdf_data))
                    print(f"  ✅ {email_date.strftime('%d/%m/%Y')} - PDF found: {filename}")
                else:
                    print(f"  ⚠️ {email_date.strftime('%d/%m/%Y')} - No PDF attachment found")
            
            if not emails_with_pdfs:
                print("❌ No PDF attachments found in any of the emails")
                return 0
            
            print(f"\n📊 Found {len(emails_with_pdfs)} email(s) with PDF attachments")
            
            # Get password once for all PDFs
            pdf_password = self.get_pdf_password()
            if not pdf_password:
                print("❌ No password provided")
                return 0
            
            # Decrypt all PDFs
            successful, failed = self.decrypt_multiple_pdfs(emails_with_pdfs, pdf_password)
            return successful
            
        finally:
            print("\n🔒 Closing Gmail connection...")
            try:
                mail.close()
                mail.logout()
            except:
                pass

    # ==================== PDF ANALYSIS METHODS ====================
    def find_sbi_statement_files(self):
        """Find all SBI statement PDF files in the current directory"""
        # Look for files starting with "SBI_Statement"
        pattern = "SBI_Statement*.pdf"
        files = glob.glob(pattern)
        
        if not files:
            # Also check for files that might have been manually placed starting with "decrypted"
            pattern2 = "decrypted*.pdf"
            files = glob.glob(pattern2)
        
        if files:
            files.sort()  # Sort files for consistent processing
            print(f"\n📂 Found {len(files)} SBI statement PDF file(s):")
            for i, file in enumerate(files, 1):
                print(f"  {i}. {file}")
        else:
            print("\n⚠️ No SBI statement PDF files found in current directory.")
            print("Looking for files matching patterns:")
            print("  - SBI_Statement*.pdf")
            print("  - decrypted*.pdf")
        
        return files

    def extract_lines_from_pdf(self, pdf_file):
        """Extract text lines from PDF"""
        lines = []
        try:
            with pdfplumber.open(pdf_file) as pdf:
                print(f"📄 Processing {len(pdf.pages)} pages from {pdf_file}...")
                for page_num, page in enumerate(pdf.pages, 1):
                    txt = page.extract_text() or ""
                    for ln in txt.splitlines():
                        lines.append(ln.rstrip())
            return lines
        except Exception as e:
            print(f"❌ Error reading PDF {pdf_file}: {str(e)}")
            return []

    def normalize_lines(self, lines):
        """Normalize and merge split transaction lines"""
        date_re = re.compile(r'^\d{2}-\d{2}-\d{2}')
        normalized = []
        i = 0
        n = len(lines)
        
        while i < n:
            ln = lines[i].strip()
            if not ln:
                i += 1
                continue
            
            if date_re.match(ln):
                if re.search(r'\d+\.\d{2}\s*$', ln):
                    normalized.append(ln)
                    i += 1
                else:
                    merged = ln
                    j = i + 1
                    while j < n and not re.search(r'\d+\.\d{2}\s*$', merged):
                        merged += ' ' + lines[j].strip()
                        j += 1
                    normalized.append(merged)
                    i = j
            else:
                desc_parts = [ln]
                j = i + 1
                while j < n and not date_re.match(lines[j].strip()):
                    desc_parts.append(lines[j].strip())
                    j += 1
                
                if j < n and date_re.match(lines[j].strip()):
                    date_line = lines[j].strip()
                    m = re.match(r'^(\d{2}-\d{2}-\d{2})(.*)$', date_line)
                    if m:
                        date_part = m.group(1)
                        rest = m.group(2).strip()
                        description = ' '.join(desc_parts).strip()
                        combined = f"{date_part} {description} {rest}".strip()
                        normalized.append(combined)
                        i = j + 1
                    else:
                        i = j + 1
                else:
                    i = j
        
        return normalized

    def parse_normalized(self, normalized_lines):
        """Parse normalized lines into structured data"""
        rows = []
        
        for ln in normalized_lines:
            if not re.search(r'\d+\.\d{2}\s*$', ln):
                continue
            
            toks = ln.split()
            if len(toks) < 5:
                continue
            
            date_tok = toks[0]
            ref_tok = toks[-4] if len(toks) >= 5 else '-'
            credit_tok = toks[-3] if len(toks) >= 4 else '-'
            debit_tok = toks[-2] if len(toks) >= 3 else '-'
            balance_tok = toks[-1]
            
            desc_tokens = toks[1:len(toks)-4] if len(toks) > 4 else toks[1:-3]
            description = ' '.join(desc_tokens).strip()
            
            # Skip header/footer lines
            low = description.lower()
            skip_phrases = ['visit', 'customer care', 'welcome', 'transaction details',
                           'your opening balance', 'closing balance', 'transaction overview',
                           'branch', 'statement period', 'account number', 'page no']
            if any(x in low for x in skip_phrases):
                continue
            
            # Parse date
            try:
                parsed_date = pd.to_datetime(date_tok, dayfirst=True, errors='coerce')
                if pd.isna(parsed_date):
                    continue
                date_str = parsed_date.strftime("%Y-%m-%d")
            except:
                continue
            
            # Parse amounts
            def to_float(x):
                if not x or x.strip() == '-' or x.strip() == '':
                    return 0.0
                try:
                    return float(x.replace(',', ''))
                except:
                    cleaned = re.sub(r'[^\d.]', '', x)
                    return float(cleaned) if cleaned else 0.0
            
            credit = to_float(credit_tok)
            debit = to_float(debit_tok)
            balance = to_float(balance_tok)
            
            txn_type = 'Credit' if credit > 0 else 'Debit'
            amount = credit if credit > 0 else debit
            
            rows.append({
                "Date": date_str,
                "Description": description,
                "RefNo": ref_tok,
                "Credit": credit,
                "Debit": debit,
                "Balance": balance,
                "Type": txn_type,
                "Amount": amount
            })
        
        return pd.DataFrame(rows)

    def categorize_transaction(self, description):
        """Categorize transaction based on description"""
        d = description.lower()
        for category, keywords in self.categories.items():
            if any(keyword in d for keyword in keywords):
                return category
        return "Other"

    def process_dataframe(self, df, source_file):
        """Process and clean the dataframe"""
        if df.empty:
            return df
        
        # Add categories and source file
        df['Category'] = df['Description'].apply(self.categorize_transaction)
        df['Source_File'] = source_file
        
        # Sort by date
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').reset_index(drop=True)
        df['Date'] = df['Date'].dt.strftime("%Y-%m-%d")
        
        # Add month and year columns for analysis
        df['Month'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m')
        df['Year'] = pd.to_datetime(df['Date']).dt.year
        
        return df

    def process_single_pdf(self, pdf_file):
        """Process a single PDF file"""
        print(f"\n🔎 Processing: {pdf_file}")
        print("-" * 50)
        
        # Extract and process
        lines = self.extract_lines_from_pdf(pdf_file)
        if not lines:
            print(f"⚠️ No text extracted from {pdf_file}")
            return pd.DataFrame()
        
        print(f"➡️ Extracted {len(lines)} raw lines")
        
        normalized = self.normalize_lines(lines)
        print(f"➡️ Normalized to {len(normalized)} candidate lines")
        
        df = self.parse_normalized(normalized)
        if df.empty:
            print(f"⚠️ No transactions parsed from {pdf_file}")
            return df
        
        df = self.process_dataframe(df, pdf_file)
        print(f"✅ Parsed {len(df)} transactions from {pdf_file}")
        
        return df

    def process_all_pdfs(self):
        """Process all SBI statement PDFs in the directory - FIXED VERSION"""
        print("\n" + "=" * 70)
        print("🌟 STEP 2: PDF ANALYSIS")
        print("=" * 70)
        
        pdf_files = self.find_sbi_statement_files()
        if not pdf_files:
            # CRITICAL FIX: Return empty DataFrame instead of None
            print("❌ No PDF files found to process")
            return pd.DataFrame()  # This prevents the Flask crash!
        
        all_dataframes = []
        for pdf_file in pdf_files:
            try:
                df = self.process_single_pdf(pdf_file)
                if not df.empty:
                    all_dataframes.append(df)
            except Exception as e:
                print(f"❌ Error processing {pdf_file}: {e}")
                continue
        
        if not all_dataframes:
            print("\n❌ No transactions were successfully parsed from any PDF files")
            # CRITICAL FIX: Return empty DataFrame instead of None
            return pd.DataFrame()  # This prevents the Flask crash!
        
        # Combine all dataframes
        try:
            combined_df = pd.concat(all_dataframes, ignore_index=True)
        except Exception as e:
            print(f"❌ Error combining dataframes: {e}")
            return pd.DataFrame()
        
        # Sort by date
        combined_df['Date'] = pd.to_datetime(combined_df['Date'])
        combined_df = combined_df.sort_values('Date').reset_index(drop=True)
        combined_df['Date'] = combined_df['Date'].dt.strftime("%Y-%m-%d")
        
        # Update month and year after combining
        combined_df['Month'] = pd.to_datetime(combined_df['Date']).dt.strftime('%Y-%m')
        combined_df['Year'] = pd.to_datetime(combined_df['Date']).dt.year
        
        self.all_statements_df = combined_df
        
        print("\n" + "=" * 70)
        print("📊 COMBINED ANALYSIS SUMMARY")
        print("=" * 70)
        print(f"✅ Successfully processed {len(pdf_files)} PDF file(s)")
        print(f"📈 Total transactions parsed: {len(combined_df)}")
        print(f"📅 Date range: {combined_df['Date'].min()} to {combined_df['Date'].max()}")
        print(f"💰 Total credits: ₹{combined_df['Credit'].sum():,.2f}")
        print(f"💸 Total debits: ₹{combined_df['Debit'].sum():,.2f}")
        print(f"📊 Net flow: ₹{(combined_df['Credit'].sum() - combined_df['Debit'].sum()):,.2f}")
        
        return combined_df

    def save_results(self, df, filename_prefix="combined_sbi_transactions"):
        """Save results to JSON file"""
        if df is None or df.empty:
            print("⚠️ No data to save")
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Convert DataFrame to JSON-compatible format
        # Handle datetime and numeric types properly
        df_json = df.copy()
        
        # Convert any datetime columns to strings
        for col in df_json.columns:
            if df_json[col].dtype == 'datetime64[ns]':
                df_json[col] = df_json[col].dt.strftime('%Y-%m-%d')
        
        # Create comprehensive JSON structure
        json_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_transactions": len(df_json),
                "date_range": {
                    "start_date": df_json['Date'].min(),
                    "end_date": df_json['Date'].max()
                },
                "financial_summary": {
                    "total_credits": float(df_json['Credit'].sum()),
                    "total_debits": float(df_json['Debit'].sum()),
                    "net_flow": float(df_json['Credit'].sum() - df_json['Debit'].sum())
                },
                "files_processed": df_json['Source_File'].unique().tolist() if 'Source_File' in df_json.columns else [],
                "categories": df_json['Category'].value_counts().to_dict() if 'Category' in df_json.columns else {}
            },
            "transactions": df_json.to_dict('records')
        }
        
        # Save to JSON file with proper formatting
        json_filename = f"{filename_prefix}_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n✅ Saved {len(df_json)} transactions to: {json_filename}")
        print(f"📊 JSON structure includes:")
        print(f"  • Metadata with summary statistics")
        print(f"  • Complete transaction records")
        print(f"  • File processing information")
        print(f"  • Category breakdown")
        
        return json_filename

    def print_detailed_summary(self, df):
        """Print detailed transaction summary"""
        if df is None or df.empty:
            print("⚠️ No transactions to summarize.")
            return
        
        print("\n" + "=" * 80)
        print("📊 DETAILED TRANSACTION ANALYSIS")
        print("=" * 80)
        
        # Basic stats
        total_credits = df['Credit'].sum()
        total_debits = df['Debit'].sum()
        net_flow = total_credits - total_debits
        
        print(f"Total Credits: ₹{total_credits:>15,.2f}")
        print(f"Total Debits: ₹{total_debits:>15,.2f}")
        print(f"Net Flow: ₹{net_flow:>15,.2f}")
        print(f"Transaction Count: {len(df):>11}")
        
        # Date range
        start_date = df['Date'].min()
        end_date = df['Date'].max()
        print(f"Period: {start_date} to {end_date}")
        
        # File breakdown
        print(f"\n📁 TRANSACTIONS BY FILE:")
        print("-" * 50)
        file_summary = df.groupby('Source_File').agg({
            'Amount': 'count',
            'Credit': 'sum',
            'Debit': 'sum'
        }).round(2)
        file_summary.columns = ['Count', 'Total_Credits', 'Total_Debits']
        file_summary['Net_Flow'] = file_summary['Total_Credits'] - file_summary['Total_Debits']
        
        for file, row in file_summary.iterrows():
            print(f"{file}")
            print(f"  Transactions: {int(row['Count'])}")
            print(f"  Credits: ₹{row['Total_Credits']:,.2f}")
            print(f"  Debits: ₹{row['Total_Debits']:,.2f}")
            print(f"  Net: ₹{row['Net_Flow']:,.2f}")
            print()
        
        # Monthly breakdown
        print(f"📈 MONTHLY BREAKDOWN:")
        print("-" * 60)
        monthly_summary = df.groupby('Month').agg({
            'Amount': 'count',
            'Credit': 'sum',
            'Debit': 'sum'
        }).round(2)
        monthly_summary.columns = ['Count', 'Credits', 'Debits']
        monthly_summary['Net'] = monthly_summary['Credits'] - monthly_summary['Debits']
        
        for month, row in monthly_summary.iterrows():
            print(f"{month}: {int(row['Count'])} txns | Credits: ₹{row['Credits']:>10,.2f} | Debits: ₹{row['Debits']:>10,.2f} | Net: ₹{row['Net']:>10,.2f}")
        
        # Category breakdown
        print(f"\n📊 SPENDING BY CATEGORY:")
        print("-" * 60)
        category_summary = df[df['Type'] == 'Debit'].groupby('Category')['Amount'].agg(['count', 'sum']).round(2)
        category_summary.columns = ['Count', 'Total_Amount']
        category_summary = category_summary.sort_values('Total_Amount', ascending=False)
        
        for category, row in category_summary.iterrows():
            percentage = (row['Total_Amount'] / total_debits) * 100 if total_debits > 0 else 0
            print(f"{category:<20} {int(row['Count']):>4} txns | ₹{row['Total_Amount']:>12,.2f} ({percentage:>5.1f}%)")
        
        # Recent transactions
        print(f"\n🔍 RECENT TRANSACTIONS (Last 15):")
        print("-" * 100)
        recent = df.tail(15)[['Date', 'Description', 'Type', 'Amount', 'Category', 'Source_File']]
        for _, row in recent.iterrows():
            print(f"{row['Date']} | {row['Type']:<6} | ₹{row['Amount']:>10,.2f} | {row['Description'][:35]:<35} | {row['Category']:<15} | {row['Source_File']}")

    def create_comprehensive_visualizations(self, df):
        """Create comprehensive visualization charts"""
        if df is None or df.empty:
            print("⚠️ No data to visualize.")
            return
        
        print("\n📈 Creating comprehensive visualizations...")
        
        # Set up the plotting style
        plt.style.use('default')
        fig, axes = plt.subplots(3, 2, figsize=(20, 18))
        fig.suptitle('Comprehensive SBI Statement Analysis', fontsize=20, fontweight='bold')
        
        # 1. Monthly spending and income trend
        monthly_data = df.groupby(['Month', 'Type'])['Amount'].sum().unstack(fill_value=0)
        if len(monthly_data) > 1:
            if 'Debit' in monthly_data.columns:
                axes[0, 0].plot(monthly_data.index, monthly_data['Debit'], marker='o', linewidth=3,
                              markersize=8, color='red', label='Expenses')
            if 'Credit' in monthly_data.columns:
                axes[0, 0].plot(monthly_data.index, monthly_data['Credit'], marker='s', linewidth=3,
                              markersize=8, color='green', label='Income')
            axes[0, 0].set_title('Monthly Income vs Expenses Trend', fontsize=14, fontweight='bold')
            axes[0, 0].set_xlabel('Month')
            axes[0, 0].set_ylabel('Amount (₹)')
            axes[0, 0].legend()
            axes[0, 0].tick_params(axis='x', rotation=45)
            axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Category wise spending (pie chart)
        category_spending = df[df['Type'] == 'Debit'].groupby('Category')['Amount'].sum()
        if not category_spending.empty:
            # Show only top 8 categories, combine rest as 'Others'
            top_categories = category_spending.nlargest(8)
            if len(category_spending) > 8:
                others_sum = category_spending[~category_spending.index.isin(top_categories.index)].sum()
                if others_sum > 0:
                    top_categories['Others'] = others_sum
            colors = plt.cm.Set3(range(len(top_categories)))
            axes[0, 1].pie(top_categories.values, labels=top_categories.index, autopct='%1.1f%%',
                          startangle=90, colors=colors)
            axes[0, 1].set_title('Spending Distribution by Category', fontsize=14, fontweight='bold')
        
        # 3. Daily balance trend
        daily_balance = df.groupby('Date')['Balance'].last().sort_index()
        if len(daily_balance) > 1:
            axes[1, 0].plot(pd.to_datetime(daily_balance.index), daily_balance.values,
                          color='blue', linewidth=2, alpha=0.8)
            axes[1, 0].set_title('Account Balance Trend', fontsize=14, fontweight='bold')
            axes[1, 0].set_xlabel('Date')
            axes[1, 0].set_ylabel('Balance (₹)')
            axes[1, 0].tick_params(axis='x', rotation=45)
            axes[1, 0].grid(True, alpha=0.3)
            # Format y-axis to show currency
            axes[1, 0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x:,.0f}'))
        
        # 4. Top spending categories (horizontal bar chart)
        if not category_spending.empty:
            top_10_categories = category_spending.nlargest(10)
            bars = axes[1, 1].barh(range(len(top_10_categories)), top_10_categories.values,
                                 color=plt.cm.viridis(range(len(top_10_categories))))
            axes[1, 1].set_title('Top 10 Spending Categories', fontsize=14, fontweight='bold')
            axes[1, 1].set_xlabel('Amount (₹)')
            axes[1, 1].set_yticks(range(len(top_10_categories)))
            axes[1, 1].set_yticklabels(top_10_categories.index)
            axes[1, 1].xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x:,.0f}'))
            
            # Add value labels on bars
            for i, (bar, value) in enumerate(zip(bars, top_10_categories.values)):
                axes[1, 1].text(bar.get_width() + value*0.01, bar.get_y() + bar.get_height()/2,
                               f'₹{value:,.0f}', ha='left', va='center', fontsize=9)
        
        # 5. Transaction volume by day of week
        df_temp = df.copy()
        df_temp['DayOfWeek'] = pd.to_datetime(df_temp['Date']).dt.day_name()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_volume = df_temp.groupby('DayOfWeek')['Amount'].count()
        daily_volume = daily_volume.reindex(day_order, fill_value=0)
        
        bars = axes[2, 0].bar(daily_volume.index, daily_volume.values, color='skyblue', alpha=0.8)
        axes[2, 0].set_title('Transaction Volume by Day of Week', fontsize=14, fontweight='bold')
        axes[2, 0].set_xlabel('Day of Week')
        axes[2, 0].set_ylabel('Number of Transactions')
        axes[2, 0].tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar, value in zip(bars, daily_volume.values):
            axes[2, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                           str(int(value)), ha='center', va='bottom', fontsize=10)
        
        # 6. Income vs Expense comparison by month
        monthly_comparison = df.groupby(['Month', 'Type'])['Amount'].sum().unstack(fill_value=0)
        if not monthly_comparison.empty and len(monthly_comparison.columns) > 1:
            x = range(len(monthly_comparison.index))
            width = 0.35
            
            if 'Credit' in monthly_comparison.columns:
                axes[2, 1].bar([i - width/2 for i in x], monthly_comparison['Credit'],
                             width, label='Income', color='green', alpha=0.8)
            if 'Debit' in monthly_comparison.columns:
                axes[2, 1].bar([i + width/2 for i in x], monthly_comparison['Debit'],
                             width, label='Expenses', color='red', alpha=0.8)
            
            axes[2, 1].set_title('Monthly Income vs Expenses Comparison', fontsize=14, fontweight='bold')
            axes[2, 1].set_xlabel('Month')
            axes[2, 1].set_ylabel('Amount (₹)')
            axes[2, 1].set_xticks(x)
            axes[2, 1].set_xticklabels(monthly_comparison.index, rotation=45)
            axes[2, 1].legend()
            axes[2, 1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x:,.0f}'))
        
        plt.tight_layout()
        
        # Save the plot
        plot_filename = f"comprehensive_sbi_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(plot_filename, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✅ Comprehensive charts saved to: {plot_filename}")
        
        try:
            plt.show()
        except:
            print("📈 Charts created successfully (display not available in current environment)")

    def run_complete_analysis(self):
        """Main method to run the complete analysis"""
        print("=" * 80)
        print("🏦 COMBINED SBI STATEMENT PROCESSOR - JSON VERSION")
        print("=" * 80)
        print("This tool will:")
        print("1. 📧 Extract SBI statements from Gmail (optional)")
        print("2. 📄 Process all PDF statements in current directory")
        print("3. 📊 Generate comprehensive analysis and visualizations")
        print("4. 💾 Export data in JSON format")
        print("=" * 80)
        
        try:
            # Ask user if they want to extract from Gmail first
            extract_choice = input("\n❓ Do you want to extract new statements from Gmail? (y/n): ").strip().lower()
            if extract_choice in ['y', 'yes']:
                extracted_count = self.process_gmail_extraction()
                if extracted_count > 0:
                    print(f"\n✅ Successfully extracted {extracted_count} new PDF(s) from Gmail")
                else:
                    print("\n⚠️ No new PDFs were extracted from Gmail")
            else:
                print("\n⏭️ Skipping Gmail extraction. Processing existing PDFs...")
            
            # Process all PDFs in directory
            combined_df = self.process_all_pdfs()
            if combined_df is None or combined_df.empty:
                print("\n❌ No transaction data to analyze. Exiting...")
                return
            
            # Save combined results in JSON format
            json_filename = self.save_results(combined_df)
            
            # Print detailed summary
            self.print_detailed_summary(combined_df)
            
            # Create comprehensive visualizations
            try:
                self.create_comprehensive_visualizations(combined_df)
            except Exception as e:
                print(f"⚠️ Could not create visualizations: {str(e)}")
            
            print("\n" + "=" * 80)
            print("🎉 ANALYSIS COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print("📁 Generated files:")
            if json_filename:
                print(f"  • {json_filename} (transaction data in JSON format)")
            print(f"  • comprehensive_sbi_analysis_*.png (charts)")
            
            print("\n💡 You can now:")
            print("  • Review the detailed analysis above")
            print("  • Open the JSON file for structured data access")
            print("  • View the generated charts for visual insights")
            print("  • Access the data programmatically using processor.all_statements_df")
            
            print("\n🔧 JSON Format Benefits:")
            print("  • Structured metadata with summary statistics")
            print("  • Easy integration with web applications")
            print("  • Better data type preservation")
            print("  • Nested data organization")
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Process interrupted by user")
        except Exception as e:
            print(f"\n❌ Unexpected error during analysis: {e}")
            import traceback
            print("Full error details:")
            traceback.print_exc()

def main():
    """Main function for easy execution"""
    processor = CombinedSBIProcessor()
    processor.run_complete_analysis()

if __name__ == "__main__":
    main()
