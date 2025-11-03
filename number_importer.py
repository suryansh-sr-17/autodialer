import csv
import io
import logging
from typing import List, Dict, Tuple, Optional, Union
from werkzeug.datastructures import FileStorage
from number_handler import NumberHandler
from models import add_multiple_phone_numbers

logger = logging.getLogger(__name__)

class NumberImporter:
    """
    Handles importing phone numbers from various sources including text input,
    file uploads, and batch processing with comprehensive validation and reporting.
    """
    
    def __init__(self):
        self.number_handler = NumberHandler()
        self.supported_file_types = ['.txt', '.csv']
        self.max_file_size = 5 * 1024 * 1024  # 5MB
        self.max_numbers_per_import = 1000
    
    def import_from_text(self, text_input: str) -> Dict[str, Union[List, int, str]]:
        """
        Import phone numbers from text input (copy-paste).
        
        Args:
            text_input: Raw text containing phone numbers
            
        Returns:
            Dict containing import results and statistics
        """
        if not text_input or not text_input.strip():
            return {
                'success': False,
                'error': 'No text input provided',
                'statistics': self._get_empty_statistics()
            }
        
        try:
            # Parse numbers from text
            raw_numbers = self.number_handler.parse_text_input(text_input)
            
            if not raw_numbers:
                return {
                    'success': False,
                    'error': 'No phone numbers found in the text',
                    'statistics': self._get_empty_statistics()
                }
            
            # Check import limit
            if len(raw_numbers) > self.max_numbers_per_import:
                return {
                    'success': False,
                    'error': f'Too many numbers. Maximum allowed: {self.max_numbers_per_import}',
                    'statistics': self._get_empty_statistics()
                }
            
            # Process the numbers
            return self._process_numbers(raw_numbers, 'text_input')
            
        except Exception as e:
            logger.error(f"Error importing from text: {e}")
            return {
                'success': False,
                'error': f'Error processing text input: {str(e)}',
                'statistics': self._get_empty_statistics()
            }
    
    def import_from_file(self, file: FileStorage) -> Dict[str, Union[List, int, str]]:
        """
        Import phone numbers from uploaded file.
        
        Args:
            file: Uploaded file object
            
        Returns:
            Dict containing import results and statistics
        """
        if not file or not file.filename:
            return {
                'success': False,
                'error': 'No file provided',
                'statistics': self._get_empty_statistics()
            }
        
        # Validate file type
        file_extension = self._get_file_extension(file.filename)
        if file_extension not in self.supported_file_types:
            return {
                'success': False,
                'error': f'Unsupported file type. Supported: {", ".join(self.supported_file_types)}',
                'statistics': self._get_empty_statistics()
            }
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > self.max_file_size:
            return {
                'success': False,
                'error': f'File too large. Maximum size: {self.max_file_size // (1024*1024)}MB',
                'statistics': self._get_empty_statistics()
            }
        
        try:
            # Read file content
            content = file.read().decode('utf-8')
            
            if not content.strip():
                return {
                    'success': False,
                    'error': 'File is empty',
                    'statistics': self._get_empty_statistics()
                }
            
            # Parse based on file type
            if file_extension == '.csv':
                raw_numbers = self._parse_csv_content(content)
            else:  # .txt
                raw_numbers = self._parse_text_content(content)
            
            if not raw_numbers:
                return {
                    'success': False,
                    'error': 'No phone numbers found in the file',
                    'statistics': self._get_empty_statistics()
                }
            
            # Check import limit
            if len(raw_numbers) > self.max_numbers_per_import:
                return {
                    'success': False,
                    'error': f'Too many numbers in file. Maximum allowed: {self.max_numbers_per_import}',
                    'statistics': self._get_empty_statistics()
                }
            
            # Process the numbers
            return self._process_numbers(raw_numbers, f'file_upload_{file_extension}')
            
        except UnicodeDecodeError:
            return {
                'success': False,
                'error': 'File encoding not supported. Please use UTF-8 encoding.',
                'statistics': self._get_empty_statistics()
            }
        except Exception as e:
            logger.error(f"Error importing from file: {e}")
            return {
                'success': False,
                'error': f'Error processing file: {str(e)}',
                'statistics': self._get_empty_statistics()
            }
    
    def import_single_number(self, number: str) -> Dict[str, Union[bool, str, Dict]]:
        """
        Import a single phone number.
        
        Args:
            number: Single phone number string
            
        Returns:
            Dict containing import result
        """
        if not number or not number.strip():
            return {
                'success': False,
                'error': 'No phone number provided',
                'number_info': {}
            }
        
        try:
            # Validate the number
            is_valid, result, number_type = self.number_handler.validate_single_number(number)
            
            if not is_valid:
                return {
                    'success': False,
                    'error': result,
                    'number_info': {'original': number}
                }
            
            # Add to database
            success, message = add_multiple_phone_numbers([result])
            
            if success['added']:
                return {
                    'success': True,
                    'message': 'Phone number added successfully',
                    'number_info': {
                        'original': number,
                        'normalized': result,
                        'type': number_type,
                        'formatted': self.number_handler.format_number_for_display(result)
                    }
                }
            elif success['duplicates']:
                return {
                    'success': False,
                    'error': 'Phone number already exists',
                    'number_info': {
                        'original': number,
                        'normalized': result,
                        'type': number_type
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to add phone number to database',
                    'number_info': {'original': number}
                }
                
        except Exception as e:
            logger.error(f"Error importing single number: {e}")
            return {
                'success': False,
                'error': f'Error processing number: {str(e)}',
                'number_info': {'original': number}
            }
    
    def _process_numbers(self, raw_numbers: List[str], source: str) -> Dict[str, Union[List, int, str]]:
        """
        Process a list of raw phone numbers through validation and database insertion.
        """
        try:
            # Validate all numbers
            validation_results = self.number_handler.validate_multiple_numbers(raw_numbers)
            
            # Extract valid normalized numbers
            valid_numbers = [item['normalized'] for item in validation_results['valid']]
            
            # Add to database if there are valid numbers
            db_results = {'added': [], 'duplicates': [], 'invalid': [], 'errors': []}
            
            if valid_numbers:
                db_results = add_multiple_phone_numbers(valid_numbers)
            
            # Combine validation and database results
            final_results = {
                'success': True,
                'source': source,
                'processed_numbers': {
                    'added': self._format_number_results(validation_results['valid'], db_results['added']),
                    'duplicates': self._format_number_results(validation_results['valid'], db_results['duplicates']),
                    'invalid': validation_results['invalid'],
                    'errors': db_results['errors']
                },
                'statistics': {
                    'total_input': len(raw_numbers),
                    'valid_found': len(validation_results['valid']),
                    'invalid_found': len(validation_results['invalid']),
                    'duplicates_in_input': len(validation_results['duplicates']),
                    'successfully_added': len(db_results['added']),
                    'already_existed': len(db_results['duplicates']),
                    'database_errors': len(db_results['errors'])
                }
            }
            
            # Add number type statistics
            type_stats = self._get_type_statistics(validation_results['valid'])
            final_results['statistics'].update(type_stats)
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error processing numbers: {e}")
            return {
                'success': False,
                'error': f'Error processing numbers: {str(e)}',
                'statistics': self._get_empty_statistics()
            }
    
    def _parse_csv_content(self, content: str) -> List[str]:
        """Parse phone numbers from CSV content."""
        numbers = []
        
        try:
            # Try to detect if there's a header
            sniffer = csv.Sniffer()
            has_header = sniffer.has_header(content)
            
            # Parse CSV
            csv_reader = csv.reader(io.StringIO(content))
            
            if has_header:
                next(csv_reader)  # Skip header row
            
            for row in csv_reader:
                for cell in row:
                    if cell and cell.strip():
                        # Try to extract numbers from each cell
                        extracted = self.number_handler.extract_numbers_from_text(cell)
                        if extracted:
                            numbers.extend(extracted)
                        else:
                            # If no numbers extracted, add the cell as-is for validation
                            numbers.append(cell.strip())
            
        except csv.Error as e:
            logger.warning(f"CSV parsing error, falling back to text parsing: {e}")
            # Fall back to text parsing
            numbers = self.number_handler.parse_text_input(content)
        
        return numbers
    
    def _parse_text_content(self, content: str) -> List[str]:
        """Parse phone numbers from plain text content."""
        return self.number_handler.parse_text_input(content)
    
    def _format_number_results(self, valid_numbers: List[Dict], db_list: List[str]) -> List[Dict]:
        """Format number results with additional information."""
        formatted = []
        
        for number_info in valid_numbers:
            if number_info['normalized'] in db_list:
                formatted.append({
                    'original': number_info['original'],
                    'normalized': number_info['normalized'],
                    'type': number_info['type'],
                    'formatted': self.number_handler.format_number_for_display(number_info['normalized'])
                })
        
        return formatted
    
    def _get_type_statistics(self, valid_numbers: List[Dict]) -> Dict[str, int]:
        """Get statistics by number type."""
        stats = {
            'mobile_count': 0,
            'toll_free_count': 0,
            'landline_count': 0
        }
        
        for number_info in valid_numbers:
            number_type = number_info['type']
            if number_type == 'mobile':
                stats['mobile_count'] += 1
            elif number_type == 'toll_free':
                stats['toll_free_count'] += 1
            elif number_type == 'landline':
                stats['landline_count'] += 1
        
        return stats
    
    def _get_empty_statistics(self) -> Dict[str, int]:
        """Get empty statistics structure."""
        return {
            'total_input': 0,
            'valid_found': 0,
            'invalid_found': 0,
            'duplicates_in_input': 0,
            'successfully_added': 0,
            'already_existed': 0,
            'database_errors': 0,
            'mobile_count': 0,
            'toll_free_count': 0,
            'landline_count': 0
        }
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension in lowercase."""
        return '.' + filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    def validate_import_request(self, numbers_count: int) -> Tuple[bool, str]:
        """
        Validate if an import request can be processed.
        
        Args:
            numbers_count: Number of phone numbers to import
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if numbers_count <= 0:
            return False, "No numbers to import"
        
        if numbers_count > self.max_numbers_per_import:
            return False, f"Too many numbers. Maximum allowed: {self.max_numbers_per_import}"
        
        return True, ""
    
    def get_import_summary(self, results: Dict) -> str:
        """
        Generate a human-readable summary of import results.
        """
        if not results.get('success'):
            return f"Import failed: {results.get('error', 'Unknown error')}"
        
        stats = results.get('statistics', {})
        
        summary_parts = [
            f"Processed {stats.get('total_input', 0)} numbers",
            f"Added {stats.get('successfully_added', 0)} new numbers",
        ]
        
        if stats.get('already_existed', 0) > 0:
            summary_parts.append(f"{stats['already_existed']} already existed")
        
        if stats.get('invalid_found', 0) > 0:
            summary_parts.append(f"{stats['invalid_found']} were invalid")
        
        if stats.get('database_errors', 0) > 0:
            summary_parts.append(f"{stats['database_errors']} had database errors")
        
        return ". ".join(summary_parts) + "."