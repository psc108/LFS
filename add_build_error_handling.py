#!/usr/bin/env python3

# Read the current build_engine.py
with open('src/build/build_engine.py', 'r') as f:
    content = f.read()

# Add comprehensive error handling to start_build method
old_start_build = '''    def start_build(self, config_path: str) -> str:
        """Start a new build"""
        try:
            # Generate unique build ID
            build_id = f"lfs-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.urandom(4).hex()}"
            
            # Load configuration
            config = self.load_config(config_path)
            if not config:
                raise Exception(f"Failed to load configuration from {config_path}")
            
            # Create build record
            total_stages = len(config.get('stages', []))
            success = self.db.create_build(build_id, config.get('name', 'Unknown'), total_stages)
            if not success:
                raise Exception("Failed to create build record")
            
            # Log build start
            self.db.add_document(
                build_id, 'log', 'Build Started',
                f"Build {build_id} started with configuration: {config.get('name', 'Unknown')}",
                {'config_path': config_path, 'total_stages': total_stages}
            )
            
            # Save configuration
            self.db.add_document(
                build_id, 'config', 'Build Configuration',
                yaml.dump(config),
                {'config_path': config_path}
            )
            
            # Start build in background thread
            build_thread = threading.Thread(target=self._execute_build, args=(build_id, config))
            build_thread.daemon = True
            build_thread.start()
            
            return build_id
            
        except Exception as e:
            print(f"Build execution error: {e}")
            if 'build_id' in locals():
                self.db.add_document(
                    build_id, 'error', 'Build Exception',
                    str(e), {'exception_type': type(e).__name__}
                )
            raise'''

new_start_build = '''    def start_build(self, config_path: str) -> str:
        """Start a new build with comprehensive error handling"""
        build_id = None
        try:
            print("🔍 Starting build process...")
            
            # Generate unique build ID
            build_id = f"lfs-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.urandom(4).hex()}"
            print(f"🆔 Generated build ID: {build_id}")
            
            # Load configuration
            print(f"📋 Loading configuration from: {config_path}")
            config = self.load_config(config_path)
            if not config:
                raise Exception(f"Failed to load configuration from {config_path}")
            print(f"✅ Configuration loaded: {config.get('name', 'Unknown')}")
            
            # Create build record
            total_stages = len(config.get('stages', []))
            print(f"🏗️ Creating build record with {total_stages} stages...")
            success = self.db.create_build(build_id, config.get('name', 'Unknown'), total_stages)
            if not success:
                raise Exception("Failed to create build record in database")
            print("✅ Build record created successfully")
            
            # Log build start
            print("📝 Logging build start...")
            self.db.add_document(
                build_id, 'log', 'Build Started',
                f"Build {build_id} started with configuration: {config.get('name', 'Unknown')}",
                {'config_path': config_path, 'total_stages': total_stages}
            )
            
            # Save configuration
            print("💾 Saving build configuration...")
            self.db.add_document(
                build_id, 'config', 'Build Configuration',
                yaml.dump(config),
                {'config_path': config_path}
            )
            
            print("🚀 Starting build thread...")
            # Start build in background thread with error handling
            build_thread = threading.Thread(
                target=self._safe_execute_build, 
                args=(build_id, config),
                name=f"BuildThread-{build_id}"
            )
            build_thread.daemon = True
            build_thread.start()
            
            print(f"✅ Build {build_id} started successfully")
            return build_id
            
        except Exception as e:
            print(f"💥 Build execution error: {e}")
            import traceback
            traceback.print_exc()
            
            if build_id:
                try:
                    self.db.add_document(
                        build_id, 'error', 'Build Exception',
                        f"Build failed to start: {str(e)}\\n\\nTraceback:\\n{traceback.format_exc()}",
                        {'exception_type': type(e).__name__, 'startup_failure': True}
                    )
                    self.db.update_build_status(build_id, 'failed', 0)
                except Exception as db_error:
                    print(f"💥 Failed to log error to database: {db_error}")
            
            raise'''

content = content.replace(old_start_build, new_start_build)

# Add safe execute build method
safe_execute_method = '''
    def _safe_execute_build(self, build_id: str, config: dict):
        """Safely execute build with comprehensive error handling"""
        try:
            print(f"🔧 Starting safe build execution for {build_id}")
            self._execute_build(build_id, config)
            print(f"✅ Build execution completed for {build_id}")
        except Exception as e:
            print(f"💥 Build execution failed for {build_id}: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                # Log the error
                self.db.add_document(
                    build_id, 'error', 'Build Execution Error',
                    f"Build execution failed: {str(e)}\\n\\nTraceback:\\n{traceback.format_exc()}",
                    {'exception_type': type(e).__name__, 'execution_failure': True}
                )
                
                # Update build status
                self.db.update_build_status(build_id, 'failed', 0)
                
                # Trigger error callback
                if 'build_error' in self.callbacks:
                    for callback in self.callbacks['build_error']:
                        try:
                            callback({'build_id': build_id, 'error': str(e)})
                        except Exception as cb_error:
                            print(f"Error in build_error callback: {cb_error}")
                            
            except Exception as log_error:
                print(f"💥 Failed to log build error: {log_error}")
'''

# Insert the safe execute method before the _execute_build method
content = content.replace(
    '    def _execute_build(self, build_id: str, config: dict):',
    safe_execute_method + '\n    def _execute_build(self, build_id: str, config: dict):'
)

# Write the updated content
with open('src/build/build_engine.py', 'w') as f:
    f.write(content)

print("✅ Added comprehensive error handling to build engine")