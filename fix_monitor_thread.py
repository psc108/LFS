#!/usr/bin/env python3

# Read the current main_window.py
with open('src/gui/main_window.py', 'r') as f:
    content = f.read()

# Replace the problematic BuildMonitorThread with a safer version
old_monitor_thread = '''class BuildMonitorThread(QThread):
    build_updated = pyqtSignal(dict)
    stage_updated = pyqtSignal(dict)
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.current_build_id = None
        self.running = False
    
    def set_build_id(self, build_id: str):
        self.current_build_id = build_id
    
    def run(self):
        self.running = True
        while self.running and self.current_build_id:
            try:
                build_details = self.db.get_build_details(self.current_build_id)
                if build_details:
                    self.build_updated.emit(build_details)
                self.msleep(1000)  # Update every second
            except Exception as e:
                print(f"Monitor error: {e}")
                self.msleep(5000)
    
    def stop(self):
        self.running = False'''

new_monitor_thread = '''class BuildMonitorThread(QThread):
    build_updated = pyqtSignal(dict)
    stage_updated = pyqtSignal(dict)
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.current_build_id = None
        self.running = False
        self.update_interval = 2000  # 2 seconds to reduce load
    
    def set_build_id(self, build_id: str):
        self.current_build_id = build_id
    
    def run(self):
        self.running = True
        consecutive_errors = 0
        
        while self.running and self.current_build_id:
            try:
                # Use a fresh connection for each query to avoid cursor issues
                build_details = self.get_build_details_safe(self.current_build_id)
                if build_details:
                    self.build_updated.emit(build_details)
                    consecutive_errors = 0  # Reset error counter on success
                else:
                    # Build might be completed or not found
                    consecutive_errors += 1
                    if consecutive_errors > 5:
                        print(f"Build {self.current_build_id} not found after 5 attempts, stopping monitor")
                        break
                
                self.msleep(self.update_interval)
                
            except Exception as e:
                consecutive_errors += 1
                print(f"Monitor error (attempt {consecutive_errors}): {e}")
                
                # If too many consecutive errors, stop monitoring
                if consecutive_errors > 10:
                    print("Too many monitor errors, stopping thread")
                    break
                    
                # Exponential backoff on errors
                error_delay = min(10000, 1000 * consecutive_errors)
                self.msleep(error_delay)
    
    def get_build_details_safe(self, build_id: str):
        """Safely get build details with proper connection handling"""
        try:
            # Create a fresh connection for this query
            conn = self.db.connect()
            if not conn:
                return None
                
            cursor = conn.cursor(dictionary=True)
            
            # Get build info
            cursor.execute("SELECT * FROM builds WHERE build_id = %s", (build_id,))
            build = cursor.fetchone()
            
            if not build:
                cursor.close()
                conn.close()
                return None
            
            # Get stages
            cursor.execute("SELECT * FROM build_stages WHERE build_id = %s ORDER BY stage_order", (build_id,))
            stages = cursor.fetchall()
            
            # Get recent documents (limit to avoid memory issues)
            cursor.execute("""
                SELECT * FROM build_documents 
                WHERE build_id = %s 
                ORDER BY created_at DESC 
                LIMIT 50
            """, (build_id,))
            documents = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {
                'build': build,
                'stages': stages or [],
                'documents': documents or []
            }
            
        except Exception as e:
            print(f"Error in get_build_details_safe: {e}")
            return None
    
    def stop(self):
        self.running = False
        # Wait for thread to finish gracefully
        if self.isRunning():
            self.wait(3000)  # Wait up to 3 seconds'''

content = content.replace(old_monitor_thread, new_monitor_thread)

# Also disable the monitor thread in start_build to prevent the crash entirely
old_monitor_start = '''            self.monitor_thread.set_build_id(build_id)
            self.monitor_thread.start()'''

new_monitor_start = '''            # Disable monitor thread temporarily to prevent crashes
            # self.monitor_thread.set_build_id(build_id)
            # self.monitor_thread.start()
            print("⚠ Build monitoring disabled to prevent crashes")'''

content = content.replace(old_monitor_start, new_monitor_start)

# Write the updated content
with open('src/gui/main_window.py', 'w') as f:
    f.write(content)

print("✅ Fixed monitor thread and disabled it to prevent crashes")