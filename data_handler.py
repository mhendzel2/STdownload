import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd
from logger import setup_logger


class DataHandler:
    """Handle data storage and retrieval operations"""
    
    def __init__(self, output_dir: str = "./data"):
        """
        Initialize data handler
        
        Args:
            output_dir: Directory to save data files
        """
        self.output_dir = output_dir
        self.logger = setup_logger('DataHandler')
        os.makedirs(output_dir, exist_ok=True)
        
    def save_to_csv(self, data: pd.DataFrame, filename: str, include_timestamp: bool = False) -> str:
        """
        Save DataFrame to CSV file. Default is now NOT to include timestamp.
        
        Args:
            data: DataFrame to save
            filename: Output filename
            include_timestamp: Whether to include timestamp in filename
            
        Returns:
            str: Full path to saved file
        """
        if include_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{timestamp}{ext}"
            
        filepath = os.path.join(self.output_dir, filename)
        try:
            data.to_csv(filepath)
            self.logger.info(f"Saved CSV file: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Failed to save CSV file {filepath}: {e}")
            raise
        
    def save_multiple_to_excel(self, data_dict: Dict[str, pd.DataFrame], filename: str) -> str:
        """
        Save multiple DataFrames to Excel file with separate sheets, handling potential
        sheet name collisions.
        
        Args:
            data_dict: Dictionary mapping sheet names to DataFrames
            filename: Output filename
            
        Returns:
            str: Full path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(filename)
        if not ext:
            ext = '.xlsx'
        filename = f"{name}_{timestamp}{ext}"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Clean sheet names and handle collisions
        sheet_names = {}
        cleaned_names_count = {}
        
        for symbol, data in data_dict.items():
            # Clean sheet name (Excel sheet names have restrictions)
            cleaned = self._clean_sheet_name(symbol)
            
            # Handle collisions by appending a counter
            if cleaned in cleaned_names_count:
                cleaned_names_count[cleaned] += 1
                final_name = f"{cleaned}_{cleaned_names_count[cleaned]}"
            else:
                cleaned_names_count[cleaned] = 0
                final_name = cleaned
            
            sheet_names[symbol] = final_name
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                for symbol, data in data_dict.items():
                    sheet_name = sheet_names[symbol]
                    data.to_excel(writer, sheet_name=sheet_name)
                    self.logger.info(f"Added sheet '{sheet_name}' for symbol '{symbol}'")
            
            self.logger.info(f"Saved Excel file with {len(data_dict)} sheets: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Failed to save Excel file {filepath}: {e}")
            raise
    
    def _clean_sheet_name(self, name: str) -> str:
        """
        Clean sheet name to be Excel-compatible
        
        Args:
            name: Original sheet name
            
        Returns:
            str: Cleaned sheet name
        """
        # Excel sheet name restrictions: max 31 chars, no special chars
        invalid_chars = ['[', ']', '*', '?', ':', '/', '\\']
        cleaned = name
        
        for char in invalid_chars:
            cleaned = cleaned.replace(char, '_')
        
        # Truncate to 31 characters if needed
        if len(cleaned) > 31:
            cleaned = cleaned[:31]
        
        return cleaned
        
    def load_from_csv(self, filename: str, parse_dates: bool = True) -> Optional[pd.DataFrame]:
        """
        Load DataFrame from CSV file
        
        Args:
            filename: Input filename
            parse_dates: Whether to parse date columns
            
        Returns:
            pd.DataFrame: Loaded data or None if failed
        """
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            if parse_dates:
                data = pd.read_csv(filepath, index_col=0, parse_dates=True)
            else:
                data = pd.read_csv(filepath, index_col=0)
            
            self.logger.info(f"Loaded CSV file: {filepath}")
            return data
        except FileNotFoundError:
            self.logger.error(f"File not found: {filepath}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load CSV file {filepath}: {e}")
            return None
    
    def save_metadata(self, metadata: Dict[str, Any], filename: str) -> str:
        """
        Save metadata to JSON file
        
        Args:
            metadata: Metadata dictionary
            filename: Output filename
            
        Returns:
            str: Full path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(filename)
        if not ext:
            ext = '.json'
        filename = f"{name}_{timestamp}{ext}"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            self.logger.info(f"Saved metadata file: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Failed to save metadata file {filepath}: {e}")
            raise
    
    def list_files(self, extension: str = None) -> List[str]:
        """
        List files in the output directory
        
        Args:
            extension: Filter by file extension (e.g., '.csv')
            
        Returns:
            List[str]: List of filenames
        """
        try:
            files = os.listdir(self.output_dir)
            if extension:
                files = [f for f in files if f.endswith(extension)]
            return sorted(files)
        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            return []
    
    def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get file information
        
        Args:
            filename: Filename to get info for
            
        Returns:
            Dict[str, Any]: File information or None if failed
        """
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            stat = os.stat(filepath)
            return {
                'filename': filename,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'filepath': filepath
            }
        except Exception as e:
            self.logger.error(f"Failed to get file info for {filename}: {e}")
            return None
