import json
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TypeVar, Type
from datetime import datetime
import pandas as pd

T = TypeVar('T')

class FileTool:
    """
    Handles file operations including saving CSVs and loading/saving JSON state.
    """
    
    def __init__(self, base_dir: Union[str, Path] = "artifacts"):
        """Initialize with base directory for artifacts."""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def save_csv(
        self, 
        data: List[Dict[str, Any]], 
        filename: str, 
        subdir: Optional[str] = None
    ) -> Path:
        """
        Save data to a CSV file.
        
        Args:
            data: List of dictionaries to save as CSV
            filename: Name of the output file (without .csv extension)
            subdir: Optional subdirectory under base_dir
            
        Returns:
            Path to the saved file
        """
        if not data:
            raise ValueError("No data provided to save")
            
        output_dir = self.base_dir / subdir if subdir else self.base_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean filename and ensure .csv extension
        clean_name = self._clean_filename(filename)
        if not clean_name.endswith('.csv'):
            clean_name += '.csv'
            
        filepath = output_dir / clean_name
        
        # Use pandas to handle complex data types
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False, quoting=csv.QUOTE_NONNUMERIC)
        
        return filepath
    
    def load_json(self, filepath: Union[str, Path], model: Type[T] = dict) -> T:
        """
        Load JSON data from a file, optionally parsing into a Pydantic model.
        
        Args:
            filepath: Path to the JSON file
            model: Pydantic model or dict type to parse into
            
        Returns:
            Parsed JSON data
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"JSON file not found: {filepath}")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if hasattr(model, 'parse_obj'):
            return model.parse_obj(data)
        return data
    
    def save_json(
        self, 
        data: Any, 
        filename: str, 
        subdir: Optional[str] = None,
        indent: int = 2
    ) -> Path:
        """
        Save data to a JSON file.
        
        Args:
            data: Data to serialize to JSON
            filename: Output filename (without .json extension)
            subdir: Optional subdirectory under base_dir
            indent: Indentation level for pretty-printing
            
        Returns:
            Path to the saved file
        """
        output_dir = self.base_dir / subdir if subdir else self.base_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean filename and ensure .json extension
        clean_name = self._clean_filename(filename)
        if not clean_name.endswith('.json'):
            clean_name += '.json'
            
        filepath = output_dir / clean_name
        
        # Handle Pydantic models and other special types
        if hasattr(data, 'dict'):
            data = data.dict()
        elif hasattr(data, 'model_dump'):
            data = data.model_dump()
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(
                data, 
                f, 
                indent=indent, 
                ensure_ascii=False,
                default=self._json_serializer
            )
            
        return filepath
    
    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for non-serializable types."""
        if isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat()
        elif hasattr(obj, 'dict'):
            return obj.dict()
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif isinstance(obj, Path):
            return str(obj)
        raise TypeError(f"Type {type(obj)} not serializable")
    
    def _clean_filename(self, filename: str) -> str:
        """Clean a filename to be filesystem-safe."""
        # Translation table for invalid characters
        invalid_chars = '<>:"/\\|?*\0'
        trans = str.maketrans(invalid_chars, '_' * len(invalid_chars))
        
        # Remove invalid characters and normalize spaces
        cleaned = (
            filename
            .translate(trans)  # Replace invalid chars with underscore
            .strip('. ')       # Remove leading/trailing dots and spaces
        )
        
        # Replace sequences of whitespace with a single underscore
        return '_'.join(cleaned.split())
    
    def ensure_dir(self, *path_parts: str) -> Path:
        """Ensure a directory exists, creating it if necessary."""
        dir_path = self.base_dir.joinpath(*path_parts)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def get_filepath(
        self, 
        filename: str, 
        subdir: Optional[str] = None,
        ensure_parent: bool = True
    ) -> Path:
        """
        Get a file path within the base directory.
        
        Args:
            filename: Name of the file
            subdir: Optional subdirectory
            ensure_parent: If True, ensure parent directory exists
            
        Returns:
            Full path to the file
        """
        if subdir:
            path = self.base_dir / subdir / filename
            if ensure_parent:
                path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path = self.base_dir / filename
            if ensure_parent:
                path.parent.mkdir(parents=True, exist_ok=True)
                
        return path
