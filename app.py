from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
import hashlib
import os
from datetime import datetime, timedelta
import json
from models import Database, init_database
from config import Config, allowed_file
from werkzeug.utils import secure_filename
import csv
import io

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = Database()

# Helper function to check if alumni profile is complete
def check_profile_completion():
    """Check if the current alumni user has completed their profile"""
    if 'user_id' not in session or session.get('role') != 'alumni':
        return True  # Not applicable for non-alumni users
    
    profile = db.execute_single("""
        SELECT * FROM alumni_profiles WHERE user_id = ?
    """, (session['user_id'],))
    
    return profile is not None

# Initialize database on startup
with app.app_context():
    init_database()

# Authentication Routes
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('alumni_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = db.execute_single("SELECT * FROM users WHERE email = ?", (email,))
        
        if user and hashlib.sha256(password.encode('utf-8')).hexdigest() == user['password']:
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['role'] = user['role']
            session['is_verified'] = user['is_verified']
            
            flash('Login successful!', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                # Check if alumni has completed their profile
                profile = db.execute_single("""
                    SELECT * FROM alumni_profiles WHERE user_id = ?
                """, (user['id'],))
                
                if not profile:
                    session['profile_incomplete'] = True
                    return redirect(url_for('create_profile'))
                else:
                    return redirect(url_for('alumni_dashboard'))
        else:
            flash('Invalid email or password!', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Check if user already exists
        existing_user = db.execute_single("SELECT * FROM users WHERE email = ?", (email,))
        if existing_user:
            flash('Email already registered!', 'error')
            return render_template('signup.html')
        
        # Hash password
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        # Create user
        db.execute_query("""
            INSERT INTO users (email, password, role) 
            VALUES (?, ?, ?)
        """, (email, hashed_password, 'alumni'))
        
        # Get the new user ID and log them in
        new_user = db.execute_single("SELECT * FROM users WHERE email = ?", (email,))
        session['user_id'] = new_user['id']
        session['email'] = new_user['email']
        session['role'] = new_user['role']
        session['is_verified'] = new_user['is_verified']
        session['profile_incomplete'] = True  # Flag to indicate profile needs completion
        
        flash('Account created successfully! Please complete your profile to continue.', 'success')
        return redirect(url_for('create_profile'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

# Profile Creation Route
@app.route('/create-profile', methods=['GET', 'POST'])
def create_profile():
    if 'user_id' not in session or session.get('role') != 'alumni':
        return redirect(url_for('login'))
    
    # Check if profile already exists
    existing_profile = db.execute_single("""
        SELECT * FROM alumni_profiles WHERE user_id = ?
    """, (session['user_id'],))
    
    if existing_profile:
        # Profile already exists, redirect to dashboard
        if 'profile_incomplete' in session:
            del session['profile_incomplete']
        return redirect(url_for('alumni_dashboard'))
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name'].strip()
            linkedin_url = request.form['linkedin_url'].strip()
            batch_year = int(request.form['batch_year'])
            department = request.form['department']
            has_job = request.form['has_job']
            
            # Validate required fields (LinkedIn is now optional)
            if not all([name, batch_year, department, has_job]):
                return jsonify({'success': False, 'message': 'All required fields must be filled'})
            
            # Validate LinkedIn URL format if provided
            if linkedin_url:
                import re
                linkedin_pattern = r'^https://(www\.)?linkedin\.com/in/[a-zA-Z0-9-]+/?$'
                if not re.match(linkedin_pattern, linkedin_url):
                    return jsonify({'success': False, 'message': 'Please enter a valid LinkedIn profile URL'})
            else:
                linkedin_url = None  # Set to None if empty
            
            # Handle job status
            current_job = None
            company = None
            location = None
            
            if has_job == 'yes':
                current_job = request.form.get('current_job', '').strip()
                company = request.form.get('company', '').strip()
                location = request.form.get('location', '').strip()
                
                if not all([current_job, company, location]):
                    return jsonify({'success': False, 'message': 'Job details are required when employed'})
            else:
                # Set as student status
                current_job = 'Student'
                company = 'Currently Studying'
                location = 'Student'
            
            # Create alumni profile
            db.execute_query("""
                INSERT INTO alumni_profiles 
                (user_id, name, batch_year, department, current_job, company, location, linkedin_url, privacy_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], name, batch_year, department, current_job, company, location, linkedin_url, 'public'))
            
            # Remove profile incomplete flag
            if 'profile_incomplete' in session:
                del session['profile_incomplete']
            
            return jsonify({
                'success': True, 
                'message': 'Profile created successfully!',
                'redirect_url': url_for('alumni_dashboard')
            })
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error creating profile: {str(e)}'})
    
    return render_template('alumni/create_profile.html')

# Alumni Dashboard
@app.route('/alumni/dashboard')
def alumni_dashboard():
    if 'user_id' not in session or session.get('role') != 'alumni':
        return redirect(url_for('login'))
    
    # Check if profile is complete
    profile = db.execute_single("""
        SELECT * FROM alumni_profiles WHERE user_id = ?
    """, (session['user_id'],))
    
    if not profile:
        session['profile_incomplete'] = True
        return redirect(url_for('create_profile'))
    
    # Get recent events
    events = db.execute_query("""
        SELECT * FROM events WHERE event_date >= datetime('now') ORDER BY event_date LIMIT 5
    """)
    
    # Get announcements
    announcements = db.execute_query("""
        SELECT * FROM announcements WHERE is_active = TRUE ORDER BY created_at DESC LIMIT 3
    """)
    
    return render_template('alumni/dashboard.html', 
                         profile=profile, 
                         events=events, 
                         announcements=announcements)

# Notifications
@app.route('/api/notifications')
def get_notifications():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Get notifications for the user
    notifications = []
    
    # Recent announcements
    try:
        announcements = db.execute_query("""
            SELECT title, content, created_at FROM announcements 
            WHERE is_active = TRUE 
            ORDER BY created_at DESC LIMIT 5
        """)
        
        if announcements:
            for announcement in announcements:
                notifications.append({
                    'type': 'announcement',
                    'title': announcement['title'],
                    'message': announcement['content'][:100] + '...' if len(announcement['content']) > 100 else announcement['content'],
                    'time': announcement['created_at'],
                    'icon': 'fas fa-bullhorn'
                })
    except Exception as e:
        # Add a default announcement if table doesn't exist
        notifications.append({
            'type': 'announcement',
            'title': 'Welcome!',
            'message': 'Welcome to the Alumni Platform! Explore all the features available.',
            'time': '2025-09-03 19:00:00',
            'icon': 'fas fa-bullhorn'
        })
    
    # Upcoming events
    try:
        events = db.execute_query("""
            SELECT title, event_date FROM events 
            WHERE event_date >= datetime('now') 
            ORDER BY event_date LIMIT 3
        """)
        
        if events:
            for event in events:
                notifications.append({
                    'type': 'event',
                    'title': 'Upcoming Event',
                    'message': f"{event['title']} - {event['event_date']}",
                    'time': event['event_date'],
                    'icon': 'fas fa-calendar'
                })
    except Exception as e:
        # Add a default event notification
        notifications.append({
            'type': 'event',
            'title': 'Upcoming Event',
            'message': 'Annual Alumni Reunion 2025 - Stay tuned for details!',
            'time': '2025-10-15 10:00:00',
            'icon': 'fas fa-calendar'
        })
    
    # Recent forum posts (if user is alumni)
    if session.get('role') == 'alumni':
        try:
            posts = db.execute_query("""
                SELECT title, created_at 
                FROM forum_posts 
                WHERE user_id != ? 
                ORDER BY created_at DESC LIMIT 3
            """, (session['user_id'],))
            
            if posts:
                for post in posts:
                    notifications.append({
                        'type': 'forum',
                        'title': 'New Forum Post',
                        'message': f"{post['title']}",
                        'time': post['created_at'],
                        'icon': 'fas fa-comments'
                    })
        except Exception as e:
            # Skip forum posts if table doesn't exist or has issues
            pass
    
    return jsonify({
        'notifications': notifications[:10],  # Limit to 10 notifications
        'count': len(notifications)
    })

# Profile Management
@app.route('/alumni/profile', methods=['GET', 'POST'])
def alumni_profile():
    if 'user_id' not in session or session.get('role') != 'alumni':
        return redirect(url_for('login'))
    
    # Check if profile exists, if not redirect to create profile
    profile_check = db.execute_single("""
        SELECT * FROM alumni_profiles WHERE user_id = ?
    """, (session['user_id'],))
    
    if not profile_check:
        session['profile_incomplete'] = True
        return redirect(url_for('create_profile'))
    
    if request.method == 'POST':
        # Handle profile update
        name = request.form['name']
        batch_year = request.form['batch_year']
        department = request.form['department']
        current_job = request.form['current_job']
        company = request.form['company']
        location = request.form['location']
        achievements = request.form['achievements']
        linkedin_url = request.form['linkedin_url']
        privacy_level = request.form['privacy_level']
        
        # Check if profile exists
        existing_profile = db.execute_single("""
            SELECT * FROM alumni_profiles WHERE user_id = ?
        """, (session['user_id'],))
        
        if existing_profile:
            # Update existing profile
            db.execute_query("""
                UPDATE alumni_profiles SET 
                name = ?, batch_year = ?, department = ?, current_job = ?,
                company = ?, location = ?, achievements = ?, linkedin_url = ?,
                privacy_level = ?
                WHERE user_id = ?
            """, (name, batch_year, department, current_job, company, location,
                  achievements, linkedin_url, privacy_level, session['user_id']))
        else:
            # Create new profile
            db.execute_query("""
                INSERT INTO alumni_profiles 
                (user_id, name, batch_year, department, current_job, company, location,
                 achievements, linkedin_url, privacy_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], name, batch_year, department, current_job,
                  company, location, achievements, linkedin_url, privacy_level))
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('alumni_profile'))
    
    # Get current profile
    profile = db.execute_single("""
        SELECT * FROM alumni_profiles WHERE user_id = ?
    """, (session['user_id'],))
    
    return render_template('alumni/profile.html', profile=profile)

# Alumni Directory
@app.route('/alumni/directory')
def alumni_directory():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Check profile completion for alumni users
    if session.get('role') == 'alumni' and not check_profile_completion():
        session['profile_incomplete'] = True
        return redirect(url_for('create_profile'))
    
    search = request.args.get('search', '')
    batch = request.args.get('batch', '')
    department = request.args.get('department', '')
    
    query = """
        SELECT ap.*, u.email FROM alumni_profiles ap 
        JOIN users u ON ap.user_id = u.id 
        WHERE u.is_verified = TRUE AND ap.privacy_level = 'public'
    """
    params = []
    
    if search:
        query += " AND (ap.name LIKE ? OR ap.company LIKE ? OR ap.location LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])
    
    if batch:
        query += " AND ap.batch_year = ?"
        params.append(batch)
    
    if department:
        query += " AND ap.department = ?"
        params.append(department)
    
    query += " ORDER BY ap.name"
    
    alumni = db.execute_query(query, params)
    
    # Get unique batches and departments for filters
    batches = db.execute_query("SELECT DISTINCT batch_year FROM alumni_profiles WHERE batch_year IS NOT NULL ORDER BY batch_year DESC")
    departments = db.execute_query("SELECT DISTINCT department FROM alumni_profiles WHERE department IS NOT NULL ORDER BY department")
    
    return render_template('alumni/directory.html', 
                         alumni=alumni, 
                         batches=batches, 
                         departments=departments,
                         search=search,
                         selected_batch=batch,
                         selected_department=department)

# Forum
@app.route('/forum')
def forum():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    posts = db.execute_query("""
        SELECT fp.*, ap.name as author_name, 
               COUNT(fc.id) as comment_count
        FROM forum_posts fp
        LEFT JOIN alumni_profiles ap ON fp.author_id = ap.user_id
        LEFT JOIN forum_comments fc ON fp.id = fc.post_id
        GROUP BY fp.id
        ORDER BY fp.created_at DESC
    """)
    
    return render_template('forum/index.html', posts=posts)

@app.route('/forum/post/<int:post_id>')
def forum_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    post = db.execute_single("""
        SELECT fp.*, ap.name as author_name
        FROM forum_posts fp
        LEFT JOIN alumni_profiles ap ON fp.author_id = ap.user_id
        WHERE fp.id = ?
    """, (post_id,))
    
    if not post:
        flash('Post not found!', 'error')
        return redirect(url_for('forum'))
    
    comments = db.execute_query("""
        SELECT fc.*, ap.name as author_name
        FROM forum_comments fc
        LEFT JOIN alumni_profiles ap ON fc.author_id = ap.user_id
        WHERE fc.post_id = ?
        ORDER BY fc.created_at ASC
    """, (post_id,))
    
    return render_template('forum/post.html', post=post, comments=comments)

# Events
@app.route('/events')
def events():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Redirect admins to admin events page
    if session.get('role') == 'admin':
        return redirect(url_for('admin_events'))
    
    # Check profile completion for alumni users
    if session.get('role') == 'alumni' and not check_profile_completion():
        session['profile_incomplete'] = True
        return redirect(url_for('create_profile'))
    
    # Get ongoing events (happening today)
    ongoing_events = db.execute_query("""
        SELECT e.*, 
               COUNT(er.id) as registration_count,
               MAX(CASE WHEN er.user_id = ? THEN 1 ELSE 0 END) as is_registered,
               'ongoing' as event_status
        FROM events e
        LEFT JOIN event_registrations er ON e.id = er.event_id
        WHERE date(e.event_date) = date('now')
        GROUP BY e.id
        ORDER BY e.event_date ASC
    """, (session['user_id'],))
    
    # Get upcoming events (future dates)
    upcoming_events = db.execute_query("""
        SELECT e.*, 
               COUNT(er.id) as registration_count,
               MAX(CASE WHEN er.user_id = ? THEN 1 ELSE 0 END) as is_registered,
               'upcoming' as event_status
        FROM events e
        LEFT JOIN event_registrations er ON e.id = er.event_id
        WHERE date(e.event_date) > date('now')
        GROUP BY e.id
        ORDER BY e.event_date ASC
    """, (session['user_id'],))
    
    # Get past events
    past_events = db.execute_query("""
        SELECT e.*, COUNT(er.id) as registration_count,
               'past' as event_status
        FROM events e
        LEFT JOIN event_registrations er ON e.id = er.event_id
        WHERE date(e.event_date) < date('now')
        GROUP BY e.id
        ORDER BY e.event_date DESC
        LIMIT 10
    """)
    
    return render_template('events/index.html', 
                         ongoing_events=ongoing_events,
                         upcoming_events=upcoming_events, 
                         past_events=past_events,
                         datetime=datetime)

@app.route('/events/register/<int:event_id>', methods=['POST'])
def register_event(event_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Check if already registered
    existing = db.execute_single("""
        SELECT * FROM event_registrations 
        WHERE event_id = ? AND user_id = ?
    """, (event_id, session['user_id']))
    
    if existing:
        flash('You are already registered for this event!', 'warning')
    else:
        db.execute_query("""
            INSERT INTO event_registrations (event_id, user_id)
            VALUES (?, ?)
        """, (event_id, session['user_id']))
        flash('Successfully registered for the event!', 'success')
    
    return redirect(url_for('events'))

# Job Board
@app.route('/jobs')
def job_board():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    job_type = request.args.get('type', '')
    location = request.args.get('location', '')
    
    query = """
        SELECT jp.*, ap.name as posted_by_name
        FROM job_postings jp
        LEFT JOIN alumni_profiles ap ON jp.posted_by = ap.user_id
        WHERE 1=1
    """
    params = []
    
    if job_type:
        query += " AND jp.job_type = ?"
        params.append(job_type)
    
    if location:
        query += " AND jp.location LIKE ?"
        params.append(f"%{location}%")
    
    query += " ORDER BY jp.created_at DESC"
    
    jobs = db.execute_query(query, params)
    
    return render_template('jobs/index.html', jobs=jobs, 
                         selected_type=job_type, 
                         selected_location=location)

# Mentorship
@app.route('/mentorship')
def mentorship():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Check profile completion for alumni users
    if session.get('role') == 'alumni' and not check_profile_completion():
        session['profile_incomplete'] = True
        return redirect(url_for('create_profile'))
    
    # Get available mentors
    mentors = db.execute_query("""
        SELECT ap.*, u.email
        FROM alumni_profiles ap
        JOIN users u ON ap.user_id = u.id
        WHERE ap.available_for_mentorship = TRUE 
        AND u.is_verified = TRUE
        AND ap.user_id != ?
        ORDER BY ap.name
    """, (session['user_id'],))
    
    # Get user's mentorship requests
    requests = db.execute_query("""
        SELECT mr.*, ap.name as mentor_name
        FROM mentorship_requests mr
        JOIN alumni_profiles ap ON mr.mentor_id = ap.user_id
        WHERE mr.mentee_id = ?
        ORDER BY mr.created_at DESC
    """, (session['user_id'],))
    
    return render_template('mentorship/index.html', mentors=mentors, requests=requests)



# Admin Dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    # Get statistics
    stats = {
        'total_alumni': db.execute_single("SELECT COUNT(*) as count FROM users WHERE role = 'alumni'")['count'],
        'verified_alumni': db.execute_single("SELECT COUNT(*) as count FROM users WHERE role = 'alumni' AND is_verified = TRUE")['count'],
        'pending_verification': db.execute_single("SELECT COUNT(*) as count FROM users WHERE role = 'alumni' AND is_verified = FALSE")['count'],
        'total_events': db.execute_single("SELECT COUNT(*) as count FROM events")['count'],

        'total_posts': db.execute_single("SELECT COUNT(*) as count FROM forum_posts")['count']
    }
    
    # Get recent registrations
    recent_alumni = db.execute_query("""
        SELECT u.*, ap.name
        FROM users u
        LEFT JOIN alumni_profiles ap ON u.id = ap.user_id
        WHERE u.role = 'alumni' AND u.is_verified = FALSE
        ORDER BY u.created_at DESC
        LIMIT 10
    """)
    
    return render_template('admin/dashboard.html', stats=stats, recent_alumni=recent_alumni)

@app.route('/admin/verify_alumni/<int:user_id>')
def verify_alumni(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    db.execute_query("UPDATE users SET is_verified = TRUE WHERE id = ?", (user_id,))
    flash('Alumni verified successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_alumni', methods=['POST'])
def admin_add_alumni():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        email = request.form['email']
        name = request.form['name']
        batch_year = request.form['batch_year']
        department = request.form['department']
        password = request.form['password']
        auto_verify = 'auto_verify' in request.form
        
        # Check if user already exists
        existing_user = db.execute_single("SELECT * FROM users WHERE email = ?", (email,))
        if existing_user:
            return jsonify({'success': False, 'message': 'Email already registered'})
        
        # Hash password
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        # Create user
        db.execute_query("""
            INSERT INTO users (email, password, role, is_verified) 
            VALUES (?, ?, ?, ?)
        """, (email, hashed_password, 'alumni', auto_verify))
        
        # Get the new user ID
        user_id = db.execute_single("SELECT id FROM users WHERE email = ?", (email,))['id']
        
        # Create alumni profile
        db.execute_query("""
            INSERT INTO alumni_profiles (user_id, name, batch_year, department)
            VALUES (?, ?, ?, ?)
        """, (user_id, name, batch_year, department))
        
        return jsonify({'success': True, 'message': 'Alumni added successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/remove_alumni/<int:user_id>', methods=['DELETE'])
def admin_remove_alumni(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Delete alumni profile first (foreign key constraint)
        db.execute_query("DELETE FROM alumni_profiles WHERE user_id = ?", (user_id,))
        
        # Delete user
        db.execute_query("DELETE FROM users WHERE id = ? AND role = 'alumni'", (user_id,))
        
        return jsonify({'success': True, 'message': 'Alumni removed successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# File Upload Handler
@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        return jsonify({'success': True, 'filename': filename})
    
    return jsonify({'error': 'Invalid file type'}), 400

# API Routes for AJAX
@app.route('/api/sync_linkedin', methods=['POST'])
def sync_linkedin():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Simulate LinkedIn sync with dummy data
    dummy_data = {
        'current_job': 'Senior Software Engineer',
        'company': 'Tech Corp',
        'location': 'San Francisco, CA'
    }
    
    db.execute_query("""
        UPDATE alumni_profiles SET 
        current_job = ?, company = ?, location = ?
        WHERE user_id = ?
    """, (dummy_data['current_job'], dummy_data['company'], 
          dummy_data['location'], session['user_id']))
    
    return jsonify({'success': True, 'data': dummy_data})

@app.route('/api/download_certificate/<int:event_id>')
def download_certificate(event_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Check if user is registered for the event
    registration = db.execute_single("""
        SELECT er.*, e.title, e.event_date, ap.name
        FROM event_registrations er
        JOIN events e ON er.event_id = e.id
        JOIN alumni_profiles ap ON er.user_id = ap.user_id
        WHERE er.event_id = ? AND er.user_id = ?
    """, (event_id, session['user_id']))
    
    if not registration:
        flash('You are not registered for this event!', 'error')
        return redirect(url_for('events'))
    
    # Generate certificate (this would typically use a PDF library)
    # For now, return a simple response
    return jsonify({
        'success': True,
        'message': 'Certificate generated successfully!',
        'download_url': f'/certificates/event_{event_id}_user_{session["user_id"]}.pdf'
    })

# Messaging System
@app.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get inbox messages
    inbox_messages = db.execute_query("""
        SELECT m.*, ap.name as sender_name
        FROM messages m
        LEFT JOIN alumni_profiles ap ON m.sender_id = ap.user_id
        WHERE m.recipient_id = ?
        ORDER BY m.created_at DESC
    """, (session['user_id'],))
    
    # Get sent messages
    sent_messages = db.execute_query("""
        SELECT m.*, ap.name as recipient_name
        FROM messages m
        LEFT JOIN alumni_profiles ap ON m.recipient_id = ap.user_id
        WHERE m.sender_id = ?
        ORDER BY m.created_at DESC
    """, (session['user_id'],))
    
    # Get unread count
    unread_count = db.execute_single("""
        SELECT COUNT(*) as count FROM messages 
        WHERE recipient_id = ? AND is_read = FALSE
    """, (session['user_id'],))['count']
    
    # Get available users for compose
    if session.get('role') == 'admin':
        available_users = db.execute_query("""
            SELECT ap.user_id, ap.name, u.email
            FROM alumni_profiles ap
            JOIN users u ON ap.user_id = u.id
            WHERE u.is_verified = TRUE AND u.id != ?
            ORDER BY ap.name
        """, (session['user_id'],))
    else:
        # Alumni can message other alumni and admins
        available_users = db.execute_query("""
            SELECT ap.user_id, ap.name, u.email
            FROM alumni_profiles ap
            JOIN users u ON ap.user_id = u.id
            WHERE u.is_verified = TRUE AND u.id != ?
            UNION
            SELECT u.id as user_id, u.email as name, u.email
            FROM users u
            WHERE u.role = 'admin' AND u.id != ?
            ORDER BY name
        """, (session['user_id'], session['user_id']))
    
    return render_template('messages/inbox.html',
                         inbox_messages=inbox_messages,
                         sent_messages=sent_messages,
                         unread_count=unread_count,
                         available_users=available_users)

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        recipient_id = request.form['recipient_id']
        subject = request.form['subject']
        content = request.form['content']
        
        db.execute_query("""
            INSERT INTO messages (sender_id, recipient_id, subject, content)
            VALUES (?, ?, ?, ?)
        """, (session['user_id'], recipient_id, subject, content))
        
        return jsonify({'success': True, 'message': 'Message sent successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/messages/<int:message_id>')
def get_message(message_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    message = db.execute_single("""
        SELECT m.*, ap.name as sender_name
        FROM messages m
        LEFT JOIN alumni_profiles ap ON m.sender_id = ap.user_id
        WHERE m.id = ? AND (m.sender_id = ? OR m.recipient_id = ?)
    """, (message_id, session['user_id'], session['user_id']))
    
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    
    return jsonify({'success': True, 'message': dict(message)})

@app.route('/api/messages/<int:message_id>/read', methods=['POST'])
def mark_message_read(message_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    db.execute_query("""
        UPDATE messages SET is_read = TRUE 
        WHERE id = ? AND recipient_id = ?
    """, (message_id, session['user_id']))
    
    return jsonify({'success': True})

@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
def delete_message(message_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    db.execute_query("""
        DELETE FROM messages 
        WHERE id = ? AND (sender_id = ? OR recipient_id = ?)
    """, (message_id, session['user_id'], session['user_id']))
    
    return jsonify({'success': True})

@app.route('/api/message_count')
def get_message_count():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    unread_count = db.execute_single("""
        SELECT COUNT(*) as count FROM messages 
        WHERE recipient_id = ? AND is_read = FALSE
    """, (session['user_id'],))['count']
    
    return jsonify({'count': unread_count})

# Admin Event Management Routes
@app.route('/admin/events')
def admin_events():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    try:
        current_datetime = datetime.now()
        
        # Get all events with registration counts
        all_events_detailed = db.execute_query("""
            SELECT e.*, COUNT(er.id) as registration_count,
                   COUNT(CASE WHEN er.attended = 1 THEN 1 END) as attendance_count
            FROM events e
            LEFT JOIN event_registrations er ON e.id = er.event_id
            GROUP BY e.id
            ORDER BY e.event_date ASC
        """)
        
        # Initialize event categories
        ongoing_events = []
        upcoming_events = []
        past_events = []
        all_events = []
        
        if all_events_detailed:
            for event in all_events_detailed:
                event_date = event['event_date']
                
                # Ensure event_date is a datetime object
                if isinstance(event_date, str):
                    try:
                        event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                    except:
                        try:
                            event_date = datetime.strptime(event_date, '%Y-%m-%d %H:%M:%S')
                        except:
                            continue
                
                # Update the event_date in the event dict
                event['event_date'] = event_date
                
                # Categorize events
                if event_date.date() == current_datetime.date():
                    event['status'] = 'ongoing'
                    ongoing_events.append(event)
                elif event_date > current_datetime:
                    event['status'] = 'upcoming'
                    upcoming_events.append(event)
                else:
                    event['status'] = 'past'
                    past_events.append(event)
                
                # Add to all events list
                all_events.append(event)
        
        # Statistics
        stats = {
            'total_events': len(all_events),
            'total_registrations': db.execute_single("SELECT COUNT(*) as count FROM event_registrations")['count'] or 0,
            'ongoing_count': len(ongoing_events),
            'upcoming_count': len(upcoming_events),
        }
        
        # Limit past events to 20 most recent
        past_events = sorted(past_events, key=lambda x: x['event_date'], reverse=True)[:20]
        
        return render_template('admin/events.html', 
                             total_events=stats['total_events'],
                             total_registrations=stats['total_registrations'],
                             ongoing_count=stats['ongoing_count'],
                             upcoming_count=stats['upcoming_count'],
                             ongoing_events=ongoing_events,
                             upcoming_events=upcoming_events, 
                             past_events=past_events,
                             all_events=all_events,
                             datetime=datetime)
    
    except Exception as e:
        print(f"ERROR in admin_events: {str(e)}")
        flash(f'Error loading events: {str(e)}', 'error')
        return render_template('admin/events.html', 
                             total_events=0,
                             total_registrations=0,
                             ongoing_count=0,
                             upcoming_count=0,
                             ongoing_events=[],
                             upcoming_events=[], 
                             past_events=[],
                             all_events=[],
                             datetime=datetime)

@app.route('/admin/events/<int:event_id>/registrations')
def admin_event_registrations(event_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get event details
        event = db.execute_single("SELECT * FROM events WHERE id = ?", (event_id,))
        if not event:
            return jsonify({'success': False, 'message': 'Event not found'})
        
        # Get registrations with alumni details
        registrations = db.execute_query("""
            SELECT er.*, ap.name, ap.batch_year, ap.department, ap.company, u.email,
                   er.status as registration_status
            FROM event_registrations er
            JOIN alumni_profiles ap ON er.user_id = ap.user_id
            JOIN users u ON er.user_id = u.id
            WHERE er.event_id = ?
            ORDER BY er.registered_at DESC
        """, (event_id,))
        
        # Format registration data
        formatted_registrations = []
        for reg in registrations:
            formatted_reg = dict(reg)
            # Format registered_at date
            if formatted_reg['registered_at']:
                if isinstance(formatted_reg['registered_at'], str):
                    try:
                        reg_date = datetime.fromisoformat(formatted_reg['registered_at'].replace('Z', '+00:00'))
                    except:
                        reg_date = datetime.strptime(formatted_reg['registered_at'], '%Y-%m-%d %H:%M:%S')
                else:
                    reg_date = formatted_reg['registered_at']
                formatted_reg['registered_at'] = reg_date.strftime('%b %d, %Y at %I:%M %p')
            
            # Set default status if not present
            if not formatted_reg.get('status'):
                formatted_reg['status'] = 'approved'
            
            formatted_registrations.append(formatted_reg)
        
        return jsonify({
            'success': True, 
            'event_title': event['title'],
            'registrations': formatted_registrations
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/registration/<int:registration_id>/approve', methods=['POST'])
def admin_approve_registration(registration_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db.execute_query("""
            UPDATE event_registrations SET status = 'approved' WHERE id = ?
        """, (registration_id,))
        
        return jsonify({'success': True, 'message': 'Registration approved'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/registration/<int:registration_id>/edit', methods=['POST'])
def admin_edit_registration(registration_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        status = data.get('status', 'approved')
        notes = data.get('notes', '')
        
        db.execute_query("""
            UPDATE event_registrations SET status = ?, admin_notes = ? WHERE id = ?
        """, (status, notes, registration_id))
        
        return jsonify({'success': True, 'message': 'Registration updated'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/registrations/bulk-approve', methods=['POST'])
def admin_bulk_approve_registrations():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        registration_ids = data.get('registration_ids', [])
        
        if not registration_ids:
            return jsonify({'success': False, 'message': 'No registrations selected'})
        
        placeholders = ','.join(['?' for _ in registration_ids])
        db.execute_query(f"""
            UPDATE event_registrations SET status = 'approved' 
            WHERE id IN ({placeholders})
        """, registration_ids)
        
        return jsonify({
            'success': True, 
            'message': f'{len(registration_ids)} registrations approved'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/registrations/bulk-remove', methods=['POST'])
def admin_bulk_remove_registrations():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        registration_ids = data.get('registration_ids', [])
        
        if not registration_ids:
            return jsonify({'success': False, 'message': 'No registrations selected'})
        
        placeholders = ','.join(['?' for _ in registration_ids])
        db.execute_query(f"DELETE FROM event_registrations WHERE id IN ({placeholders})", registration_ids)
        
        return jsonify({
            'success': True, 
            'message': f'{len(registration_ids)} registrations removed'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/<int:event_id>/delete', methods=['DELETE'])
def admin_delete_event(event_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Delete event registrations first (foreign key constraint)
        db.execute_query("DELETE FROM event_registrations WHERE event_id = ?", (event_id,))
        
        # Delete event
        db.execute_query("DELETE FROM events WHERE id = ?", (event_id,))
        
        return jsonify({'success': True, 'message': 'Event deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/<int:event_id>/send-reminders', methods=['POST'])
def admin_send_reminders(event_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get registered users count
        count = db.execute_single("""
            SELECT COUNT(*) as count FROM event_registrations WHERE event_id = ?
        """, (event_id,))['count']
        
        # Simulate sending reminders (in real app, would send actual emails)
        return jsonify({'success': True, 'message': 'Reminders sent successfully', 'count': count})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})



@app.route('/admin/events/registration/<int:registration_id>/remove', methods=['DELETE'])
def admin_remove_registration(registration_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Remove the registration
        db.execute_query("DELETE FROM event_registrations WHERE id = ?", (registration_id,))
        
        return jsonify({'success': True, 'message': 'Registration removed successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/registration/<int:registration_id>/remind', methods=['POST'])
def admin_remind_registration(registration_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get registration details
        registration = db.execute_single("""
            SELECT er.*, e.title as event_title, e.event_date, ap.name, u.email
            FROM event_registrations er
            JOIN events e ON er.event_id = e.id
            JOIN alumni_profiles ap ON er.user_id = ap.user_id
            JOIN users u ON er.user_id = u.id
            WHERE er.id = ?
        """, (registration_id,))
        
        if not registration:
            return jsonify({'success': False, 'message': 'Registration not found'})
        
        # In a real application, you would send an email here
        # For now, we'll just simulate the reminder
        print(f"Reminder sent to {registration['email']} for event: {registration['event_title']}")
        
        return jsonify({'success': True, 'message': 'Reminder sent successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/registrations/bulk-remind', methods=['POST'])
def admin_bulk_remind_registrations():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        registration_ids = data.get('registration_ids', [])
        
        if not registration_ids:
            return jsonify({'success': False, 'message': 'No registrations selected'})
        
        # Get registration details
        placeholders = ','.join(['?' for _ in registration_ids])
        registrations = db.execute_query(f"""
            SELECT er.*, e.title as event_title, e.event_date, ap.name, u.email
            FROM event_registrations er
            JOIN events e ON er.event_id = e.id
            JOIN alumni_profiles ap ON er.user_id = ap.user_id
            JOIN users u ON er.user_id = u.id
            WHERE er.id IN ({placeholders})
        """, registration_ids)
        
        # In a real application, you would send emails here
        # For now, we'll just simulate the reminders
        for registration in registrations:
            print(f"Reminder sent to {registration['email']} for event: {registration['event_title']}")
        
        return jsonify({
            'success': True, 
            'message': f'Reminders sent to {len(registrations)} alumni'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/alumni/<int:user_id>/profile')
def admin_view_alumni_profile(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    # Get alumni profile
    profile = db.execute_single("""
        SELECT ap.*, u.email, u.is_verified, u.created_at as user_created_at
        FROM alumni_profiles ap
        JOIN users u ON ap.user_id = u.id
        WHERE ap.user_id = ?
    """, (user_id,))
    
    if not profile:
        flash('Alumni profile not found!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Get alumni's event registrations
    registrations = db.execute_query("""
        SELECT er.*, e.title, e.event_date, e.location
        FROM event_registrations er
        JOIN events e ON er.event_id = e.id
        WHERE er.user_id = ?
        ORDER BY e.event_date DESC
    """, (user_id,))
    
    return render_template('admin/alumni_profile.html', 
                         profile=profile, 
                         registrations=registrations)

# Debug route to check events
@app.route('/debug/events')
def debug_events():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Get all events
    all_events = db.execute_query("SELECT * FROM events ORDER BY event_date")
    
    # Get current datetime
    current_time = datetime.now()
    
    # Manual categorization for debugging
    ongoing = []
    upcoming = []
    past = []
    
    for event in all_events:
        event_date = event['event_date']
        if isinstance(event_date, str):
            try:
                event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            except:
                continue
        
        if event_date.date() == current_time.date():
            ongoing.append(event)
        elif event_date > current_time:
            upcoming.append(event)
        else:
            past.append(event)
    
    return jsonify({
        'current_time': current_time.isoformat(),
        'total_events': len(all_events),
        'all_events': [{'id': e['id'], 'title': e['title'], 'date': str(e['event_date'])} for e in all_events],
        'ongoing_count': len(ongoing),
        'upcoming_count': len(upcoming),
        'past_count': len(past),
        'ongoing': [{'id': e['id'], 'title': e['title'], 'date': str(e['event_date'])} for e in ongoing],
        'upcoming': [{'id': e['id'], 'title': e['title'], 'date': str(e['event_date'])} for e in upcoming],
        'past': [{'id': e['id'], 'title': e['title'], 'date': str(e['event_date'])} for e in past]
    })

# Enhanced Event Management Routes
@app.route('/admin/events/create', methods=['POST'])
def admin_create_event():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        title = request.form['title']
        description = request.form['description']
        event_date = request.form['event_date']
        location = request.form.get('location', '')
        capacity = request.form.get('capacity')
        event_type = request.form.get('event_type', 'general')
        require_approval = 'require_approval' in request.form
        send_notifications = 'send_notifications' in request.form
        
        # Convert capacity to int if provided
        capacity_value = int(capacity) if capacity and capacity.strip() else None
        
        db.execute_query("""
            INSERT INTO events (title, description, event_date, location, capacity, event_type, 
                              require_approval, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, description, event_date, location, capacity_value, event_type, 
              require_approval, session['user_id']))
        
        # Send notifications if requested
        if send_notifications:
            # In a real app, this would send actual notifications
            pass
        
        return jsonify({'success': True, 'message': 'Event created successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/<int:event_id>/edit')
def admin_get_event(event_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        event = db.execute_single("SELECT * FROM events WHERE id = ?", (event_id,))
        if not event:
            return jsonify({'success': False, 'message': 'Event not found'})
        
        # Format datetime for HTML input
        if event['event_date']:
            if isinstance(event['event_date'], str):
                try:
                    event_date = datetime.fromisoformat(event['event_date'].replace('Z', '+00:00'))
                except:
                    event_date = datetime.strptime(event['event_date'], '%Y-%m-%d %H:%M:%S')
            else:
                event_date = event['event_date']
            
            event['event_date'] = event_date.strftime('%Y-%m-%dT%H:%M')
        
        return jsonify({'success': True, 'event': event})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/<int:event_id>/update', methods=['POST'])
def admin_update_event(event_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        title = request.form['title']
        description = request.form['description']
        event_date = request.form['event_date']
        location = request.form.get('location', '')
        capacity = request.form.get('capacity')
        event_type = request.form.get('event_type', 'general')
        require_approval = 'require_approval' in request.form
        
        # Convert capacity to int if provided
        capacity_value = int(capacity) if capacity and capacity.strip() else None
        
        db.execute_query("""
            UPDATE events SET title = ?, description = ?, event_date = ?, location = ?, 
                            capacity = ?, event_type = ?, require_approval = ?
            WHERE id = ?
        """, (title, description, event_date, location, capacity_value, event_type, 
              require_approval, event_id))
        
        return jsonify({'success': True, 'message': 'Event updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/<int:event_id>/duplicate', methods=['POST'])
def admin_duplicate_event(event_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get original event
        original_event = db.execute_single("SELECT * FROM events WHERE id = ?", (event_id,))
        if not original_event:
            return jsonify({'success': False, 'message': 'Event not found'})
        
        # Create duplicate with modified title and future date
        new_title = f"Copy of {original_event['title']}"
        new_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        
        db.execute_query("""
            INSERT INTO events (title, description, event_date, location, capacity, 
                              event_type, require_approval, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_title, original_event['description'], new_date, original_event['location'],
              original_event.get('capacity'), original_event.get('event_type', 'general'),
              original_event.get('require_approval', False), session['user_id']))
        
        return jsonify({'success': True, 'message': 'Event duplicated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/<int:event_id>/broadcast', methods=['POST'])
def admin_broadcast_message(event_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({'success': False, 'message': 'Message is required'})
        
        # Get registered users for this event
        registrations = db.execute_query("""
            SELECT er.user_id, ap.name, u.email
            FROM event_registrations er
            JOIN users u ON er.user_id = u.id
            JOIN alumni_profiles ap ON er.user_id = ap.user_id
            WHERE er.event_id = ?
        """, (event_id,))
        
        # In a real app, this would send actual notifications/emails
        # For now, we'll just simulate it
        
        return jsonify({
            'success': True, 
            'message': f'Message broadcasted to {len(registrations)} attendees'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/<int:event_id>/end', methods=['POST'])
def admin_end_event(event_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Mark event as ended by updating its date to past
        db.execute_query("""
            UPDATE events SET event_date = datetime('now', '-1 hour')
            WHERE id = ?
        """, (event_id,))
        
        return jsonify({'success': True, 'message': 'Event ended successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/bulk-delete', methods=['POST'])
def admin_bulk_delete_events():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        event_ids = data.get('event_ids', [])
        
        if not event_ids:
            return jsonify({'success': False, 'message': 'No events selected'})
        
        # Delete registrations first
        for event_id in event_ids:
            db.execute_query("DELETE FROM event_registrations WHERE event_id = ?", (event_id,))
        
        # Delete events
        placeholders = ','.join(['?' for _ in event_ids])
        db.execute_query(f"DELETE FROM events WHERE id IN ({placeholders})", event_ids)
        
        return jsonify({
            'success': True, 
            'message': f'{len(event_ids)} events deleted successfully',
            'deleted_count': len(event_ids)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/bulk-reminders', methods=['POST'])
def admin_bulk_send_reminders():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        event_ids = data.get('event_ids', [])
        
        if not event_ids:
            return jsonify({'success': False, 'message': 'No events selected'})
        
        total_sent = 0
        for event_id in event_ids:
            # Get registration count for each event
            count = db.execute_single("""
                SELECT COUNT(*) as count FROM event_registrations WHERE event_id = ?
            """, (event_id,))
            total_sent += count['count'] if count else 0
        
        # In a real app, this would send actual reminders
        
        return jsonify({
            'success': True, 
            'message': f'Reminders sent successfully',
            'event_count': len(event_ids),
            'total_recipients': total_sent
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/live-status')
def admin_get_live_status():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get ongoing events with current attendee counts
        ongoing_events = db.execute_query("""
            SELECT e.id, e.title, COUNT(er.id) as current_attendees
            FROM events e
            LEFT JOIN event_registrations er ON e.id = er.event_id
            WHERE date(e.event_date) = date('now')
            GROUP BY e.id
        """)
        
        return jsonify({'success': True, 'events': ongoing_events})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/events/export')
def admin_export_events():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        event_ids = request.args.get('event_ids', '').split(',') if request.args.get('event_ids') else []
        
        if event_ids and event_ids[0]:  # If specific events requested
            placeholders = ','.join(['?' for _ in event_ids])
            events = db.execute_query(f"""
                SELECT e.*, COUNT(er.id) as registration_count
                FROM events e
                LEFT JOIN event_registrations er ON e.id = er.event_id
                WHERE e.id IN ({placeholders})
                GROUP BY e.id
                ORDER BY e.event_date DESC
            """, event_ids)
        else:  # Export all events
            events = db.execute_query("""
                SELECT e.*, COUNT(er.id) as registration_count
                FROM events e
                LEFT JOIN event_registrations er ON e.id = er.event_id
                GROUP BY e.id
                ORDER BY e.event_date DESC
            """)
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Event ID', 'Title', 'Description', 'Date', 'Location', 'Type', 'Registrations', 'Status'])
        
        # Write data
        current_time = datetime.now()
        for event in events:
            event_date = event['event_date']
            if isinstance(event_date, str):
                try:
                    event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                except:
                    event_date = datetime.strptime(event_date, '%Y-%m-%d %H:%M:%S')
            
            # Determine status
            if event_date.date() == current_time.date():
                status = 'Ongoing'
            elif event_date > current_time:
                status = 'Upcoming'
            else:
                status = 'Past'
            
            writer.writerow([
                event['id'],
                event['title'],
                event['description'],
                event_date.strftime('%Y-%m-%d %H:%M:%S'),
                event['location'] or '',
                event.get('event_type', 'general'),
                event['registration_count'],
                status
            ])
        
        # Create response
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'events_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Route to create sample events for testing
@app.route('/admin/create-sample-events', methods=['POST'])
def create_sample_events():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Sample events with future dates
        sample_events = [
            {
                'title': 'Annual Alumni Reunion 2025',
                'description': 'Join us for our biggest alumni gathering of the year! Reconnect with classmates, enjoy great food, and celebrate our shared memories.',
                'event_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S'),
                'location': 'College Main Auditorium'
            },
            {
                'title': 'Tech Talk: AI in Industry',
                'description': 'Learn about the latest trends in AI and how they are transforming various industries. Featuring speakers from top tech companies.',
                'event_date': (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d %H:%M:%S'),
                'location': 'Virtual Event'
            },
            {
                'title': 'Career Networking Session',
                'description': 'Network with alumni from various industries and explore new career opportunities. Perfect for recent graduates and career changers.',
                'event_date': (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d %H:%M:%S'),
                'location': 'College Conference Hall'
            },
            {
                'title': 'Entrepreneurship Workshop',
                'description': 'Learn from successful alumni entrepreneurs about starting and scaling your own business. Interactive sessions and Q&A included.',
                'event_date': (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S'),
                'location': 'Innovation Center'
            },
            {
                'title': 'Live Demo Event - Today',
                'description': 'This is a test event happening today to test ongoing events functionality.',
                'event_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'location': 'Test Location'
            }
        ]
        
        created_count = 0
        for event in sample_events:
            db.execute_query("""
                INSERT INTO events (title, description, event_date, location, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (event['title'], event['description'], event['event_date'], 
                  event['location'], session['user_id']))
            created_count += 1
        
        return jsonify({'success': True, 'message': f'Created {created_count} sample events successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)