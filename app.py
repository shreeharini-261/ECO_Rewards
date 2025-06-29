from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql.cursors
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'damn',  # Enter your MySQL password here
    'db': 'ecorewards',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**db_config)

# Helper functions
def get_user_points(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM user_points WHERE user_id = %s", (user_id,))
            return cursor.fetchone()
    finally:
        connection.close()

def update_user_points(user_id, points_earned=0, points_redeemed=0):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if points_earned > 0:
                cursor.execute("""
                    UPDATE user_points 
                    SET total_points_earned = total_points_earned + %s,
                        points_available = points_available + %s
                    WHERE user_id = %s
                """, (points_earned, points_earned, user_id))
            if points_redeemed > 0:
                cursor.execute("""
                    UPDATE user_points 
                    SET points_redeemed = points_redeemed + %s,
                        points_available = points_available - %s
                    WHERE user_id = %s
                """, (points_redeemed, points_redeemed, user_id))
        connection.commit()
    finally:
        connection.close()

def calculate_points(waste_type, quantity):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT points_per_kg FROM point_rules WHERE waste_type = %s AND is_active = TRUE", (waste_type,))
            rule = cursor.fetchone()
            return int(float(quantity) * float(rule['points_per_kg'])) if rule else 0
    finally:
        connection.close()

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard' if session.get('is_admin') else 'user_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
                user = cursor.fetchone()
                
                if user:
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['is_admin'] = user['is_admin']
                    return redirect(url_for('admin_dashboard' if user['is_admin'] else 'user_dashboard'))
                else:
                    flash('Invalid username or password', 'danger')
        finally:
            connection.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Enhanced User Dashboard Route
@app.route('/user/dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('is_admin'):
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    points = get_user_points(user_id)
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get pending and approved submissions
            cursor.execute("""
                SELECT ws.*, wr.points_per_kg, 
                CASE WHEN ws.status = 'approved' THEN 'Approved' 
                     WHEN ws.status = 'rejected' THEN 'Rejected'
                     ELSE 'Pending' END as status_text
                FROM waste_submissions ws
                LEFT JOIN point_rules wr ON ws.waste_type = wr.waste_type
                WHERE ws.user_id = %s 
                ORDER BY ws.submission_date DESC
                LIMIT 10
            """, (user_id,))
            submissions = cursor.fetchall()
            
            # Get available rewards
            cursor.execute("""
                SELECT * FROM rewards 
                WHERE is_active = TRUE 
                AND (stock IS NULL OR stock > 0) 
                ORDER BY points_required
            """)
            rewards = cursor.fetchall()
            
            # Get redemption history
            cursor.execute("""
                SELECT r.*, rw.name as reward_name,
                CASE WHEN r.status = 'approved' THEN 'Approved' 
                     WHEN r.status = 'rejected' THEN 'Rejected'
                     ELSE 'Pending' END as status_text
                FROM redemptions r
                JOIN rewards rw ON r.reward_id = rw.id
                WHERE r.user_id = %s 
                ORDER BY r.redemption_date DESC
                LIMIT 5
            """, (user_id,))
            redemptions = cursor.fetchall()
    finally:
        connection.close()
    
    return render_template('user_dashboard.html', 
                         points=points, 
                         submissions=submissions, 
                         rewards=rewards, 
                         redemptions=redemptions)

# Enhanced Admin Approval System
@app.route('/admin/process-submissions', methods=['POST'])
def process_submissions():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    submission_id = request.form.get('submission_id')
    action = request.form.get('action')
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if action == 'approve':
                cursor.execute("""
                    UPDATE waste_submissions 
                    SET status = 'approved' 
                    WHERE id = %s AND status = 'pending'
                """, (submission_id,))
                
                # Get submission details to award points
                cursor.execute("""
                    SELECT user_id, waste_type, quantity, points_earned 
                    FROM waste_submissions 
                    WHERE id = %s
                """, (submission_id,))
                submission = cursor.fetchone()
                
                if submission and not submission['points_earned']:
                    points = calculate_points(submission['waste_type'], submission['quantity'])
                    cursor.execute("""
                        UPDATE waste_submissions 
                        SET points_earned = %s 
                        WHERE id = %s
                    """, (points, submission_id))
                    update_user_points(submission['user_id'], points_earned=points)
                
                flash('Submission approved and points awarded', 'success')
            
            elif action == 'reject':
                cursor.execute("""
                    UPDATE waste_submissions 
                    SET status = 'rejected' 
                    WHERE id = %s
                """, (submission_id,))
                flash('Submission rejected', 'info')
            
            connection.commit()
    finally:
        connection.close()
    
    return redirect(url_for('admin_submissions'))

# Enhanced Waste Collection Tracking
@app.route('/admin/mark-collected/<int:submission_id>')
def mark_collected(submission_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE waste_submissions 
                SET collected_date = NOW() 
                WHERE id = %s AND status = 'approved'
            """, (submission_id,))
            connection.commit()
            flash('Waste marked as collected', 'success')
    finally:
        connection.close()
    
    return redirect(url_for('admin_submissions'))
@app.route('/user/submit-waste', methods=['POST'])
def submit_waste():
    if 'user_id' not in session or session.get('is_admin'):
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    waste_type = request.form['waste_type']
    quantity = float(request.form['quantity'])
    location = request.form.get('location', '')
    
    points_earned = calculate_points(waste_type, quantity)
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO waste_submissions 
                (user_id, waste_type, quantity, location, points_earned, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
            """, (user_id, waste_type, quantity, location, points_earned))
            connection.commit()
        
        if points_earned > 0:
            update_user_points(user_id, points_earned=points_earned)
        
        flash(f'Waste submitted successfully! You earned {points_earned} points.', 'success')
    finally:
        connection.close()
    
    return redirect(url_for('user_dashboard'))

@app.route('/user/redeem-reward', methods=['POST'])
def redeem_reward():
    if 'user_id' not in session or session.get('is_admin'):
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    reward_id = request.form['reward_id']
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM rewards WHERE id = %s AND is_active = TRUE", (reward_id,))
            reward = cursor.fetchone()
            
            if not reward:
                flash('Invalid reward selected', 'danger')
                return redirect(url_for('user_dashboard'))
            
            if reward['stock'] is not None and reward['stock'] <= 0:
                flash('This reward is out of stock', 'danger')
                return redirect(url_for('user_dashboard'))
            
            user_points = get_user_points(user_id)
            if user_points['points_available'] < reward['points_required']:
                flash('Not enough points to redeem this reward', 'danger')
                return redirect(url_for('user_dashboard'))
            
            cursor.execute("""
                INSERT INTO redemptions 
                (user_id, reward_id, points_spent, status)
                VALUES (%s, %s, %s, 'pending')
            """, (user_id, reward_id, reward['points_required']))
            
            if reward['stock'] is not None:
                cursor.execute("UPDATE rewards SET stock = stock - 1 WHERE id = %s", (reward_id,))
            
            connection.commit()
        
        update_user_points(user_id, points_redeemed=reward['points_required'])
        flash(f'Reward redemption requested successfully! {reward["points_required"]} points deducted.', 'success')
    finally:
        connection.close()
    
    return redirect(url_for('user_dashboard'))

# Admin Routes
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM waste_submissions WHERE status = 'pending'")
            pending_submissions = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM redemptions WHERE status = 'pending'")
            pending_redemptions = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = FALSE")
            total_users = cursor.fetchone()['count']
            
            cursor.execute("SELECT SUM(total_points_earned) as total FROM user_points")
            total_points = cursor.fetchone()['total'] or 0
            
            cursor.execute("""
                (SELECT 'submission' as type, id, user_id, submission_date as date 
                 FROM waste_submissions 
                 ORDER BY submission_date DESC LIMIT 5)
                UNION ALL
                (SELECT 'redemption' as type, id, user_id, redemption_date as date 
                 FROM redemptions 
                 ORDER BY redemption_date DESC LIMIT 5)
                ORDER BY date DESC LIMIT 10
            """)
            activities = cursor.fetchall()
    finally:
        connection.close()
    
    return render_template('admin_dashboard.html',
                         pending_submissions=pending_submissions,
                         pending_redemptions=pending_redemptions,
                         total_users=total_users,
                         total_points=total_points,
                         activities=activities)

@app.route('/admin/submissions')
def admin_submissions():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    status = request.args.get('status', 'pending')
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ws.*, u.username 
                FROM waste_submissions ws
                JOIN users u ON ws.user_id = u.id
                WHERE ws.status = %s
                ORDER BY ws.submission_date DESC
            """, (status,))
            submissions = cursor.fetchall()
    finally:
        connection.close()
    
    return render_template('admin_submissions.html', 
                         submissions=submissions, 
                         status=status)
    
    return render_template('admin_submissions.html', submissions=submissions, status=status)
@app.route('/admin/approve-submission/<int:submission_id>')
def approve_submission(submission_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM waste_submissions WHERE id = %s", (submission_id,))
            submission = cursor.fetchone()
            
            if submission and submission['status'] == 'pending':
                cursor.execute("UPDATE waste_submissions SET status = 'approved' WHERE id = %s", (submission_id,))
                
                if not submission['points_earned']:
                    points_earned = calculate_points(submission['waste_type'], submission['quantity'])
                    cursor.execute("UPDATE waste_submissions SET points_earned = %s WHERE id = %s", (points_earned, submission_id))
                    update_user_points(submission['user_id'], points_earned=points_earned)
                
                connection.commit()
                flash('Submission approved successfully', 'success')
    finally:
        connection.close()
    
    return redirect(url_for('admin_submissions'))

@app.route('/admin/reject-submission/<int:submission_id>')
def reject_submission(submission_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE waste_submissions SET status = 'rejected' WHERE id = %s AND status = 'pending'", (submission_id,))
            connection.commit()
            flash('Submission rejected', 'info')
    finally:
        connection.close()
    
    return redirect(url_for('admin_submissions'))

@app.route('/admin/redemptions')
def admin_redemptions():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    status = request.args.get('status', 'pending')
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT r.*, u.username, rw.name as reward_name 
                FROM redemptions r
                JOIN users u ON r.user_id = u.id
                JOIN rewards rw ON r.reward_id = rw.id
                WHERE r.status = %s
                ORDER BY r.redemption_date DESC
            """, (status,))
            redemptions = cursor.fetchall()
    finally:
        connection.close()
    
    return render_template('admin_redemptions.html', redemptions=redemptions, status=status)

@app.route('/admin/approve-redemption/<int:redemption_id>')
def approve_redemption(redemption_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE redemptions SET status = 'approved' WHERE id = %s AND status = 'pending'", (redemption_id,))
            connection.commit()
            flash('Redemption approved successfully', 'success')
    finally:
        connection.close()
    
    return redirect(url_for('admin_redemptions'))

@app.route('/admin/reject-redemption/<int:redemption_id>')
def reject_redemption(redemption_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM redemptions WHERE id = %s", (redemption_id,))
            redemption = cursor.fetchone()
            
            if redemption:
                update_user_points(redemption['user_id'], points_earned=redemption['points_spent'])
                
                cursor.execute("SELECT stock FROM rewards WHERE id = %s", (redemption['reward_id'],))
                reward = cursor.fetchone()
                if reward and reward['stock'] is not None:
                    cursor.execute("UPDATE rewards SET stock = stock + 1 WHERE id = %s", (redemption['reward_id'],))
                
                cursor.execute("UPDATE redemptions SET status = 'rejected' WHERE id = %s", (redemption_id,))
                connection.commit()
                flash('Redemption rejected and points returned to user', 'info')
    finally:
        connection.close()
    
    return redirect(url_for('admin_redemptions'))

@app.route('/admin/point-rules')
def admin_point_rules():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM point_rules ORDER BY waste_type")
            rules = cursor.fetchall()
    finally:
        connection.close()
    
    return render_template('admin_point_rules.html', rules=rules)

@app.route('/admin/update-point-rule', methods=['POST'])
def update_point_rule():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    rule_id = request.form['rule_id']
    points = float(request.form['points'])
    is_active = 'is_active' in request.form
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE point_rules 
                SET points_per_kg = %s, is_active = %s 
                WHERE id = %s
            """, (points, is_active, rule_id))
            connection.commit()
            flash('Point rule updated successfully', 'success')
    finally:
        connection.close()
    
    return redirect(url_for('admin_point_rules'))

@app.route('/admin/rewards')
def admin_rewards():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM rewards ORDER BY points_required")
            rewards = cursor.fetchall()
    finally:
        connection.close()
    
    return render_template('admin_rewards.html', rewards=rewards)

@app.route('/admin/add-reward', methods=['POST'])
def add_reward():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    name = request.form['name']
    description = request.form['description']
    points_required = int(request.form['points_required'])
    stock = request.form.get('stock')
    stock = None if stock == '' else int(stock)
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO rewards 
                (name, description, points_required, stock, is_active)
                VALUES (%s, %s, %s, %s, TRUE)
            """, (name, description, points_required, stock))
            connection.commit()
            flash('Reward added successfully', 'success')
    finally:
        connection.close()
    
    return redirect(url_for('admin_rewards'))

@app.route('/admin/toggle-reward/<int:reward_id>')
def toggle_reward(reward_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE rewards SET is_active = NOT is_active WHERE id = %s", (reward_id,))
            connection.commit()
            flash('Reward status toggled', 'info')
    finally:
        connection.close()
    
    return redirect(url_for('admin_rewards'))

@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.*, up.total_points_earned, up.points_available, up.points_redeemed
                FROM users u
                LEFT JOIN user_points up ON u.id = up.user_id
                WHERE u.is_admin = FALSE
                ORDER BY u.username
            """)
            users = cursor.fetchall()
    finally:
        connection.close()
    
    return render_template('admin_users.html', users=users)

if __name__ == '__main__':
    app.run(debug=True)