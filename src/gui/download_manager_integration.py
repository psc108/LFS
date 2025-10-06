# Download Manager Integration for Enhanced Main Window

def add_download_manager_methods(main_window_class):
    """Add download manager methods to the main window class"""
    
    def open_download_manager(self):
        """Open the download manager dialog"""
        try:
            from .download_manager import DownloadManagerDialog
            
            dialog = DownloadManagerDialog(self, self.build_engine)
            dialog.exec_()
            
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Download Manager Error", f"Failed to open download manager: {str(e)}")
    
    def download_sources(self):
        """Download LFS source packages"""
        from PyQt5.QtWidgets import QProgressDialog, QMessageBox
        from PyQt5.QtCore import Qt
        
        if not self.build_engine:
            QMessageBox.warning(self, "Download Error", "Build engine not available")
            return
        
        try:
            # Show download progress dialog
            progress_dialog = QProgressDialog("Downloading LFS source packages...", "Cancel", 0, 100, self)
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.show()
            
            # Start download
            result = self.build_engine.download_lfs_sources()
            
            progress_dialog.close()
            
            if result:
                successful = len(result.get('success', []))
                failed = len(result.get('failed', []))
                
                message = f"Download completed!\n\nSuccessful: {successful}\nFailed: {failed}"
                
                if failed > 0:
                    message += "\n\nFailed downloads:"
                    for failure in result.get('failed', [])[:5]:  # Show first 5 failures
                        message += f"\n• {failure.get('package', 'Unknown')}: {failure.get('error', 'Unknown error')}"
                
                QMessageBox.information(self, "Download Complete", message)
            else:
                QMessageBox.warning(self, "Download Error", "Failed to start download process")
                
        except Exception as e:
            QMessageBox.critical(self, "Download Error", f"Failed to download sources: {str(e)}")
    
    # Add methods to the class
    main_window_class.open_download_manager = open_download_manager
    main_window_class.download_sources = download_sources
    
    return main_window_class